#!/usr/bin/env python3
"""Local-first YouTube production pipeline: Ollama -> native Python video engine -> Piper -> FFmpeg -> YouTube OAuth."""
from pathlib import Path
import argparse, json, os, re, shutil, subprocess, sys, time
from niche_research import research_niches, render_report
from safe_mode import nvidia_gpu_metrics
from hardware_scanner import scan_hardware
from engine.video_engine import generate_video as run_video_engine

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'outputs'; OUT.mkdir(exist_ok=True)
OLLAMA=os.environ.get('OLLAMA_URL','http://127.0.0.1:11434').rstrip('/')

def run(cmd, **kw):
    print('+', ' '.join(map(str,cmd)))
    return subprocess.run(list(map(str,cmd)),check=True,**kw)
def need_exe(name):
    p=shutil.which(name)
    if not p: raise RuntimeError(f'{name} not found on PATH. See CHANNEL_GUIDE.md for offline setup.')
    return p

def local_script(topic, model, research=None):
    research_context = ""
    if research:
        compact = []
        for row in research.get("ranked_niches", [])[:6]:
            samples = []
            for video in sorted(row.get("results", []), key=lambda x: x.get("views") or 0, reverse=True)[:4]:
                samples.append({"title": video.get("title"), "views": video.get("views"),
                                "estimated_views_per_day": video.get("views_per_day"),
                                "age_days": video.get("age_days"), "url": video.get("url")})
            compact.append({"niche": row.get("niche"), "search_query": row.get("query"),
                            "relative_opportunity_score": row.get("score"),
                            "median_views_per_day": row.get("median_views_per_day"),
                            "fresh_share_percent": row.get("freshness_score"),
                            "sample_videos": samples})
        research_context = "\nPUBLIC YOUTUBE SEARCH RESEARCH (imperfect relative signals, not a guarantee):\n" + json.dumps(compact, ensure_ascii=False)
    prompt=f'''You are an exceptional YouTube Shorts researcher, story editor and retention-focused scriptwriter.
Input niche/topic or seed: {topic}
{research_context}

Choose a specific, original video idea using the strongest research signal when research is present. Do not copy another video's title or script. Avoid pretending search data proves a topic will go viral. Use a clear, narrow promise and a payoff viewers can actually get. For factual topics, do not invent statistics, quotes, studies, or dramatic facts; phrase uncertainty honestly.

Return ONLY one valid JSON object in this exact shape (populate the values, do not return these instructions):
{{"chosen_topic":"specific video angle","title":"compelling title","description":"description","tags":["tag1","tag2"],"hook":"exact opening spoken line","script":"full spoken script","visual_prompt":"detailed opening-shot visual prompt","thumbnail_concept":"one clear thumbnail idea","retention_beats":["0:00 hook","0:10 reveal"]}}

Field requirements: chosen_topic is a specific angle, not just the broad niche; title is compelling and accurate, about 45-70 characters when practical; description includes a brief disclosure that visuals/narration may be AI-generated; tags is an array of 8-15 specific short tags; hook is the exact opening line spoken in the first 1-3 seconds; script is a 45-60 second YouTube Short (about 110-145 words); visual_prompt describes a cinematic, concrete opening shot that reinforces the hook, with no visible text/logos, designed for a small video model; thumbnail_concept gives one high-contrast focal idea without fake evidence; retention_beats is an array of 4-6 concise beats with approximate timestamps.

SCRIPT RETENTION RULES:
- Start with the hook immediately. No greetings, no channel intro, no “In today's video”, and no generic “Did you know?” unless it sets up a truly specific mystery.
- In the first two sentences create a concrete curiosity gap, surprising contrast, visual question, or problem with stakes; do not give away the full answer immediately.
- Promise a specific payoff early, then deliver it before the ending.
- Add a reveal, example, comparison, or mini-payoff every 8-12 seconds so the middle does not drag.
- Use short, natural spoken sentences and concrete verbs. Write for listening, not essay reading.
- Make the ending satisfying; use a very brief CTA only after the payoff. No fake urgency, false claims, engagement bait, or unsupported claims.
- The first sentence of script must exactly match hook. Keep the whole script feasible to narrate at normal speed in under 60 seconds.
- If research is present, use its winning patterns as inspiration, not copied wording. Choose a differentiated angle; the exact titles supplied are examples, not text to reuse.
'''
    try:
        # Keep the small language model on CPU and unload it immediately after generation,
        # preserving dedicated VRAM for the native video inference engine.
        d=post_json(OLLAMA+'/api/generate',{'model':model,'prompt':prompt,'stream':False,'format':'json','keep_alive':0,'options':{'num_gpu':0,'num_ctx':4096,'num_predict':1600,'num_thread':2}},timeout=600)
        raw=d.get('response','').strip()
        package=json.loads(raw)
        required=('title','description','tags','script')
        if not all(k in package for k in required): raise ValueError('Missing package fields')
        package.setdefault('chosen_topic', topic)
        package.setdefault('hook', sentence_chunks(package['script'])[0] if package.get('script') else '')
        package.setdefault('visual_prompt', f"Cinematic opening shot visualizing: {package.get('chosen_topic', topic)}. Immediate visual intrigue, realistic motion, no text or logos.")
        package.setdefault('thumbnail_concept', '')
        package.setdefault('retention_beats', [])
        if not isinstance(package['tags'], list): package['tags'] = []
        # Keep the narration opening aligned with the separately generated hook field.
        script_text = str(package.get('script') or '').strip()
        hook_text = str(package.get('hook') or '').strip()
        if hook_text and script_text and not script_text.startswith(hook_text):
            sentences = sentence_chunks(script_text)
            remainder = ' '.join(sentences[1:]) if len(sentences) > 1 else ''
            package['script'] = (hook_text + (' ' + remainder if remainder else '')).strip()
        return package
    except Exception as e:
        raise RuntimeError(f'Local script generation failed. Is Ollama running with model "{model}" downloaded? Details: {e}')

def sentence_chunks(script):
    parts=re.split(r'(?<=[.!?])\s+', re.sub(r'\s+',' ',script.strip()))
    return [p.strip() for p in parts if p.strip()]
def make_srt(script, duration, path):
    chunks=sentence_chunks(script)
    if not chunks: raise RuntimeError('Script is empty')
    weights=[max(1,len(x.split())) for x in chunks]; total=sum(weights); cursor=0; lines=[]
    def ts(sec):
        ms=int(sec*1000); h,ms=divmod(ms,3600000); m,ms=divmod(ms,60000); s,ms=divmod(ms,1000)
        return f'{h:02}:{m:02}:{s:02},{ms:03}'
    for i,(txt,w) in enumerate(zip(chunks,weights),1):
        start=cursor; cursor += duration*w/total
        # Keep each subtitle card readable.
        lines += [str(i),f'{ts(start)} --> {ts(cursor)}',txt,'']
    path.write_text('\n'.join(lines),encoding='utf-8-sig')

def generate_video(prompt, image_path=None, duration=4, fps=24, aspect="16:9"):
    """Use the in-process LTX runtime or a clearly labelled still-image renderer."""
    inventory = scan_hardware(ROOT)
    mode = "image-motion" if image_path else "text"
    task = {"mode": mode, "prompt": prompt, "image_path": str(image_path) if image_path else None,
            "duration": duration, "fps": fps, "aspect": aspect, "motion": "balanced",
            "inventory": inventory}
    output = OUT / f"raw_{int(time.time())}.mp4"
    result = run_video_engine(task, output, progress=lambda p, msg: print(f"  {p:5.1%} {msg}"))
    print("Video engine:", result.get("engine"))
    if not result.get("is_generative_ai"):
        print("NOTE:", result.get("description"))
    return Path(result["path"])

def make_voice(script, output):
    piper=shutil.which('piper')
    model=os.environ.get('PIPER_MODEL','')
    if not piper or not model or not Path(model).exists():
        raise RuntimeError('Offline TTS is not configured. Install Piper and set PIPER_MODEL to a downloaded local voice .onnx file; see CHANNEL_GUIDE.md. No cloud voice API is used.')
    proc=subprocess.run([piper,'--model',model,'--output_file',str(output)],input=script,text=True,capture_output=True,timeout=300)
    if proc.returncode: raise RuntimeError('Piper failed: '+proc.stderr[-2000:])

def media_duration(path):
    ffprobe=need_exe('ffprobe')
    out=subprocess.run([ffprobe,'-v','error','-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1',str(path)],capture_output=True,text=True,check=True)
    return max(1.0,float(out.stdout.strip()))

def compose(raw, voice, srt, final, fps=24):
    ff=need_exe('ffmpeg')
    # Escape subtitle path for FFmpeg filter syntax on Windows and POSIX.
    sub=str(srt.resolve()).replace('\\','/').replace(':','\\:').replace("'","\\'")
    vf=f"subtitles='{sub}':force_style='FontName=Arial,FontSize=22,Outline=2,Shadow=1,Alignment=2,MarginV=35'"
    # The local visual clip can be shorter than the narration. Loop it to preserve
    # narration/subtitle duration; the current pipeline does not yet build a scene timeline.
    run([ff,'-y','-stream_loop','-1','-i',raw,'-i',voice,'-vf',vf,'-r',str(fps),'-c:v','libx264','-preset','veryfast','-threads','2','-crf','22','-c:a','aac','-b:a','128k','-shortest','-movflags','+faststart',final])

def upload_youtube(video, package, privacy):
    try:
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request as GoogleRequest
        from google.oauth2.credentials import Credentials
    except ImportError:
        raise RuntimeError('YouTube upload libraries missing. Run: .venv\\Scripts\\python -m pip install google-api-python-client google-auth-oauthlib google-auth-httplib2')
    client=ROOT/'client_secret.json'; token=ROOT/'youtube_token.json'
    if not client.exists(): raise RuntimeError('Missing client_secret.json. Create OAuth Desktop credentials in Google Cloud and place the downloaded file beside this script; see CHANNEL_GUIDE.md.')
    scopes=['https://www.googleapis.com/auth/youtube.upload']
    creds=None
    if token.exists(): creds=Credentials.from_authorized_user_file(str(token),scopes)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token: creds.refresh(GoogleRequest())
        else: creds=InstalledAppFlow.from_client_secrets_file(str(client),scopes).run_local_server(port=0)
        token.write_text(creds.to_json(),encoding='utf-8')
    youtube=build('youtube','v3',credentials=creds)
    body={'snippet':{'title':str(package['title'])[:100],'description':str(package['description'])[:5000], 'tags':[str(t)[:30] for t in package.get('tags',[])][:500], 'categoryId':'27'},'status':{'privacyStatus':privacy,'selfDeclaredMadeForKids':False}}
    request=youtube.videos().insert(part='snippet,status',body=body,media_body=MediaFileUpload(str(video),mimetype='video/mp4',chunksize=8*1024*1024,resumable=True))
    response=None
    while response is None:
        status,response=request.next_chunk()
        if status: print(f'Upload: {int(status.progress()*100)}%')
    return 'https://www.youtube.com/watch?v='+response['id']

def main():
    ap=argparse.ArgumentParser(description='Offline YouTube channel production pipeline')
    ap.add_argument('--topic',help='Specific topic; with --auto-niche it becomes a seed for research')
    ap.add_argument('--interest',help='Broad channel interest for automatic niche research; omit/blank to scan multiple niches')
    ap.add_argument('--auto-niche',action='store_true',help='Research public YouTube results and choose a relative opportunity before writing')
    ap.add_argument('--research-only',action='store_true',help='Create a niche research report and stop without generating a video')
    ap.add_argument('--skip-research',action='store_true',help='Do not access public search; use a fixed topic entirely offline')
    ap.add_argument('--model',default=os.environ.get('OLLAMA_MODEL','qwen3:4b'),help='Small local Ollama model name; script generation is CPU-only in safe mode')
    ap.add_argument('--motion-image', help='Optional local still image; creates an image-motion MP4 on low-VRAM PCs (not generative AI)')
    ap.add_argument('--duration',type=int,default=60,help='Approximate subtitle timing duration in seconds')
    ap.add_argument('--fps',type=int,default=24,help='Output frame rate for local video rendering')
    ap.add_argument('--privacy',choices=['private','unlisted','public'],default='private')
    ap.add_argument('--no-upload',action='store_true',help='Create finished MP4 locally without uploading')
    ap.add_argument('--prompt-only',action='store_true',help='Only generate script/metadata locally after any requested research')
    args=ap.parse_args()
    interest=(args.interest or (args.topic if args.auto_niche else '') or '').strip()
    research=None
    if args.auto_niche and not args.skip_research:
        print('\n[0/5] Researching niche opportunities from public YouTube search...')
        research=research_niches(interest or None)
        print('\nNiche opportunity ranking:')
        for rank,row in enumerate(research['ranked_niches'][:5],1):
            fresh='n/a' if row['freshness_score'] is None else f"{row['freshness_score']}%"
            print(f"  {rank}. {row['niche']} | score {row['score']}/100 | median {row['median_views_per_day']:,.1f} views/day | recent uploads {fresh}")
        topic=research['ranked_niches'][0]['niche']
    else:
        topic=(args.topic or input('What is this YouTube video about? ').strip()).strip()
    if not topic: raise SystemExit('A topic is required, or run with --auto-niche to research one automatically.')
    stamp=time.strftime('%Y%m%d_%H%M%S')
    base=OUT/(f'research_{stamp}' if args.research_only else f'channel_{stamp}')
    base.mkdir(parents=True,exist_ok=True)
    if research:
        (base/'niche_research_report.md').write_text(render_report(research),encoding='utf-8')
        (base/'niche_research.json').write_text(json.dumps(research,indent=2,ensure_ascii=False),encoding='utf-8')
        print('Research report:',base/'niche_research_report.md')
    if args.research_only:
        if not research: raise SystemExit('--research-only requires --auto-niche unless --skip-research is disabled.')
        print('Research-only run complete. No model or GPU generation was started.')
        return
    print('\n[1/5] Generating a research-informed script, hook and YouTube metadata with local Ollama...')
    package=local_script(topic,args.model,research=research)
    (base/'package.json').write_text(json.dumps(package,indent=2,ensure_ascii=False),encoding='utf-8')
    (base/'script.txt').write_text(package['script'],encoding='utf-8')
    print('Chosen angle:',package.get('chosen_topic',topic))
    print('Opening hook:',package.get('hook',''))
    print('Title:',package['title']); print('Script saved:',base/'script.txt')
    if package.get('thumbnail_concept'):
        print('Thumbnail concept:',package['thumbnail_concept'])
    if args.prompt_only: print('Metadata saved:',base/'package.json'); return
    print('\n[2/5] Generating video with the integrated native Python engine...')
    visual_prompt=package.get('visual_prompt') or package.get('chosen_topic') or topic
    raw=generate_video(visual_prompt, image_path=args.motion_image, duration=max(2, min(args.duration, 12)), fps=args.fps)
    print('Raw video:',raw)
    print('\n[3/5] Creating offline narration with Piper...')
    voice=base/'narration.wav'; make_voice(package['script'],voice)
    print('\n[4/5] Burning subtitles and muxing narration with FFmpeg...')
    srt=base/'subtitles.srt'; voice_duration=media_duration(voice); make_srt(package['script'],voice_duration,srt)
    final=base/'final_video.mp4'; compose(raw,voice,srt,final)
    (base/'upload_metadata.json').write_text(json.dumps({'title':package['title'],'description':package['description'],'tags':package['tags'],'video_file':str(final)},indent=2,ensure_ascii=False),encoding='utf-8')
    print('Finished MP4:',final)
    if args.no_upload: print('Local production complete. Upload skipped (--no-upload).'); return
    print('\n[5/5] Uploading through official YouTube OAuth...')
    url=upload_youtube(final,package,args.privacy)
    (base/'youtube_url.txt').write_text(url,encoding='utf-8'); print('Published:',url)

if __name__=='__main__':
    try: main()
    except KeyboardInterrupt: print('\nCancelled by user.'); sys.exit(130)
    except Exception as e: print('\nERROR:',e); sys.exit(1)

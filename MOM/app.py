import os, time, subprocess, shutil
from pathlib import Path
from threading import Thread
from flask import Flask, render_template, request, send_file, jsonify
import markdown
import ollama
from faster_whisper import WhisperModel
from xhtml2pdf import pisa
from hardware import detect, recommended_model, installed_models, pull_model

BASE = Path(__file__).resolve().parent
UPLOAD_FOLDER = BASE / 'uploads'; OUTPUT_FOLDER = BASE / 'output'
UPLOAD_FOLDER.mkdir(exist_ok=True); OUTPUT_FOLDER.mkdir(exist_ok=True)
app = Flask(__name__)
whisper_model = None
processing_status = {"status":"idle","step":"","progress":0,"error":"","result_file":""}

def log(msg):
    print(f"[MOM] {msg}")

def ensure_llm():
    model = recommended_model()
    if model not in installed_models():
        log(f"Downloading recommended local model: {model}")
        pull_model(model)
    return model

def load_whisper():
    global whisper_model
    if whisper_model is None:
        whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
    return whisper_model

def pdf_from_markdown(md, path):
    html = markdown.markdown(md, extensions=['tables'])
    full = f"<html><body style='font-family:Arial;padding:40px'>{html}</body></html>"
    with open(path, 'w+b') as f: return pisa.CreatePDF(full, dest=f).err

def process_meeting(file_path):
    global processing_status
    try:
        processing_status.update(status='processing', progress=5, step='Detecting your hardware...')
        hw = detect(); model_name = ensure_llm()
        processing_status.update(progress=15, step=f'Using {model_name} · {hw["gpu"]["name"]}')
        path = Path(file_path); media = path
        if path.suffix.lower() not in {'.mp3','.wav','.m4a'}:
            ffmpeg = shutil.which('ffmpeg')
            if ffmpeg:
                audio = path.with_suffix('.mp3')
                subprocess.run([ffmpeg,'-i',str(path),'-vn','-acodec','libmp3lame','-y',str(audio)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                media = audio
        processing_status.update(progress=25, step='Transcribing locally with Whisper...')
        segments,_ = load_whisper().transcribe(str(media), beam_size=5)
        transcript=' '.join(s.text.strip() for s in segments)
        if len(transcript.strip()) < 5: raise RuntimeError('Could not extract enough speech from this recording.')
        processing_status.update(progress=65, step=f'Generating minutes with local {model_name}...')
        prompt = f'''Create professional Minutes of Meeting from this transcript. Return Markdown with: Executive Summary, Attendees (only if supported), Key Discussion Points, Decisions Made, Action Items with Task/Owner/Deadline, Risks and Next Steps. Never invent facts.\n\nTRANSCRIPT:\n{transcript}'''
        result = ollama.generate(model=model_name, prompt=prompt)
        md = result['response']
        processing_status.update(progress=90, step='Creating professional PDF...')
        name=f'MoM_{int(time.time())}.pdf'; pdf=OUTPUT_FOLDER/name
        pdf_from_markdown(md,pdf)
        processing_status.update(status='done',progress=100,step='Finished!',result_file=name)
    except Exception as e:
        processing_status.update(status='error',error=str(e),step='Setup or processing failed.')

@app.route('/')
def index(): return render_template('index.html')

@app.route('/hardware')
def hardware():
    hw=detect(); rec=recommended_model(hw)
    return jsonify({"hardware":hw,"recommended_model":rec,"installed_models":installed_models()})

@app.route('/setup-model',methods=['POST'])
def setup_model():
    try: return jsonify({"model":pull_model(recommended_model())})
    except Exception as e: return jsonify({"error":str(e)}),500

@app.route('/upload',methods=['POST'])
def upload_file():
    global processing_status
    file=request.files.get('file')
    if not file: return jsonify(error='No file selected'),400
    safe=Path(file.filename).name; path=UPLOAD_FOLDER/safe; file.save(path)
    processing_status={"status":"processing","step":"Starting local pipeline...","progress":0,"error":"","result_file":""}
    Thread(target=process_meeting,args=(path,),daemon=True).start()
    return jsonify(status='started')

@app.route('/status')
def status(): return jsonify(processing_status)

@app.route('/download/<filename>')
def download(filename): return send_file(OUTPUT_FOLDER/Path(filename).name,as_attachment=True)

if __name__=='__main__': app.run(debug=False,port=5000)

import json
from pathlib import Path
import streamlit as st
from app.hardware import detect,recommended_model,model_options
from app.ai.ollama_client import is_running,installed_models,chat
from app.ai.semantic_rag import LocalSemanticIndex,answer
from app.ai.prompts import notes_prompt
from app.study import generate_cards,generate_quiz,parse_json
from app.processors.ingest import extract_pdf,extract_docx,extract_text_file,extract_media,youtube_to_text,chunk_text
from app.processors.tts import speak
from app.storage import create_course,courses,sources,add_source,save_activity,activity

st.set_page_config(page_title='StudyAI Local',page_icon='🧠',layout='wide')
st.markdown('''<style>
.stApp{background:radial-gradient(900px 500px at 10% 0%,rgba(124,58,237,.22),transparent 60%),#09090f;color:#f7f5ff}.block-container{max-width:1250px;padding:30px 35px 60px}h1,h2,h3{font-family:Space Grotesk,sans-serif!important}.hero{padding:42px 0 25px}.hero h1{font-size:clamp(45px,6vw,76px);line-height:.98;letter-spacing:-.06em}.hero p,.muted{color:#9c98aa}.card{background:linear-gradient(180deg,#171722,#11111a);border:1px solid #2b2a39;border-radius:20px;padding:22px;margin:10px 0}.pill{display:inline-block;border:1px solid #4c3575;background:#24183d;color:#c4b5fd;border-radius:99px;padding:6px 10px;font-size:12px;font-weight:700}div.stButton>button{border-radius:12px;min-height:42px;font-weight:600}div.stButton>button[kind=primary]{background:linear-gradient(135deg,#7c3aed,#8b5cf6);border:0}
</style>''',unsafe_allow_html=True)

if 'index' not in st.session_state: st.session_state.index=LocalSemanticIndex()
for k,v in {'course_id':None,'material':'','chunks':[],'sources':[],'cards':[],'quiz':[],'card_i':0,'quiz_i':0,'score':0,'page':'Home'}.items():
    if k not in st.session_state: st.session_state[k]=v
hw=detect(); rec,rec_size,_=recommended_model(hw)

with st.sidebar:
    st.markdown('## 🧠 StudyAI')
    st.caption('Private · Local · Offline')
    page=st.radio('Workspace',['Home','Import Material','Notes','Flashcards','Quiz','AI Tutor','Courses','History'],index=['Home','Import Material','Notes','Flashcards','Quiz','AI Tutor','Courses','History'].index(st.session_state.page),label_visibility='collapsed')
    st.session_state.page=page
    st.divider(); st.markdown('### Local AI')
    st.caption(f'RAM · {hw.ram_gb:.1f} GB');st.caption(f'GPU · {hw.gpu_name}');st.caption(f'VRAM · {hw.vram_gb:.1f} GB');st.caption(f'Free disk · {hw.free_gb:.1f} GB')
    opts=model_options(); labels=[f'{m} · {d}' for m,_,d in opts]; cur=st.session_state.get('model',rec); idx=next((i for i,x in enumerate(opts) if x[0]==cur),0); st.session_state.model=opts[st.selectbox('Model',labels,index=idx)][0]
    if is_running() and st.session_state.model in installed_models(): st.success('Local AI ready')
    else: st.warning('Ollama/model not ready')
    st.caption(f'Recommended: {rec} · ~{rec_size} GB')

def ensure_course():
    if not st.session_state.course_id:
        st.session_state.course_id=create_course('My Study Course')

def add_material(name,kind,text):
    if not text.strip(): return
    ensure_course(); add_source(st.session_state.course_id,name,kind,text); st.session_state.sources.append((name,kind,text)); st.session_state.material+='\n\n'+text; st.session_state.chunks=chunk_text(st.session_state.material); st.session_state.index.build(st.session_state.chunks); save_activity(st.session_state.course_id,'source_added',{'name':name,'type':kind})

if page=='Home':
    st.markdown('<div class="hero"><span class="pill">✦ 100% LOCAL AI</span><h1>The fastest way to learn<br><span style="color:#a78bfa">anything.</span></h1><p>Bring PDFs, DOCX files, YouTube lessons, audio and video together. Generate notes, flashcards, quizzes and ask a private AI tutor.</p></div>',unsafe_allow_html=True)
    a,b,c,d=st.columns(4)
    for col,icon,title,desc in [(a,'📕','PDF','Text + OCR'),(b,'📄','DOCX','Documents + tables'),(c,'▶️','YouTube','Transcript + Whisper'),(d,'🎙️','Audio/Video','Local Whisper')]:
        with col: st.markdown(f'<div class="card"><div style="font-size:28px">{icon}</div><h3>{title}</h3><div class="muted">{desc}</div></div>',unsafe_allow_html=True)
    if st.button('Start a study workspace →',type='primary',use_container_width=True): st.session_state.page='Import Material'; st.rerun()

elif page=='Import Material':
    st.title('Build your study workspace'); st.caption('Add multiple sources. They become one searchable course knowledge base.')
    if not st.session_state.course_id:
        name=st.text_input('Course name','My Study Course')
        if st.button('Create course',type='primary'): st.session_state.course_id=create_course(name); st.rerun()
    else:
        st.success('Course ready. Add as many sources as you want.')
    tabs=st.tabs(['📄 Files','▶️ YouTube'])
    with tabs[0]:
        files=st.file_uploader('Upload PDF, DOCX, TXT, Markdown, audio or video',type=['pdf','docx','txt','md','mp3','wav','m4a','mp4','mkv','webm','mov'],accept_multiple_files=True)
        if files and st.button('Process selected files',type='primary'):
            for f in files:
                p=Path('data')/f.name; p.parent.mkdir(exist_ok=True); p.write_bytes(f.getbuffer()); ext=p.suffix.lower()
                with st.spinner(f'Processing {f.name} locally...'):
                    if ext=='.pdf': text=extract_pdf(p)
                    elif ext=='.docx': text=extract_docx(p)
                    elif ext in {'.txt','.md'}: text=extract_text_file(p)
                    else: text=extract_media(p)
                add_material(f.name,ext,text)
            st.success('All selected material was added to the course.')
    with tabs[1]:
        url=st.text_input('YouTube URL')
        if st.button('Import YouTube lesson',type='primary') and url:
            with st.spinner('Getting transcript / downloading audio for local Whisper...'): text,method=youtube_to_text(url)
            add_material(url,'youtube',text); st.success(f'Imported using {method}.')
    if st.session_state.sources:
        st.markdown('### Sources')
        for name,kind,text in st.session_state.sources: st.markdown(f'<div class="card"><b>{name}</b><div class="muted">{kind} · {len(text):,} characters</div></div>',unsafe_allow_html=True)

elif page=='Notes':
    st.title('AI Notes')
    if not st.session_state.chunks: st.info('Import material first.')
    elif st.button('Generate complete study notes',type='primary'):
        with st.spinner('Generating locally...'):
            parts=[chat(st.session_state.model,[{'role':'system','content':'Create accurate study notes.'},{'role':'user','content':notes_prompt(c)}],temperature=.1) for c in st.session_state.chunks[:20]]
            out=chat(st.session_state.model,[{'role':'system','content':'Combine notes without inventing facts.'},{'role':'user','content':'Combine these notes into a coherent study guide:\n\n'+'\n---\n'.join(parts)}],temperature=.1)
            st.session_state.notes=out; save_activity(st.session_state.course_id,'notes',{'text':out})
    if st.session_state.get('notes'): st.markdown('<div class="card">'+st.session_state.notes+'</div>',unsafe_allow_html=True)

elif page=='Flashcards':
    st.title('Flashcard Review')
    if not st.session_state.chunks: st.info('Import material first.')
    else:
        if not st.session_state.cards and st.button('Generate flashcards',type='primary'):
            with st.spinner('Creating cards locally...'): st.session_state.cards=parse_json(generate_cards(st.session_state.model,'\n'.join(st.session_state.chunks[:15])))
        if st.session_state.cards:
            card=st.session_state.cards[st.session_state.card_i%len(st.session_state.cards)]
            st.markdown(f'<div class="card"><div class="pill">CARD {st.session_state.card_i+1}/{len(st.session_state.cards)}</div><h2>{card["question"]}</h2></div>',unsafe_allow_html=True)
            if 'show_answer' not in st.session_state: st.session_state.show_answer=False
            if st.button('Show answer'): st.session_state.show_answer=True
            if st.session_state.show_answer:
                st.info(card['answer'])
                if st.button('Next card',type='primary'): st.session_state.card_i+=1; st.session_state.show_answer=False; st.rerun()

elif page=='Quiz':
    st.title('Interactive Quiz')
    if not st.session_state.chunks: st.info('Import material first.')
    else:
        if not st.session_state.quiz and st.button('Generate quiz',type='primary'):
            with st.spinner('Creating quiz locally...'): st.session_state.quiz=parse_json(generate_quiz(st.session_state.model,'\n'.join(st.session_state.chunks[:15])))
        if st.session_state.quiz:
            q=st.session_state.quiz[st.session_state.quiz_i%len(st.session_state.quiz)]
            st.markdown(f'<div class="card"><div class="pill">QUESTION {st.session_state.quiz_i+1}/{len(st.session_state.quiz)}</div><h2>{q["question"]}</h2></div>',unsafe_allow_html=True)
            choice=st.radio('Choose an answer',q['options'],key=f'q{st.session_state.quiz_i}')
            if st.button('Check answer',type='primary'):
                correct=q['options'][q['answer_index']];
                if choice==correct: st.session_state.score+=1; st.success('Correct!')
                else: st.error(f'Not quite. Correct answer: {correct}')
                st.caption(q['explanation'])
                if st.button('Next question'): st.session_state.quiz_i+=1; st.rerun()
            st.metric('Score',f'{st.session_state.score}/{max(1,st.session_state.quiz_i+1)}')

elif page=='AI Tutor':
    st.title('AI Tutor'); st.caption('Semantic retrieval + reranking + local Qwen.')
    if not st.session_state.chunks: st.info('Import material first.')
    else:
        q=st.chat_input('Ask anything about your course...')
        if q:
            with st.chat_message('user'): st.write(q)
            with st.chat_message('assistant'):
                with st.spinner('Searching your course locally...'): out=answer(st.session_state.model,q,st.session_state.index)
                st.write(out); save_activity(st.session_state.course_id,'question',{'q':q,'answer':out})

elif page=='Courses':
    st.title('My Courses')
    for cid,name,created in courses():
        st.markdown(f'<div class="card"><h3>{name}</h3><div class="muted">Created {created}</div></div>',unsafe_allow_html=True)

elif page=='History':
    st.title('Study History')
    if not st.session_state.course_id: st.info('Create or load a course first.')
    else:
        for kind,payload,created in activity(st.session_state.course_id): st.markdown(f'<div class="card"><b>{kind}</b><div class="muted">{created}</div></div>',unsafe_allow_html=True)

# Optional local podcast/TTS action is available from the Notes page via generated text.

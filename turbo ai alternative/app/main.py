import streamlit as st
from pathlib import Path
from app.hardware import detect, recommended_model, model_options
from app.ai.ollama_client import is_running, installed_models, chat
from app.ai.rag import answer_from_text
from app.ai.prompts import notes_prompt, flashcards_prompt, quiz_prompt
from app.processors.pdf import extract_pdf, chunk_text

st.set_page_config(page_title="StudyAI Local", page_icon="🧠", layout="wide")
st.markdown('''<style>@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;600;700&family=Space+Grotesk:wght@600;700&display=swap');.stApp{background:radial-gradient(900px 500px at 12% 0%,rgba(124,58,237,.20),transparent 60%),#09090f;color:#f7f5ff}.block-container{max-width:1200px;padding:30px 36px 60px}h1,h2,h3{font-family:"Space Grotesk",sans-serif!important}.hero{padding:45px 0 28px}.hero h1{font-size:clamp(46px,6vw,76px);letter-spacing:-.06em;line-height:1;margin:18px 0}.hero p{font-size:18px;line-height:1.6;color:#9c98aa;max-width:700px}.badge{display:inline-block;padding:7px 12px;border-radius:999px;background:#21183a;color:#c4b5fd;border:1px solid #3b2861;font-size:12px;font-weight:700}.card{background:linear-gradient(180deg,#15151f,#101018);border:1px solid #292938;border-radius:20px;padding:22px;margin:10px 0}.metric{background:#12121b;border:1px solid #292938;border-radius:16px;padding:18px}.muted{color:#9c98aa;font-size:13px}div.stButton>button{border-radius:12px;min-height:44px;font-weight:600}div.stButton>button[kind="primary"]{background:linear-gradient(135deg,#7c3aed,#8b5cf6);border:0}</style>''', unsafe_allow_html=True)

for k,v in {"material":"","chunks":[],"file_name":"","notes":"","cards":"","quiz":""}.items():
    if k not in st.session_state: st.session_state[k]=v
hw=detect(); rec,rec_size,_=recommended_model(hw)
with st.sidebar:
    st.markdown("## 🧠 StudyAI")
    st.caption("Private · Local · Offline")
    page=st.radio("Workspace",["Home","Study Material","Notes","Flashcards & Quiz","AI Tutor"],label_visibility="collapsed")
    st.divider(); st.markdown("### Local AI")
    st.caption(f"RAM · {hw.ram_gb:.1f} GB"); st.caption(f"GPU · {hw.gpu_name}"); st.caption(f"VRAM · {hw.vram_gb:.1f} GB"); st.caption(f"Free disk · {hw.free_gb:.1f} GB")
    opts=model_options(); labels=[f"{m} · {d}" for m,_,d in opts]; cur=st.session_state.get("model",rec); idx=next((i for i,x in enumerate(opts) if x[0]==cur),0); st.session_state.model=opts[st.selectbox("Model",labels,index=idx)][0]
    if is_running() and st.session_state.model in installed_models(): st.success("Local AI ready")
    else: st.warning("Install/start Ollama and the selected model")
    st.caption(f"Recommended: {rec} · ~{rec_size} GB")

if page=="Home":
    st.markdown('<div class="hero"><span class="badge">✦ 100% LOCAL AI</span><h1>The fastest way to learn<br><span style="color:#a78bfa">anything.</span></h1><p>Turn your study materials into interactive activities with AI that runs directly on your computer. No cloud AI API required.</p></div>',unsafe_allow_html=True)
    a,b,c=st.columns(3)
    for col,title,desc in [(a,"🔒 Private","Your documents stay on your PC"),(b,"⚡ Local AI","Qwen runs through Ollama"),(c,"∞ Study","Notes, cards, quizzes and tutor")]:
        with col: st.markdown(f'<div class="metric"><h3>{title}</h3><div class="muted">{desc}</div></div>',unsafe_allow_html=True)
    st.markdown("## Start a study session")
    st.markdown('<div class="card">',unsafe_allow_html=True)
    up=st.file_uploader("Drop your PDF here",type=["pdf"])
    if up and st.button("Generate study workspace →",type="primary",use_container_width=True):
        p=Path(up.name); p.write_bytes(up.getbuffer());
        with st.spinner("Reading locally..."): st.session_state.material=extract_pdf(str(p))
        st.session_state.chunks=chunk_text(st.session_state.material); st.session_state.file_name=up.name; st.success("Material ready. Use the sidebar to study.")
    st.markdown('</div>',unsafe_allow_html=True)
    x,y,z,w=st.columns(4)
    for col,icon,title in [(x,"📝","Notes"),(y,"🧠","Flashcards"),(z,"🎯","Quiz"),(w,"💬","AI Tutor")]:
        with col: st.markdown(f'<div class="card"><div style="font-size:28px">{icon}</div><h3>{title}</h3><div class="muted">Generated locally</div></div>',unsafe_allow_html=True)

elif page=="Study Material":
    st.title("Study Material")
    if not st.session_state.material: st.info("Upload a PDF on Home first.")
    else:
        st.markdown(f'<div class="card"><h3>📄 {st.session_state.file_name}</h3><div class="muted">{len(st.session_state.material):,} characters · {len(st.session_state.chunks)} chunks</div></div>',unsafe_allow_html=True)
        with st.expander("Preview extracted text"): st.text(st.session_state.material[:12000])

elif page=="Notes":
    st.title("AI Notes");
    if not st.session_state.material: st.info("Upload a PDF first.")
    elif st.button("Generate notes",type="primary"):
        with st.spinner("Thinking locally..."):
            parts=[chat(st.session_state.model,[{"role":"system","content":"You are a precise study-note generator."},{"role":"user","content":notes_prompt(c)}],temperature=.1) for c in st.session_state.chunks[:12]]
            st.session_state.notes=chat(st.session_state.model,[{"role":"system","content":"Combine notes accurately."},{"role":"user","content":"Combine these notes:\n\n"+"\n\n---\n".join(parts)}],temperature=.1)
    if st.session_state.notes: st.markdown('<div class="card">'+st.session_state.notes+'</div>',unsafe_allow_html=True)

elif page=="Flashcards & Quiz":
    st.title("Active Recall")
    if not st.session_state.material: st.info("Upload a PDF first.")
    else:
        source="\n\n".join(st.session_state.chunks[:8]); t1,t2=st.tabs(["🧠 Flashcards","🎯 Quiz"])
        with t1:
            if st.button("Generate flashcards",type="primary"): st.session_state.cards=chat(st.session_state.model,[{"role":"system","content":"Create accurate educational flashcards."},{"role":"user","content":flashcards_prompt(source)}],temperature=.2)
            if st.session_state.cards: st.markdown(st.session_state.cards)
        with t2:
            if st.button("Generate quiz",type="primary"): st.session_state.quiz=chat(st.session_state.model,[{"role":"system","content":"Create accurate educational quizzes."},{"role":"user","content":quiz_prompt(source)}],temperature=.2)
            if st.session_state.quiz: st.markdown(st.session_state.quiz)

else:
    st.title("AI Tutor"); st.caption("Ask questions grounded in your uploaded material.")
    if not st.session_state.chunks: st.info("Upload a PDF first.")
    q=st.chat_input("Ask about your material...")
    if q:
        with st.chat_message("user"): st.write(q)
        with st.chat_message("assistant"):
            with st.spinner("Searching locally..."): st.write(answer_from_text(st.session_state.model,q,st.session_state.chunks))

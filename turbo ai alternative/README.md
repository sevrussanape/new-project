# StudyAI Local — Turbo AI Alternative

A privacy-first local AI study workspace inspired by modern AI learning platforms. StudyAI processes your study material on your own computer using local AI models instead of requiring OpenAI/Gemini/Claude APIs.

## ✨ What is included

- 📕 PDF ingestion
- 🔍 Scanned-PDF OCR fallback
- 📄 DOCX ingestion, including tables
- 📝 TXT / Markdown ingestion
- 🎙️ Audio upload
- 🎥 Video upload
- 🗣️ Local Whisper transcription
- ▶️ YouTube transcript import
- ▶️ YouTube → local audio → Whisper fallback
- 📚 Multiple sources combined into one study knowledge base
- 🧠 Semantic embeddings
- 🗃️ Local FAISS vector database
- 🎯 Retrieval + reranking
- 🤖 Local Qwen3 LLM through Ollama
- 📝 AI notes
- 🧠 Flashcards + review mode
- 🎯 Interactive quizzes + answer checking/scoring
- 💬 AI Tutor grounded in retrieved course material
- 🔊 Optional local text-to-speech utility
- 🖼️ Foundation for local vision/multimodal models
- 🖥️ Hardware-aware model recommendation
- 🔒 No OpenAI/Gemini/Claude API required
- 🌐 Local Streamlit website
- 🪟 Windows `setup.bat` and `run.bat`

---

# 🚀 HOW TO RUN — START HERE

If you have just downloaded/cloned this project, **follow these steps in order**.

## 1. Install Python

Install **Python 3.11 or newer**.

During Windows installation, make sure:

```text
☑ Add Python to PATH
```

Check the installation:

```bash
python --version
```

You should see something like:

```text
Python 3.11.x
```

## 2. Install Ollama

Install Ollama on your computer:

urlOllama download pagehttps://ollama.com/download

Ollama runs the local LLM. StudyAI communicates with Ollama on your own machine.

You do **not** need an OpenAI API key, Gemini API key, Claude API key, or other cloud AI key.

After installing Ollama, you can check it from Command Prompt:

```bash
ollama --version
```

## 3. Download/clone the repository

```bash
git clone https://github.com/sevrussanape/new-project.git
cd new-project
git checkout ai-project
```

Then open this folder:

```text
turbo ai alternative
```

You can also download the repository as a ZIP from GitHub and extract it.

## 4. FIRST THING TO CLICK: `setup.bat`

On Windows, open:

```text
turbo ai alternative
```

Then **double-click:**

```text
setup.bat
```

### Do NOT run `run.bat` first.

`setup.bat` prepares the computer for StudyAI.

It performs roughly this process:

```text
                 setup.bat
                     │
                     ▼
          Create Python virtual environment
                     │
                     ▼
             Install Python libraries
                     │
                     ▼
              Check Ollama
                     │
                     ▼
        Detect RAM / GPU / VRAM / disk
                     │
                     ▼
          Select suitable Qwen3 model
                     │
                     ▼
       Download Qwen3 to user's computer
                     │
                     ▼
              Setup completed
```

The first setup can take time because AI models and Python dependencies may need to download.

## 5. AFTER setup finishes: `run.bat`

When `setup.bat` says setup is complete, **double-click:**

```text
run.bat
```

This starts the local StudyAI website.

It normally opens:

```text
http://localhost:8501
```

If the browser does not open automatically, copy that address into your browser.

## 6. First study session

Once the website opens:

```text
Home
  ↓
Upload study material
  ↓
PDF / DOCX / Audio / Video / YouTube
  ↓
Process locally
  ↓
Build semantic knowledge base
  ↓
Ask AI / Generate Notes / Flashcards / Quiz
```

---

# 📦 What gets installed/downloaded?

The GitHub project itself is intentionally small.

On the user's computer, setup can install/download:

```text
Python libraries
       +
Ollama
       +
Qwen3 LLM
       +
Embedding model
       +
Whisper model (when transcription is used)
       +
Optional OCR engine
```

These files are **not pushed to GitHub**.

For example, Qwen3 variants can range from a few GB to tens of GB depending on the selected model. The project therefore downloads an appropriate model locally instead of storing it in the repository.

---

# 🧠 Automatic model selection

StudyAI checks the computer's available resources and recommends a suitable local Qwen3 model.

Typical choices are:

| Model | Approx. model size | Intended use |
|---|---:|---|
| Qwen3 4B | ~2.6 GB | Lightweight computers |
| Qwen3 8B | ~5.2 GB | Balanced performance |
| Qwen3 14B | ~9.3 GB | Higher quality |
| Qwen3 30B | ~19 GB | High-end systems |

Actual storage requirements vary by model build and Ollama cache.

---

# 📚 Supported study sources

## PDF

Normal text PDFs are extracted locally.

For scanned PDFs, StudyAI can use OCR when the local OCR engine is installed.

## DOCX

DOCX paragraphs and tables can be extracted and added to the same study knowledge base.

## Audio

Audio can be transcribed locally with Whisper.

## Video

Video audio can be processed through the local transcription pipeline.

## YouTube

YouTube can use an available transcript first. If a transcript is unavailable, StudyAI can fall back to downloading the audio and transcribing it locally with Whisper.

> YouTube URL importing necessarily requires internet access because the source video is online.

---

# 🔍 Local semantic RAG

StudyAI does not simply paste the entire document into the LLM.

The workflow is:

```text
Documents
    ↓
Extract text
    ↓
Split into chunks
    ↓
Sentence-transformer embeddings
    ↓
FAISS local vector index
    ↓
Retrieve relevant chunks
    ↓
Rerank candidates
    ↓
Send relevant context to Qwen3
    ↓
Generate grounded answer
```

This makes the AI Tutor much more useful for large study materials.

---

# 📝 Study features

### AI Notes

Generate structured notes and summaries from your material.

### Flashcards

Generate question/answer flashcards and review them using active recall.

### Quiz

Generate multiple-choice questions, submit answers, and calculate the score.

### AI Tutor

Ask questions about your uploaded material. The system retrieves relevant source content before asking the local LLM to answer.

---

# 🔒 Offline / privacy behavior

There are two different situations:

### First-time setup

Internet is normally required to:

- Install Python packages
- Download the Qwen model
- Download embedding/Whisper models when required

### After models are installed

The core workflow can run locally/offline:

```text
Your documents
      ↓
Local extraction
      ↓
Local OCR / Whisper
      ↓
Local embeddings
      ↓
Local FAISS
      ↓
Local reranking
      ↓
Local Qwen3
      ↓
Answer
```

The exception is **direct YouTube importing**, which requires internet access to retrieve the online source.

---

# 🛠️ Optional OCR setup on Windows

If you use scanned PDFs, install the Tesseract OCR engine and make sure `tesseract.exe` is available on PATH.

Normal text PDFs do not require Tesseract.

---

# 📁 Project structure

```text
turbo ai alternative/
│
├── app/
│   ├── ai/
│   │   ├── ollama_client.py
│   │   ├── prompts.py
│   │   └── rag.py
│   │
│   ├── processors/
│   │   ├── audio.py
│   │   ├── pdf.py
│   │   └── ingest.py
│   │
│   ├── hardware.py
│   ├── main.py
│   └── setup.py
│
├── data/
├── models/
├── requirements.txt
├── setup.bat
├── run.bat
├── .gitignore
├── LICENSE
└── README.md
```

---

# ❓ Troubleshooting

### `python` is not recognized

Reinstall Python and enable **Add Python to PATH**, then reopen Command Prompt.

### Ollama is not running

Start the Ollama application and run `setup.bat` again.

### Model download is taking a long time

This is normal. The model is several GB depending on the selected model. You only need to download it once for that installation.

### Website does not open

Run `run.bat` again and check the terminal for the local address, normally:

```text
http://localhost:8501
```

### OCR does not work

Install Tesseract and make sure `tesseract.exe` is on PATH.

### YouTube import fails

Check that the computer has internet access and that the YouTube URL is valid. Direct YouTube importing cannot work fully offline.

---

# 🛣️ Scope

The core local study workflow is the priority:

- PDF
- DOCX
- YouTube
- Audio/video
- Whisper
- OCR
- Semantic embeddings
- FAISS retrieval
- Reranking
- Local Qwen3
- Notes
- Flashcards/review
- Quiz/scoring
- AI Tutor

The following optional items were intentionally left out of this build as requested:

- Course/project management
- Local study history
- Final marketing-page polish

---

# ⚠️ Important

This project is designed to be a **local AI alternative**, not a claim that it is identical to or affiliated with Turbo AI.

Large AI models are deliberately excluded from GitHub. `setup.bat` downloads the required models to the user's computer so the repository remains lightweight.

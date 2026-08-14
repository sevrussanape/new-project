# StudyAI Local — Turbo AI Alternative

A privacy-first **local AI study assistant** inspired by modern AI learning platforms. The goal is to provide a polished study workspace while keeping the AI processing on the user's own computer.

## ✨ What this project does

StudyAI is designed around this workflow:

```text
Your study material
       ↓
 PDF / documents / recordings
       ↓
 Local processing
       ↓
 Local RAG + Qwen3
       ↓
 ┌─────┬──────────┬─────────┐
 ↓     ↓          ↓         ↓
Notes Flashcards Quiz    AI Tutor
```

### Current working features

- 📕 PDF upload and local text extraction
- 🤖 Local Qwen3 LLM through Ollama
- 🧠 AI-generated study notes
- 🗂️ Flashcard generation
- 🎯 Quiz generation
- 💬 AI Tutor grounded in uploaded material
- 🖥️ Hardware detection
- ⚙️ Automatic local-model recommendation
- 🔒 No cloud AI API required
- 🌐 Local Streamlit web application
- 🪟 Windows `setup.bat` and `run.bat`
- 📦 Large AI model files are downloaded locally and are **not stored in GitHub**

## 🚀 How to install and run

### Step 1 — Install Python

Install **Python 3.11 or newer**.

Check it with:

```bash
python --version
```

### Step 2 — Install Ollama

Install Ollama on the computer from:

https://ollama.com/download

Ollama is responsible for running the local LLM. StudyAI does not send your prompts or documents to a cloud AI provider.

### Step 3 — Download this repository

```bash
git clone https://github.com/sevrussanape/new-project.git
cd new-project
```

Then switch to the project branch:

```bash
git checkout ai-project
```

Open:

```text
turbo ai alternative
```

### Step 4 — First installation

On Windows, double-click:

```text
setup.bat
```

**This is the first file you should run.**

The setup process:

```text
setup.bat
   ↓
Create Python virtual environment
   ↓
Install Python libraries
   ↓
Check Ollama
   ↓
Detect RAM / GPU / VRAM / disk
   ↓
Choose a suitable Qwen3 model
   ↓
Download the model to the user's PC
   ↓
Setup complete
```

### Step 5 — Start the website

After setup finishes, double-click:

```text
run.bat
```

The local StudyAI website will start in your browser, normally at:

```text
http://localhost:8501
```

## 🧠 Model strategy

The repository **does not contain the LLM weights**. This is intentional.

The setup script recommends a Qwen3 model based on the computer's available resources. Supported model choices currently include:

| Model | Approx. model size | Target |
|---|---:|---|
| Qwen3 4B | ~2.6 GB | Lightweight PCs |
| Qwen3 8B | ~5.2 GB | Balanced |
| Qwen3 14B | ~9.3 GB | Higher quality |
| Qwen3 30B | ~19 GB | High-end systems |

The actual installed size can vary depending on the Ollama model build and local cache.

### Why isn't the model on GitHub?

A model can be several gigabytes, while the source code is tiny. Putting the model into GitHub would make the repository unnecessarily huge.

Instead:

```text
GitHub
  ↓
Small source-code repository
  ↓
User runs setup.bat
  ↓
Ollama downloads the recommended model
  ↓
Model lives on the user's computer
```

## 🔒 Privacy / offline operation

The initial setup needs internet access to install dependencies and download the selected model.

After setup, the core AI workflow is local:

```text
User PDF
   ↓
Local extraction
   ↓
Local retrieval
   ↓
Local Qwen3
   ↓
Local answer
```

No OpenAI, Gemini, Claude, or other cloud AI API key is required for the current core workflow.

## 📁 Project structure

```text
turbo ai alternative/
│
├── app/
│   ├── ai/
│   │   ├── ollama_client.py
│   │   ├── prompts.py
│   │   └── rag.py
│   ├── processors/
│   │   ├── audio.py
│   │   └── pdf.py
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

## 🛣️ Roadmap

The current repository is the working MVP. Planned upgrades are:

- [ ] DOCX ingestion
- [ ] YouTube import/transcript workflow
- [ ] Audio and video upload
- [ ] Local Whisper transcription
- [ ] Semantic embeddings
- [ ] Vector database
- [ ] Reranking for better RAG accuracy
- [ ] OCR for scanned PDFs
- [ ] Better multimodal document understanding
- [ ] Interactive flashcard review
- [ ] Interactive quiz scoring
- [ ] Local text-to-speech / AI podcast mode
- [ ] Course/project management
- [ ] Local study history
- [ ] More polished Turbo-style landing page and workspace

## ⚠️ Current limitation

This is **not yet a complete one-to-one replacement for Turbo AI**. The current MVP focuses on the local LLM + PDF + study-material workflow. The roadmap above describes the remaining functionality needed for a fuller alternative.

## 📄 License

MIT License. See `LICENSE` for details.

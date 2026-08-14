# StudyAI Local — Turbo AI Alternative

A privacy-first local AI study workspace. The repository is small; large AI weights are downloaded to the user's computer during setup.

## Implemented

- PDF ingestion
- Scanned-PDF OCR fallback
- DOCX ingestion including tables
- TXT / Markdown ingestion
- Audio and video ingestion
- Local Whisper transcription
- YouTube transcript import with local-audio + Whisper fallback
- Multi-source course knowledge base
- Local sentence-transformer semantic embeddings
- FAISS vector database
- Retrieval + lightweight reranking
- Local Qwen3 LLM through Ollama
- AI notes
- Structured flashcards with review mode
- Structured quizzes with answer checking and scoring
- AI Tutor grounded in retrieved course sources
- Local SQLite course/activity storage
- Optional local TTS utility
- Hardware-aware Qwen model selection
- Windows setup/run scripts
- No OpenAI/Gemini/Claude API required

## Setup (Windows)

1. Install Python 3.11+.
2. Install Ollama from https://ollama.com/download.
3. Clone the repository and checkout `ai-project`.
4. Open `turbo ai alternative`.
5. **Run `setup.bat` first.**
6. When setup finishes, run `run.bat`.

Setup creates a virtual environment, installs dependencies, checks the computer's RAM/GPU/storage, and downloads a suitable Qwen3 model through Ollama.

### Optional OCR

OCR support uses Tesseract when available. If a scanned PDF needs OCR, install the Tesseract OCR engine on Windows and ensure `tesseract.exe` is on PATH. Normal text PDFs do not require it.

### What downloads on first use

The Qwen LLM is downloaded by Ollama. The sentence-transformer embedding model (`all-MiniLM-L6-v2`) is downloaded the first time the semantic index is built. Whisper downloads its selected model the first time audio/video transcription is used. These files are intentionally excluded from GitHub.

## Workflow

```text
PDF / DOCX / YouTube / Audio / Video
                 ↓
        Local extraction / Whisper / OCR
                 ↓
            Text chunks
                 ↓
       Sentence embeddings + FAISS
                 ↓
             Retrieval
                 ↓
            Reranking
                 ↓
            Local Qwen3
                 ↓
  Notes · Flashcards · Quiz · AI Tutor
```

## Offline behavior

The initial setup and online YouTube import require internet access. After the required models and dependencies have been downloaded, document processing, transcription, embeddings, retrieval and LLM generation can run locally. YouTube itself necessarily requires internet access when importing directly from a URL.

## Model files are not in GitHub

This repository intentionally contains source code only. A local installation can use several GB of model files without making the GitHub repository huge.

## Current scope

The requested core Turbo-style study features are implemented. Course management/history and the final marketing-page polish are optional extras and are not required for the core local AI workflow.

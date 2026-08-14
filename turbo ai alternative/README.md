# StudyAI Local

A privacy-first local AI study assistant. It runs the LLM locally through Ollama and keeps model files out of GitHub.

## Features
- PDF upload and local extraction
- Local Qwen3 model via Ollama
- AI notes, flashcards, quizzes and tutor chat
- Automatic hardware-based model recommendation
- Windows `setup.bat` and `run.bat`

## Setup
1. Install Python 3.11+.
2. Install Ollama from https://ollama.com/download.
3. Run `setup.bat`.
4. The setup detects hardware and downloads an appropriate Qwen3 model.
5. Run `run.bat`.

The model is intentionally downloaded on the user's computer rather than committed to GitHub.

## Roadmap
DOCX, YouTube, audio/video ingestion, Whisper transcription, semantic RAG, reranking, OCR, local TTS and the full Turbo-style study experience are planned for the next iterations.

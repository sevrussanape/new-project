# 🔒 Local AI Secretary: 100% Private MoM Generator

Convert your meeting recordings (Video/Audio) into professional, formatted PDF Minutes of Meeting (MoM) using **100% Local AI**. 

**Zero Cloud. Zero Costs. Zero Limits.**

---

## ✨ Features
- **100% Private**: Your audio never leaves your machine.
- **Faster-Whisper**: High-performance local transcription.
- **Ollama Integration**: Uses `llama3.2:1b` for intelligent summarization.
- **Professional PDF**: Beautifully formatted reports using `xhtml2pdf`.
- **Modern Web UI**: Glassmorphism design with real-time progress tracking.

---

## 🛠️ Prerequisites

Before running the project, you must install the following tools:

### 1. Python 3.10+
Download and install from [python.org](https://www.python.org/downloads/). Ensure you check **"Add Python to PATH"** during installation.

### 2. FFmpeg (Required for audio processing)
Open PowerShell as Administrator and run:
```powershell
winget install Gyan.FFmpeg
```

### 3. Ollama (The AI Runner)
1. Download from **[ollama.com](https://ollama.com/download)**.
2. Once installed, open your terminal and pull the brain for the app:
```powershell
ollama pull llama3.2:1b
```

---

## 🚀 Installation & Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/local-ai-secretary.git
   cd local-ai-secretary
   git checkout ai-project
   ```

2. **Install Dependencies**:
   ```bash
   pip install flask faster-whisper ollama markdown xhtml2pdf
   ```

3. **Run the Application**:
   ```bash
   python app.py
   ```

4. **Access the App**:
   Open **[http://127.0.0.1:5000](http://127.0.0.1:5000)** in your browser.

---

## 🌐 Online Version (`mom_online`)

The `mom_online` directory contains a version optimized for **Cloud Deployment** (e.g., Render, Railway, Heroku). 

- **Purpose**: Use this version if you want to host the app online.
- **AI**: Uses Gemini 1.5 Flash for both transcription and analysis (no local dependencies required).
- **Setup**:
  1. Add your `GEMINI_API_KEY` to `mom_online/app.py`.
  2. Deploy using the included `Procfile` and `requirements.txt`.

---

## 📂 Project Structure
- `app.py`: The heart of the application (Flask + AI Logic).
- `templates/`: HTML structure.
- `static/`: CSS styling and JavaScript for the UI.
- `uploads/`: Temporary storage for your uploaded files.
- `output/`: Where your finished PDFs live.

---

## ⚖️ License
MIT License - Feel free to use, modify, and share!

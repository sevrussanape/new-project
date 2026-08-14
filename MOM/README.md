# 🔒 Local AI Secretary — 100% Local MoM Generator

Turn meeting audio/video into professional **Minutes of Meeting (MoM)** PDFs using local AI.

The MOM project is now designed for **local/offline AI processing**. There is no cloud Gemini version and no API-key setup in this project.

## ✨ Features

- 🎙️ Audio and video meeting uploads
- 🗣️ Local Faster-Whisper transcription
- 🧠 Local Qwen3 through Ollama
- 🖥️ Automatic RAM / GPU / VRAM detection
- ⚙️ Automatic Qwen model recommendation
- 📥 Automatic Qwen download when the recommended model is missing
- 🎬 FFmpeg discovery through the system PATH
- 📝 Professional Minutes of Meeting generation
- 📄 PDF export
- 📊 Real-time processing progress
- 🌑 Modern responsive local web interface
- 🔒 Recordings and generated content remain on the computer
- 🌐 Runs at `http://127.0.0.1:5000`

---

# 🚀 HOW TO RUN — START HERE

## 1. Install Python

Install **Python 3.11 or newer** and enable **Add Python to PATH** during installation.

Check it:

```powershell
python --version
```

## 2. Install Ollama

Install Ollama:

https://ollama.com/download

Check it:

```powershell
ollama --version
```

You do **not** need a Gemini, OpenAI, Claude, or other cloud API key.

## 3. Install FFmpeg

FFmpeg is used to extract audio from video recordings.

On Windows PowerShell:

```powershell
winget install Gyan.FFmpeg
```

After installation, reopen your terminal.

Check it:

```powershell
ffmpeg -version
```

## 4. First thing to click: `setup.bat`

Open the `MOM` folder and double-click:

```text
setup.bat
```

**Do not run `app.py` first.**

The setup script:

```text
setup.bat
   ↓
Create Python virtual environment
   ↓
Install dependencies
   ↓
Detect RAM
   ↓
Detect NVIDIA GPU / VRAM
   ↓
Recommend Qwen3 model
   ↓
Prepare local AI environment
```

The recommended model can be downloaded automatically when the application starts if it is not already installed.

## 5. Start the website

After setup completes, activate the environment if needed:

```powershell
.venv\Scripts\activate
```

Then run:

```powershell
python app.py
```

Open:

```text
http://127.0.0.1:5000
```

## 6. Use MOM

```text
Upload meeting recording
        ↓
Hardware detection
        ↓
Recommended Qwen model
        ↓
Local Whisper transcription
        ↓
Local Qwen analysis
        ↓
Professional MoM
        ↓
PDF download
```

---

# 🧠 Automatic Qwen model selection

MOM checks your computer before selecting a model.

Current recommendations are approximately:

| Model | Approx. size | Target |
|---|---:|---|
| `qwen3:4b` | ~2.6 GB | Low-resource / CPU systems |
| `qwen3:8b` | ~5.2 GB | Balanced systems |
| `qwen3:14b` | ~9.3 GB | Higher-quality systems |
| `qwen3:30b` | ~19 GB | High-end systems |

The actual model size can vary by Ollama build.

The model is **not stored in GitHub**. It is downloaded to the user's computer when needed.

---

# 🖥️ Hardware detection

The application reports:

- Total RAM
- Free disk space
- NVIDIA GPU name when available
- NVIDIA VRAM when available
- Recommended Qwen model
- Installed Ollama models

If no NVIDIA GPU is available, MOM can fall back to a smaller Qwen model suitable for the available RAM.

---

# 🔒 Privacy and offline operation

The core processing pipeline is local:

```text
Meeting file
    ↓
Local FFmpeg
    ↓
Local Faster-Whisper
    ↓
Local transcript
    ↓
Local Qwen3 via Ollama
    ↓
Local PDF
```


### Internet is only needed initially for things such as:

- Installing Python packages
- Installing/downloading Ollama
- Downloading the selected Qwen model
- Downloading Whisper model files if not already cached

After those components are installed, the core meeting-processing workflow can operate without cloud AI.

---

# 🎙️ Supported recordings

The web interface accepts common audio/video formats such as:

```text
MP4
MOV
MKV
WEBM
MP3
WAV
M4A
```

Video audio is extracted with FFmpeg before transcription when FFmpeg is available.

---

# 📝 Minutes generation

The local Qwen prompt asks for professional meeting minutes containing information such as:

- Executive Summary
- Attendees when supported by the transcript
- Key Discussion Points
- Decisions Made
- Action Items
- Owner
- Deadline
- Risks
- Next Steps

The model is instructed not to invent unsupported facts.

---

# 🌐 Website

The MOM website was designed around a modern local-AI experience:

- Dark premium interface
- Local AI badge
- Large hero section
- Recording upload card
- Hardware information
- Recommended Qwen model
- Live progress bar
- Processing states
- PDF result screen
- Responsive layout

The website is served locally by Flask.

---

# 📁 Project structure

```text
MOM/
│
├── app.py
├── hardware.py
├── requirements.txt
├── setup.bat
├── templates/
│   └── index.html
├── uploads/
├── output/
└── README.md
```


# ⚠️ Troubleshooting

### `python` is not recognized

Reinstall Python and enable **Add Python to PATH**. Then open a new terminal.

### `ollama` is not recognized

Install Ollama and restart the terminal.

### Qwen download fails

Make sure Ollama is installed and running. Check:

```powershell
ollama list
```

### FFmpeg is not found

Install FFmpeg and ensure `ffmpeg` works from a new terminal:

```powershell
ffmpeg -version
```

### NVIDIA GPU is not detected

MOM uses `nvidia-smi` for NVIDIA detection. If it is unavailable, the application falls back to RAM-based model selection.

### Whisper is slow

Local transcription speed depends heavily on CPU/GPU hardware and the Whisper model size.

---

# ⚖️ License

MIT License — feel free to use, modify, and share.

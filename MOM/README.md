# 🔒 Local AI Secretary — 100% Local MoM Generator

Turn meeting audio/video into professional **Minutes of Meeting (MoM)** PDFs using local AI.

The MOM project is designed for **local/offline AI processing**. There is no cloud Gemini version and no API-key setup.

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

---

# 🚀 HOW TO RUN — START HERE

## 1. Install Python

Install **Python 3.11 or newer** and enable **Add Python to PATH**.

```powershell
python --version
```

## 2. Install Ollama

Install Ollama from:

https://ollama.com/download

Check it:

```powershell
ollama --version
```

You do **not** need a Gemini, OpenAI, Claude, or other cloud API key.

## 3. Install FFmpeg

FFmpeg extracts audio from video recordings.

```powershell
winget install Gyan.FFmpeg
```

Then reopen the terminal and check:

```powershell
ffmpeg -version
```

## 4. First thing to click: `setup.bat`

Open the `MOM` folder and double-click:

```text
setup.bat
```

**Do not run `app.py` first.**

Setup performs:

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

The recommended Qwen model is downloaded when required.

## 5. Start the website

```powershell
.venv\Scripts\activate
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

# 🖥️ Website / Application Structure

The MOM website is designed as a **full local AI application**, following the same modern product direction as the Turbo AI Alternative project rather than being only a simple upload page.

The planned/current application layout is:

```text
┌─────────────────────────────────────────────────────────────┐
│ ✦ MOM AI                              ● Local AI    Settings │
├──────────────┬──────────────────────────────────────────────┤
│              │                                              │
│  Dashboard   │       Turn Meetings Into Clear Action       │
│              │                                              │
│  New Meeting │   ┌──────────────────────────────────────┐   │
│              │   │                                      │   │
│  Meetings    │   │       🎙 Upload Meeting              │   │
│              │   │                                      │   │
│  Documents   │   │       MP4 • MP3 • WAV • M4A          │   │
│              │   │                                      │   │
│  AI Model    │   │          Choose Recording            │   │
│              │   │                                      │   │
│  Settings    │   └──────────────────────────────────────┘   │
│              │                                              │
│              │  GPU       VRAM       RAM       AI Model     │
│              │  RTX ...   8GB        32GB      Qwen3 8B    │
│              │                                              │
│              │  Recent Meetings                             │
│              │  ┌────────────┐ ┌────────────┐ ┌──────────┐ │
│              │  │ Meeting 01 │ │ Meeting 02 │ │ Meeting  │ │
│              │  │ ✓ Complete │ │ ✓ Complete │ │ Process  │ │
│              │  └────────────┘ └────────────┘ └──────────┘ │
└──────────────┴──────────────────────────────────────────────┘
```

### Main sections

```text
Dashboard
New Meeting
Meetings
Documents
AI Model
Settings
```

### Processing workspace

```text
Recording
    ↓
🎙 Whisper
    ↓
🧠 Transcript
    ↓
🤖 Qwen3
    ↓
📋 Minutes
    ↓
📄 PDF
```


# 🧠 Automatic Qwen model selection

MOM checks your computer before selecting a model.

| Model | Approx. size | Target |
|---|---:|---|
| `qwen3:4b` | ~2.6 GB | Low-resource / CPU systems |
| `qwen3:8b` | ~5.2 GB | Balanced systems |
| `qwen3:14b` | ~9.3 GB | Higher-quality systems |
| `qwen3:30b` | ~19 GB | High-end systems |

Actual model size can vary by Ollama build.

Models are **not stored in GitHub**. They are downloaded to the user's computer when needed.

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

The local Qwen prompt generates professional meeting minutes containing information such as:

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

```
MOM/
│
├── app.py
├── hardware.py
├── requirements.txt
├── setup.bat
├── README.md
│
├── templates/
│   └── index.html
│
├── static/
│   ├── style.css
│   └── app.js
│
├── uploads/
└── output/
```

### `templates/index.html`

Contains the application HTML structure.

### `static/style.css`

Contains the modern responsive visual design.

### `static/app.js`

Handles hardware information, upload, processing progress, errors, and PDF result handling.

The website is served locally by Flask.

---

# ⚠️ Troubleshooting

### `python` is not recognized

Reinstall Python and enable **Add Python to PATH**. Then open a new terminal.

### `ollama` is not recognized

Install Ollama and restart the terminal.

### Qwen download fails

Make sure Ollama is installed and running:

```powershell
ollama list
```

### FFmpeg is not found

Install FFmpeg and ensure:

```powershell
ffmpeg -version
```

works from a new terminal.

### NVIDIA GPU is not detected

MOM uses `nvidia-smi` for NVIDIA detection. If unavailable, the application falls back to RAM-based model selection.

### Whisper is slow

Local transcription speed depends heavily on CPU/GPU hardware and the selected Whisper model.

---

# ⚖️ License

MIT License — feel free to use, modify, and share.

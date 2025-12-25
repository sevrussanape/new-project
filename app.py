import os
import time
import shutil
import subprocess
import markdown
import ollama
from faster_whisper import WhisperModel
from flask import Flask, render_template, request, send_file, jsonify
from pathlib import Path
from xhtml2pdf import pisa
from threading import Thread

# FFmpeg path configuration
FFMPEG_BIN_DIR = r"C:\Users\kashy\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.0.1-full_build\bin"
FFMPEG_PATH = os.path.join(FFMPEG_BIN_DIR, "ffmpeg.exe")
FFPROBE_PATH = os.path.join(FFMPEG_BIN_DIR, "ffprobe.exe")

# Force paths into environment
os.environ["PATH"] = FFMPEG_BIN_DIR + os.pathsep + os.environ["PATH"]
os.environ["FFMPEG_BINARY"] = FFMPEG_PATH
os.environ["FFPROBE_BINARY"] = FFPROBE_PATH

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Local Model Config
# We use llama3.2:1b for extreme speed on local machines
LOCAL_LLM_MODEL = "llama3.2:1b"

# Global Faster-Whisper Model (lazy load)
whisper_model = None

# Global state to track progress
processing_status = {
    "status": "idle",
    "step": "",
    "progress": 0,
    "error": "",
    "result_file": ""
}

def load_whisper():
    global whisper_model
    if whisper_model is None:
        log_debug("Loading local Faster-Whisper model (base)...")
        # Run on CPU by default, int8 for speed
        whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
    return whisper_model

def convert_html_to_pdf(source_html, output_filename):
    result_file = open(output_filename, "w+b")
    pisa_status = pisa.CreatePDF(source_html, dest=result_file)
    result_file.close()
    return pisa_status.err

def log_debug(msg):
    log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "debug.log")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"[{time.ctime()}] {msg}\n")
    print(msg)

def process_meeting(file_path):
    global processing_status
    try:
        log_debug(f"--- NEW LOCAL JOB ---")
        log_debug(f"Processing File: {file_path}")
        processing_status["status"] = "processing"
        processing_status["progress"] = 5
        
        # 1. Extract Audio
        processing_status["step"] = "Optimizing audio locally..."
        video_path = Path(file_path).absolute()
        audio_path = video_path.with_suffix(".mp3")
        
        if video_path.suffix.lower() == ".mp3":
            media_path = str(video_path)
        elif os.path.exists(FFMPEG_PATH):
            try:
                subprocess.run(
                    [FFMPEG_PATH, "-i", str(video_path), "-vn", "-acodec", "libmp3lame", "-y", str(audio_path)],
                    check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                media_path = str(audio_path)
            except Exception as e:
                log_debug(f"FFmpeg failed: {e}")
                media_path = str(video_path)
        else:
            media_path = str(video_path)
        
        processing_status["progress"] = 20
        
        # 2. Local Transcription (Faster-Whisper)
        processing_status["step"] = "Transcribing locally (100% Free)..."
        model = load_whisper()
        segments, info = model.transcribe(media_path, beam_size=5)
        
        transcript_parts = []
        for segment in segments:
            transcript_parts.append(segment.text)
        
        transcript = " ".join(transcript_parts)
        log_debug(f"Transcript Length: {len(transcript)}")
        
        if not transcript or len(transcript.strip()) < 5:
            raise Exception("Transcription failed to extract text.")
            
        processing_status["progress"] = 60
        
        # 3. Local LLM Analysis (Ollama)
        processing_status["step"] = f"Generating Minutes with Local AI ({LOCAL_LLM_MODEL})..."
        log_debug(f"Calling Ollama...")
        
        prompt = f"Generate professional Minutes of Meeting from this transcript:\n\n{transcript}\n\nInclude Summary, Attendees, Discussion, Decisions, and Action Items in Markdown."
        
        try:
            response = ollama.generate(model=LOCAL_LLM_MODEL, prompt=prompt)
            generated_text = response['response']
            log_debug("Ollama response successful.")
        except Exception as e:
            log_debug(f"Ollama Error: {e}")
            raise Exception(f"Local AI (Ollama) failed. Make sure Ollama is running and you have pulled the model: ollama pull {LOCAL_LLM_MODEL}")

        processing_status["progress"] = 90
        
        # 4. PDF Generation
        processing_status["step"] = "Finalizing professional PDF..."
        html_body = markdown.markdown(generated_text, extensions=['tables'])
        full_html = f"<html><body style='font-family: Arial; padding: 40px;'>{html_body}</body></html>"
        
        pdf_filename = f"MoM_{int(time.time())}.pdf"
        pdf_path = os.path.join(OUTPUT_FOLDER, pdf_filename)
        convert_html_to_pdf(full_html, pdf_path)
        
        processing_status["status"] = "done"
        processing_status["progress"] = 100
        processing_status["step"] = "Finished!"
        processing_status["result_file"] = pdf_filename
        log_debug("LOCAL JOB COMPLETED.")
        
    except Exception as e:
        log_debug(f"CRITICAL LOCAL ERROR: {e}")
        processing_status["status"] = "error"
        processing_status["error"] = str(e)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    global processing_status
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    if file:
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(file_path)
        
        processing_status = {
            "status": "processing",
            "step": "Starting Local Pipeline...",
            "progress": 0,
            "error": "",
            "result_file": ""
        }
        
        thread = Thread(target=process_meeting, args=(file_path,))
        thread.start()
        return jsonify({"status": "started"})

@app.route('/status')
def get_status():
    return jsonify(processing_status)

@app.route('/download/<filename>')
def download_file(filename):
    return send_file(os.path.join(OUTPUT_FOLDER, filename), as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True, port=5000, use_reloader=False) 

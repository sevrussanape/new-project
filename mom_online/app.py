import os
import time
import shutil
import subprocess
import markdown
import google.generativeai as genai
from flask import Flask, render_template, request, send_file, jsonify
from pathlib import Path
from xhtml2pdf import pisa
from threading import Thread

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# API Key for Gemini
API_KEY = "YOUR_GEMINI_API_KEY_HERE"
genai.configure(api_key=API_KEY)

# Use Flash for cost/speed efficiency on the cloud
# Flash handles transcription natively via the File API
MODEL_NAME = "gemini-1.5-flash"

# Global state to track progress
processing_status = {
    "status": "idle",
    "step": "",
    "progress": 0,
    "error": "",
    "result_file": ""
}

def convert_html_to_pdf(source_html, output_filename):
    result_file = open(output_filename, "w+b")
    pisa_status = pisa.CreatePDF(source_html, dest=result_file)
    result_file.close()
    return pisa_status.err

def process_meeting(file_path):
    global processing_status
    try:
        processing_status["status"] = "processing"
        processing_status["progress"] = 10
        
        # 1. Upload to Gemini
        processing_status["step"] = "Uploading to Cloud AI..."
        model = genai.GenerativeModel(MODEL_NAME)
        uploaded_file = genai.upload_file(path=file_path)
        
        while uploaded_file.state.name == "PROCESSING":
            time.sleep(2)
            uploaded_file = genai.get_file(uploaded_file.name)
            
        processing_status["progress"] = 40
        
        # 2. Transcription & Analysis (Handled in one intelligent prompt for Flash)
        processing_status["step"] = "Transcribing and Analyzing Meeting..."
        prompt = "Please provide a full verbatim transcript followed by professional Minutes of Meeting (Summary, Attendees, Action Items) in Markdown format."
        
        response = None
        for attempt in range(5):
            try:
                response = model.generate_content([prompt, uploaded_file])
                break
            except Exception as e:
                if "429" in str(e): 
                    time.sleep(30)
                else: raise e
        
        if not response:
            raise Exception("Cloud AI failed to process the meeting.")

        processing_status["progress"] = 80
        
        # 3. PDF Generation
        processing_status["step"] = "Generating PDF..."
        html_body = markdown.markdown(response.text, extensions=['tables'])
        full_html = f"<html><body style='font-family: Arial; padding: 40px;'>{html_body}</body></html>"
        
        pdf_filename = f"MoM_{int(time.time())}.pdf"
        pdf_path = os.path.join(OUTPUT_FOLDER, pdf_filename)
        convert_html_to_pdf(full_html, pdf_path)
        
        processing_status["status"] = "done"
        processing_status["progress"] = 100
        processing_status["step"] = "Finished!"
        processing_status["result_file"] = pdf_filename
        
    except Exception as e:
        processing_status["status"] = "error"
        processing_status["error"] = str(e)
        print(f"Error: {e}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    global processing_status
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    if file:
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(file_path)
        
        processing_status = {
            "status": "processing",
            "step": "Starting...",
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
    # Use environment port for deployment (Render/Railway)
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

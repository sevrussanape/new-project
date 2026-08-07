"""
Step 1: Speech-to-Text Transcription using Gemini 1.5 Pro
"""

import os
import sys
import time
import subprocess
import shutil
import google.generativeai as genai
from pathlib import Path

# API Key
os.environ["GEMINI_API_KEY"] = "YOUR_GEMINI_API_KEY_HERE"

def setup_gemini():
    api_key = os.environ.get("GEMINI_API_KEY")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(model_name="gemini-2.0-flash-exp")

def extract_audio(video_path):
    # ... (omitted matching lines for brevity, assuming standard replace works on chunks)
    # Actually I need to target the setup_gemini and main loop separately or use multi_replace.
    # I will stick to replace_file_content for the model name first.
    pass 
    # Wait, I can't do pass. I will do model name first.

def extract_audio(video_path):
    """Extracts audio from video to save bandwidth."""
    video_path = Path(video_path)
    if not video_path.exists():
        print(f"Error: File {video_path} not found.")
        sys.exit(1)

    ffmpeg_path = r"C:\Users\kashy\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.0.1-full_build\bin\ffmpeg.exe"
    
    # Check if we can execute it
    if not os.path.exists(ffmpeg_path):
         print("FFmpeg not found at hardcoded path. Trying global path...")
         ffmpeg_path = "ffmpeg"

    print("running ffmpeg to extract audio...")
    audio_path = video_path.with_suffix(".mp3")
    try:
        subprocess.run(
            [ffmpeg_path, "-i", str(video_path), "-vn", "-acodec", "libmp3lame", "-y", str(audio_path)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return audio_path
    except Exception:
        return video_path

def upload_and_process(file_path):
    print(f"Uploading {file_path}...")
    uploaded_file = genai.upload_file(path=file_path)
    print(f"Upload complete. URI: {uploaded_file.uri}")

    while uploaded_file.state.name == "PROCESSING":
        print(".", end="", flush=True)
        time.sleep(2)
        uploaded_file = genai.get_file(uploaded_file.name)

    if uploaded_file.state.name == "FAILED":
        print("\nError: Processing failed.")
        sys.exit(1)
    return uploaded_file

def main():
    if len(sys.argv) < 2:
        print("Usage: python transcribe.py <video_file>")
        return

    input_file = sys.argv[1]
    model = setup_gemini()
    
    # 1. Optimize
    audio_file = extract_audio(input_file)
    
    # 2. Upload
    media_ref = upload_and_process(audio_file)
    
    # 3. Transcribe
    print("\n\nWait, converting speech to text (Tokenization)...")
    response = None
    for attempt in range(10):
        try:
            response = model.generate_content([
                "Please provide a full, verbatim transcript of this meeting recording. Do not summarize, just write down what was said.",
                media_ref
            ])
            break
        except Exception as e:
            if "429" in str(e) or "ResourceExhausted" in str(e):
                print(f"\nRate limit hit. Retrying in 60 seconds... (Attempt {attempt+1}/10)")
                time.sleep(60)
            else:
                raise e

    if not response:
        print("Error: Could not transcribe after 10 attempts due to Rate Limiting.")
        sys.exit(1)
    
    output_filename = "transcript.txt"
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(response.text)
    
    print(f"\n[Success] Transcript saved to {output_filename}")
    
    # Cleanup
    if audio_file != Path(input_file) and audio_file.exists():
        os.remove(audio_file)

if __name__ == "__main__":
    main()

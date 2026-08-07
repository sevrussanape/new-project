"""
Meeting Minutes Generator using Google Gemini 1.5 Pro
"""

import os
import sys
import time
import subprocess
import shutil
import google.generativeai as genai
from pathlib import Path

# Configure your API KEY here or set it as an environment variable
os.environ["GEMINI_API_KEY"] = "YOUR_GEMINI_API_KEY_HERE"

def setup_gemini():
    """Configures the Gemini API."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable not set.")
        print("Please set it or paste it in the script.")
        # Optional: Ask user for input if not set
        api_key = input("Enter your Gemini API Key: ").strip()
        if not api_key:
             sys.exit(1)
    
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(model_name="gemini-1.5-pro-latest")

def extract_audio(video_path):
    """
    Extracts audio from video using FFmpeg if available to save upload bandwidth.
    Returns the path to the audio file (or original video if ffmpeg fails).
    """
    video_path = Path(video_path)
    if not video_path.exists():
        print(f"Error: File {video_path} not found.")
        sys.exit(1)

    # Check if ffmpeg is available
    if not shutil.which("ffmpeg"):
        print("Note: FFmpeg not found. Uploading original video file (this may take longer)...")
        return video_path

    print("FFmpeg found. Extracting audio to speed up processing...")
    audio_path = video_path.with_suffix(".mp3")
    
    try:
        # ffmpeg -i input.mp4 -vn -acodec libmp3lame output.mp3
        subprocess.run(
            ["ffmpeg", "-i", str(video_path), "-vn", "-acodec", "libmp3lame", "-y", str(audio_path)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        print(f"Audio extracted: {audio_path}")
        return audio_path
    except subprocess.CalledProcessError:
        print("Warning: Audio extraction failed. Falling back to video upload.")
        return video_path
    except Exception as e:
        print(f"Warning: {e}. Falling back to video upload.")
        return video_path

def upload_and_process(file_path):
    """Uploads file to Gemini File API and waits for processing."""
    print(f"Uploading {file_path} to Gemini...")
    file_path = Path(file_path)
    
    # MIME type inference
    mime_type = "video/mp4" # Default
    if file_path.suffix.lower() in [".mp3", ".wav", ".aac", ".flac"]:
        mime_type = "audio/mp3"
    elif file_path.suffix.lower() in [".mov", ".avi", ".mkv", ".webm"]:
        mime_type = "video/mp4" # Generic mapping
        
    uploaded_file = genai.upload_file(path=file_path, mime_type=mime_type)
    print(f"Upload complete. File URI: {uploaded_file.uri}")

    # Verify processing state
    while uploaded_file.state.name == "PROCESSING":
        print(".", end="", flush=True)
        time.sleep(2)
        uploaded_file = genai.get_file(uploaded_file.name)

    if uploaded_file.state.name == "FAILED":
        print("\nError: File processing failed.")
        sys.exit(1)
        
    print(f"\nExample file is ready: {uploaded_file.name}")
    return uploaded_file

def generate_minutes(model, media_file):
    """Generates the MoM."""
    print("Generating Minutes of Meeting... This may take a minute.")
    
    prompt = """
    You are an expert executive secretary. 
    Please analyze the attached meeting recording and generate a comprehensive 'Minutes of Meeting' document.
    
    The output should be formatted in Markdown and include:
    1. **Meeting Summary**: A brief paragraph summarizing the overall purpose and outcome.
    2. **Attendees**: Inferred list of participants (if distinct voices/introductions exist).
    3. **Key Discussion Points**: Detailed bullet points of topics discussed.
    4. **Decisions Made**: Explicit decisions or conclusions reached.
    5. **Action Items**: A table or list of tasks assigned, to whom (if known), and deadlines (if mentioned).
    6. **Next Steps**: Any scheduled follow-ups.
    
    Be professional, concise, and accurate.
    """
    
    response = model.generate_content([prompt, media_file])
    return response.text

def main():
    if len(sys.argv) < 2:
        print("Usage: python mom.py <video_or_audio_file>")
        print("Example: python mom.py meeting_recording.mp4")
        return

    input_file = sys.argv[1]
    
    # 1. Setup
    model = setup_gemini()
    
    # 2. Optimization (Extract Audio if possible)
    processed_file_path = extract_audio(input_file)
    
    # 3. Upload
    media_file_ref = upload_and_process(processed_file_path)
    
    # 4. Generate
    minutes = generate_minutes(model, media_file_ref)
    
    # 5. Output
    print("\n" + "="*40)
    print("MINUTES OF MEETING")
    print("="*40 + "\n")
    print(minutes)
    
    # Save to file
    output_filename = "minutes_of_meeting.md"
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(minutes)
    print(f"\n[Saved to {output_filename}]")

    # Cleanup extracted audio if it was created temporarily
    if processed_file_path != Path(input_file) and processed_file_path.exists():
        os.remove(processed_file_path)
        print("Temporary audio file cleaned up.")

if __name__ == "__main__":
    main()

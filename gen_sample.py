"""
Generates a sample 'meeting' video for testing the MoM pipeline.
"""
import os
import time
from gtts import gTTS
import subprocess

def main():
    print("Generating sample meeting audio...")
    
    # 1. Create a script
    script = """
    [Manager]: Alright everyone, let's start the weekly sync. Sarah, how is the frontend migration going?
    [Sarah]: Hi Mark. It's going well. We finished the login page and the dashboard. However, we are blocked on the API for the user profile.
    [Manager]: Okay. David, when can the backend team deliver the user profile API?
    [David]: We ran into some database issues, but we should have it done by Thursday morning.
    [Manager]: That's cutting it close. Let's aim for Wednesday end of day so Sarah can test it.
    [David]: Understood. I will assign two more engineers to it.
    [Manager]: Great. Also, did we decide on the color scheme for the new logo?
    [Sarah]: Yes, the design team voted for the Blue and Gold variant.
    [Manager]: Perfect. Let's lock that in. Any other blockers?
    [Sarah]: No, that's it from me.
    [Manager]: Okay, thanks everyone. Let's get back to work. Meeting adjourned.
    """
    
    # 2. Convert to Audio
    tts = gTTS(text=script, lang='en', slow=False)
    tts.save("temp_audio.mp3")
    print("Audio generated: temp_audio.mp3")
    
    # 3. Create a dummy image for video background
    # simpler to just use a solid color with ffmpeg directly
    
    # 4. Combine into Video using FFmpeg
    output_video = "sample_meeting.mp4"
    print(f"Creating video {output_video}...")
    
    # ffmpeg -f lavfi -i color=c=black:s=1280x720:r=5 -i temp_audio.mp3 -c:a copy -shortest -y output.mp4
    ffmpeg_path = r"C:\Users\kashy\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.0.1-full_build\bin\ffmpeg.exe"
    cmd = [
        ffmpeg_path, 
        "-f", "lavfi", 
        "-i", "color=c=darkblue:s=1280x720:r=5", 
        "-i", "temp_audio.mp3", 
        "-c:v", "libx264", 
        "-tune", "stillimage", 
        "-c:a", "copy", 
        "-shortest", 
        "-y", 
        output_video
    ]
    
    try:
        subprocess.run(cmd, check=True, stderr=subprocess.DEVNULL)
        print(f"\n[Success] Created {output_video}")
        print("You can now test the pipeline with this file!")
    except Exception as e:
        print(f"Error creating video: {e}")

    # Cleanup
    if os.path.exists("temp_audio.mp3"):
        os.remove("temp_audio.mp3")

if __name__ == "__main__":
    main()

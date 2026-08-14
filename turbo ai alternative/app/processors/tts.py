from __future__ import annotations
from pathlib import Path

def speak(text,out_path,rate=165):
    try:
        import pyttsx3
        engine=pyttsx3.init(); engine.setProperty('rate',rate); engine.save_to_file(text,str(out_path)); engine.run(); return Path(out_path)
    except Exception as e:
        raise RuntimeError('Local TTS failed. Install pyttsx3 and a Windows voice.') from e

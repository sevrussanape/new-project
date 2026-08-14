from pathlib import Path
from app.ai.ollama_client import vision_chat

def analyze_images(model,paths,prompt='Describe and explain the important information in these study images. Extract diagrams, labels, tables and visual relationships accurately.'):
    return vision_chat(model,[Path(p) for p in paths],prompt)

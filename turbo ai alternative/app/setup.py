import shutil, subprocess, time

def ensure_model(model, log=None):
    if not shutil.which("ollama"):
        raise RuntimeError("Install Ollama from https://ollama.com/download and rerun StudyAI.")
    try: subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception: pass
    time.sleep(2)
    from app.ai.ollama_client import installed_models, pull_model
    if model not in installed_models(): pull_model(model, progress_cb=log)
    return True

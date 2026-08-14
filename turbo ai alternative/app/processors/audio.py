def transcribe(path, model_size="small"):
    from faster_whisper import WhisperModel
    model = WhisperModel(model_size, device="auto", compute_type="auto")
    segments, _ = model.transcribe(path, vad_filter=True)
    return " ".join(seg.text.strip() for seg in segments)

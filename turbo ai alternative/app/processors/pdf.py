from pathlib import Path

def extract_pdf(path):
    import fitz
    doc = fitz.open(path)
    pages = []
    for i, page in enumerate(doc):
        text = page.get_text("text").strip()
        if text: pages.append(f"[Page {i+1}]\n{text}")
    return "\n\n".join(pages)

def chunk_text(text, chunk_size=6000, overlap=500):
    text = " ".join(text.split())
    if not text: return []
    chunks, start = [], 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        chunks.append(text[start:end])
        if end == len(text): break
        start = end - overlap
    return chunks

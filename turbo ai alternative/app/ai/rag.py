from app.ai.ollama_client import chat

def answer_from_text(model, question, chunks):
    q = set(question.lower().split())
    scored = []
    for i, chunk in enumerate(chunks):
        score = len(q & set(chunk.lower().split()))
        scored.append((score, i, chunk))
    scored.sort(reverse=True)
    context = "\n\n--- SOURCE CHUNK ---\n".join(x[2] for x in scored[:6])
    prompt = f"""You are StudyAI, an accurate study tutor. Answer from the provided source material when possible. If the source does not contain the answer, say that clearly. Do not invent facts.\n\nSOURCE:\n{context}\n\nQUESTION:\n{question}"""
    return chat(model, [{"role":"system","content":"You are a precise educational assistant."},{"role":"user","content":prompt}], temperature=0.1)

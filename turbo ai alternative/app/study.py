from __future__ import annotations
import json
from app.ai.ollama_client import chat

def generate_cards(model,source,n=12):
    prompt=f'''Create {n} high-quality flashcards from this study material. Return strict JSON array with fields question,answer,difficulty. Do not invent facts.\nMATERIAL:\n{source}'''
    return chat(model,[{'role':'system','content':'Return valid JSON only.'},{'role':'user','content':prompt}],temperature=.2)

def generate_quiz(model,source,n=10):
    prompt=f'''Create {n} multiple-choice questions from this material. Return strict JSON array. Each object has question, options (array of 4 strings), answer_index (0-3), explanation, difficulty. Use only the material.\nMATERIAL:\n{source}'''
    return chat(model,[{'role':'system','content':'Return valid JSON only.'},{'role':'user','content':prompt}],temperature=.2)

def parse_json(text):
    try: return json.loads(text)
    except Exception:
        a=text.find('['); b=text.rfind(']')
        if a>=0 and b>a: return json.loads(text[a:b+1])
        raise ValueError('Model returned invalid JSON.')

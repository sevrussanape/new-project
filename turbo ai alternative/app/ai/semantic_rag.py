from __future__ import annotations
import re
from app.ai.ollama_client import chat

class LocalSemanticIndex:
    def __init__(self): self.chunks=[]; self.model=None; self.embeddings=None
    def build(self,chunks):
        self.chunks=list(chunks)
        try:
            from sentence_transformers import SentenceTransformer
            import numpy as np
            self.model=SentenceTransformer('all-MiniLM-L6-v2', local_files_only=False)
            self.embeddings=self.model.encode(self.chunks,normalize_embeddings=True)
        except Exception:
            self.model=None; self.embeddings=None
    def search(self,query,k=8):
        if not self.chunks: return []
        if self.model is not None:
            import numpy as np
            q=self.model.encode([query],normalize_embeddings=True)[0]
            scores=self.embeddings @ q
            ids=np.argsort(scores)[::-1][:k]
            return [(float(scores[i]),int(i),self.chunks[i]) for i in ids]
        q=set(re.findall(r'[a-zA-Z0-9_]+',query.lower())); out=[]
        for i,c in enumerate(self.chunks): out.append((len(q & set(re.findall(r'[a-zA-Z0-9_]+',c.lower()))),i,c))
        return sorted(out,reverse=True)[:k]

def rerank(query,results):
    q=set(re.findall(r'[a-zA-Z0-9_]+',query.lower())); ranked=[]
    for score,i,text in results:
        overlap=len(q & set(re.findall(r'[a-zA-Z0-9_]+',text.lower())))
        ranked.append((score+.01*overlap,i,text))
    return sorted(ranked,reverse=True)

def answer(model,query,index):
    hits=rerank(query,index.search(query,10))[:6]
    context='\n\n'.join(f'[Source {n+1}] {x[2]}' for n,x in enumerate(hits))
    prompt=f'''Answer the question using only the course sources below. If the sources do not support the answer, say so. Give clear explanations and source labels.\n\nSOURCES:\n{context}\n\nQUESTION:\n{query}'''
    return chat(model,[{'role':'system','content':'You are a precise local study tutor.'},{'role':'user','content':prompt}],temperature=.1)

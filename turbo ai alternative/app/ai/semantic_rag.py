from __future__ import annotations
import re
from app.ai.ollama_client import chat

class LocalSemanticIndex:
    def __init__(self): self.chunks=[]; self.model=None; self.index=None
    def build(self,chunks):
        self.chunks=list(chunks)
        try:
            from sentence_transformers import SentenceTransformer
            import faiss, numpy as np
            self.model=SentenceTransformer('all-MiniLM-L6-v2')
            vectors=self.model.encode(self.chunks,normalize_embeddings=True).astype('float32')
            self.index=faiss.IndexFlatIP(vectors.shape[1]); self.index.add(vectors)
        except Exception:
            self.model=None; self.index=None
    def search(self,query,k=8):
        if not self.chunks: return []
        if self.model is not None and self.index is not None:
            import numpy as np
            q=self.model.encode([query],normalize_embeddings=True).astype('float32')
            scores,ids=self.index.search(q,min(k,len(self.chunks)))
            return [(float(scores[0][j]),int(ids[0][j]),self.chunks[int(ids[0][j])]) for j in range(len(ids[0])) if ids[0][j]>=0]
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

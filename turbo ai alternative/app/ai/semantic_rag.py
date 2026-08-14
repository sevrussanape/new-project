from __future__ import annotations
import math, re
from collections import Counter
from app.ai.ollama_client import chat

class LocalSemanticIndex:
    def __init__(self):
        self.chunks=[]; self.vectors=[]; self.idf={}

    def _tokens(self,text): return re.findall(r'[a-zA-Z0-9_]+', text.lower())
    def _fit(self):
        docs=[set(self._tokens(x)) for x in self.chunks]; n=max(1,len(docs)); df=Counter(t for d in docs for t in d)
        self.idf={t:math.log((1+n)/(1+c))+1 for t,c in df.items()}
    def _vec(self,text):
        c=Counter(self._tokens(text)); norm=math.sqrt(sum((v*self.idf.get(t,1))**2 for t,v in c.items())) or 1
        return {t:(v*self.idf.get(t,1))/norm for t,v in c.items()}
    def build(self,chunks):
        self.chunks=list(chunks); self._fit(); self.vectors=[self._vec(x) for x in self.chunks]
    def search(self,query,k=8):
        q=self._vec(query); scored=[]
        for i,v in enumerate(self.vectors):
            score=sum(q.get(t,0)*v.get(t,0) for t in q)
            scored.append((score,i,self.chunks[i]))
        return sorted(scored,reverse=True)[:k]

def rerank(query, results):
    q=set(re.findall(r'[a-zA-Z0-9_]+',query.lower()))
    ranked=[]
    for score,i,text in results:
        overlap=len(q & set(re.findall(r'[a-zA-Z0-9_]+',text.lower())))
        ranked.append((score+0.015*overlap,i,text))
    return sorted(ranked,reverse=True)

def answer(model,query,index):
    hits=rerank(query,index.search(query,10))[:6]
    context='\n\n--- SOURCE ---\n'.join(x[2] for x in hits)
    prompt=f'''You are StudyAI, a rigorous tutor. Answer using the supplied course sources. Cite source chunk numbers like [Source 1] when useful. If the sources do not support a claim, say so instead of inventing it. Explain clearly and concisely.\n\nSOURCES:\n{context}\n\nQUESTION:\n{query}'''
    return chat(model,[{'role':'system','content':'You are an accurate local study assistant.'},{'role':'user','content':prompt}],temperature=0.1)

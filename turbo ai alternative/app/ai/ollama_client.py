from __future__ import annotations
import json, subprocess, urllib.request, urllib.error
OLLAMA_URL='http://127.0.0.1:11434'
def is_running():
    try:
        with urllib.request.urlopen(OLLAMA_URL+'/api/tags',timeout=2): return True
    except Exception: return False
def installed_models():
    try:
        with urllib.request.urlopen(OLLAMA_URL+'/api/tags',timeout=3) as r: return [m['name'] for m in json.loads(r.read().decode()).get('models',[])]
    except Exception: return []
def pull_model(model,progress_cb=None):
    p=subprocess.Popen(['ollama','pull',model],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
    if progress_cb:
        for line in p.stdout: progress_cb(line.rstrip())
    if p.wait()!=0: raise RuntimeError('Ollama could not download the model.')
def chat(model,messages,temperature=.2):
    payload=json.dumps({'model':model,'messages':messages,'stream':False,'options':{'temperature':temperature}}).encode()
    req=urllib.request.Request(OLLAMA_URL+'/api/chat',data=payload,headers={'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(req,timeout=600) as r: return json.loads(r.read().decode())['message']['content']
    except urllib.error.URLError as e: raise RuntimeError('Cannot reach Ollama. Start Ollama and try again.') from e

def vision_chat(model,image_paths,prompt,temperature=.1):
    messages=[{'role':'user','content':prompt,'images':[str(x) for x in image_paths]}]
    return chat(model,messages,temperature)

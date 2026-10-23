import json, os, urllib.request
class ModelUnavailable(Exception): pass
class OllamaAdapter:
    def generate(self,system,user):
        url=os.getenv('OLLAMA_URL','http://localhost:11434').rstrip('/')+'/api/chat'
        payload={'model':os.getenv('OLLAMA_MODEL','gemma3:1b'),'stream':False,'format':'json','options':{'temperature':0.1},'messages':[{'role':'system','content':system},{'role':'user','content':user}]}
        try:
            req=urllib.request.Request(url,json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
            with urllib.request.urlopen(req,timeout=40) as response: data=json.load(response)
            return data['message']['content']
        except Exception as exc: raise ModelUnavailable(str(exc)) from exc

import json
import urllib.request

class OllamaAgent:
    def __init__(self,model='deepseek-r1:32b',url='http://127.0.0.1:11434',timeout=600):
        self.model,self.url,self.timeout=model,url.rstrip('/'),timeout
    def ask(self,role,question):
        data=json.dumps({'model':self.model,'stream':False,'messages':[{'role':'system','content':role},{'role':'user','content':question}], 'options':{'num_ctx':4096,'temperature':0.2}}).encode()
        req=urllib.request.Request(self.url+'/api/chat',data=data,headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=self.timeout) as r:
            return json.loads(r.read())['message']['content']

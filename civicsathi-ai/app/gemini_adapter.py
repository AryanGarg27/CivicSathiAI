import os,json,urllib.request
import os,json,urllib.request,urllib.error
class GeminiUnavailable(Exception): pass
def analyze_photo(image_base64,mime_type):
    key=os.getenv('GEMINI_API_KEY')
    if not key: raise GeminiUnavailable('Gemini is not configured. Set GEMINI_API_KEY.')
    model=os.getenv('GEMINI_MODEL','gemini-2.5-flash')
    url=f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent'
    body={'contents':[{'parts':[{'text':'Describe only visible civic infrastructure issues in this image. Give factual evidence and uncertainty. Do not infer exact address or claim official diagnosis. Respond in 80 words maximum.'},{'inline_data':{'mime_type':mime_type,'data':image_base64}}]}]}
    req=urllib.request.Request(url,data=json.dumps(body).encode(),headers={'Content-Type':'application/json','x-goog-api-key':key})
    try:
        with urllib.request.urlopen(req,timeout=35) as r: obj=json.load(r)
        text=obj['candidates'][0]['content']['parts'][0]['text']
        return {'analysis':text,'provider':'google-gemini','advisory_only':True}
    except Exception as exc:
        if isinstance(exc, urllib.error.HTTPError):
            print("GOOGLE STATUS:", exc.code)
            print("GOOGLE RESPONSE:", exc.read().decode("utf-8", errors="replace")[:3000])
        raise GeminiUnavailable('Gemini image analysis unavailable: '+type(exc).__name__) from exc

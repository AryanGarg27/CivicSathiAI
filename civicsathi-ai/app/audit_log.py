import hashlib,json,time,os
from pathlib import Path
def audit_path(): return Path(os.getenv('AUDIT_LOG_PATH', str(Path(__file__).resolve().parents[1]/'logs'/'audit.jsonl')))
def append(event,detail):
    path=audit_path();path.parent.mkdir(parents=True,exist_ok=True)
    clean={'event':event,'timestamp':round(time.time(),3),'details':detail}
    with path.open('a',encoding='utf8') as f: f.write(json.dumps(clean,ensure_ascii=False)+'\n')
def fingerprint(text): return hashlib.sha256(text.encode()).hexdigest()[:16]

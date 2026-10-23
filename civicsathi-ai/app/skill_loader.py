from pathlib import Path
import re, yaml
ROOT = Path(__file__).resolve().parents[1]
def load_skill(name='civic-request-intake'):
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',name): raise ValueError('Invalid skill name')
    path = ROOT/'skills'/name/'SKILL.md'
    data=path.read_text(encoding='utf8')
    if not data.startswith('---\n'): raise ValueError('Missing YAML frontmatter')
    _,header,body=data.split('---',2)
    meta=yaml.safe_load(header)
    if meta.get('name')!=name or not 1<=len(meta.get('description',''))<=1024: raise ValueError('Invalid Agent Skill metadata')
    return {'metadata':meta,'instructions':body.strip()}

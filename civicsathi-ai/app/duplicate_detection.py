import re
from difflib import SequenceMatcher
def tokens(s): return set(re.findall(r'\w+',s.casefold()))
def similarity(a,b):
    x,y=tokens(a),tokens(b)
    overlap=len(x&y)/max(1,len(x|y))
    return round(max(overlap,SequenceMatcher(None,a.casefold(),b.casefold()).ratio()*0.7),3)
def find_duplicates(draft,cases,threshold=.47):
    matches=[]
    for case in cases:
        if case['category']!=draft.category: continue
        # Identical wording in different sectors should not be flagged as the same issue.
        sector = lambda value: re.search(r'(?:sector|सेक्टर|ਸੈਕਟਰ)\s*[-:]?\s*(\d+[a-z]?)\b', value or '', re.I)
        a,b=sector(draft.location),sector(case.get('location'))
        if a and b and a.group(1).casefold()!=b.group(1).casefold(): continue
        score=similarity(draft.summary+' '+(draft.location or ''),case['summary']+' '+(case['location'] or ''))
        if score>=threshold: matches.append({'id':case['id'],'score':score,'summary':case['summary']})
    return sorted(matches,key=lambda x:-x['score'])[:5]

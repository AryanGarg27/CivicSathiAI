import re
from collections import Counter

def _tokens(text: str) -> Counter:
    words = re.findall(r"[a-z0-9]+", text.lower())
    stop = {"the", "a", "an", "is", "are", "at", "in", "on", "near", "and", "for", "to", "of", "has", "have", "been", "there"}
    return Counter(w for w in words if w not in stop)

def _similarity(a: str, b: str) -> float:
    ta, tb = set(_tokens(a)), set(_tokens(b))
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)

def find_possible_duplicates(query: str, samples: list[dict], threshold: float = 0.18) -> list[dict]:
    """Simple lexical baseline for hints only; not a semantic model and not an auto-rejection."""
    out = []
    for item in samples:
        score = _similarity(query, item.get("summary", ""))
        if score >= threshold:
            out.append({"id": item.get("id", "sample"), "summary": item.get("summary", ""), "score": round(score, 3)})
    return sorted(out, key=lambda row: row["score"], reverse=True)

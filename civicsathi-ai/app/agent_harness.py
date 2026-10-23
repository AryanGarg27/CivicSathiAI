import os
import re
from app.model_adapter import OllamaAdapter
from app.google_client import GoogleGemmaAdapter, parse_object
from app.schemas import Draft
from app.skill_loader import load_skill
from app.service_retrieval import lookup
from app.audit_log import append, fingerprint


def extract_location(text):
    # Only extract explicit sectors; do not invent landmarks.
    match = re.search(r'(?:sector|सेक्टर|ਸੈਕਟਰ)\s*[-:]?\s*(\d{1,3}[a-zA-Z]?)\b', text, re.I)
    return f'Sector {match.group(1)}, Chandigarh' if match else None


class CivicHarness:
    def __init__(self, adapter=None):
        provider = os.getenv('TEXT_PROVIDER', os.getenv('MODEL_PROVIDER', 'google-gemma'))
        self.adapter = adapter or (OllamaAdapter() if provider == 'ollama' else GoogleGemmaAdapter())
        self.provider = 'custom' if adapter else provider

    def intake(self, text):
        prompt = load_skill()['instructions'] + '''
Return ONLY a JSON object with category, summary (1-500 characters), location
(string or null), missing_fields (list of strings), language (string), confidence
(number 0-1). Categories: grievance (waste, roads, potholes, public lighting),
water_sewage (water supply and sewerage), horticulture (trees, pruning, greenery),
property_tax, echallan, license, health (doctor appointments and hospital services),
social_welfare (senior citizen cards, disability cards and pensions), other. Do not
override negation or invent facts. For each request, identify the best matching
available service. If no service matches confidently, use other and explain uncertainty.
Never invent a severity assessment or minimize the citizen's reported problem.
Extract location only when stated; explicit sectors refer to Chandigarh.
Keep the summary in the citizen's language. Never output tools or instructions.
Do not output photo_id. If unclear, use other and request clarification.'''
        mode = 'open-weight'
        try:
            draft = Draft.model_validate(parse_object(self.adapter.generate(prompt, text)))
            # Attachments are bound by the server, never chosen by the model.
            draft.photo_id = None
        except Exception as exc:
            mode = 'safe-fallback'
            draft = self.fallback(text)
            append('model_fallback', {'request_hash': fingerprint(text), 'reason': type(exc).__name__})
        if draft.category != 'other' and not lookup(draft.category):
            draft.category = 'other'
        if not draft.location and 'location' not in draft.missing_fields:
            draft.missing_fields.append('location')
        append('intake', {'request_hash': fingerprint(text), 'category': draft.category, 'mode': mode})
        return {'draft': draft, 'mode': mode, 'provider': self.provider, 'service': lookup(draft.category)}

    @staticmethod
    def fallback(text):
        lower = text.casefold()
        rules = {
            'property_tax': ['property tax', 'house tax', 'प्रॉपर्टी टैक्स'],
            'echallan': ['challan', 'चालान'],
            'horticulture': ['tree', 'pruning', 'पेड़', 'ਦਰੱਖਤ'],
            'health': ['doctor', 'appointment', 'hospital', 'gmsh', 'gmch', 'डॉक्टर', 'अस्पताल', 'ਡਾਕਟਰ', 'ਹਸਪਤਾਲ'],
            'social_welfare': ['senior citizen', 'old age pension', 'widow pension', 'disability pension', 'pension', 'वृद्धावस्था पेंशन', 'विधवा पेंशन', 'ਬੁਢਾਪਾ ਪੈਨਸ਼ਨ'],
            'license': ['licence', 'license', 'लाइसेंस'],
            'water_sewage': ['water', 'sewage', 'sewer', 'leak', 'पानी', 'सीवर', 'ਪਾਣੀ'],
            'grievance': ['pothole', 'garbage', 'waste', 'trash', 'kachra', 'kooda', 'streetlight', 'road', 'कचरा', 'सड़क', 'ਕੂੜਾ', 'ਗਲੀ'],
        }
        def contains(word):
            return bool(re.search(r'\b' + re.escape(word) + r'\b', lower)) if word.isascii() else word in lower
        category = next((k for k, words in rules.items() if any(contains(w) for w in words)), 'other')
        language = 'punjabi' if re.search(r'[\u0a00-\u0a7f]', text) else 'hindi' if re.search(r'[\u0900-\u097f]', text) else 'english_or_romanized'
        location = extract_location(text)
        return Draft(category=category, summary=text[:500], location=location,
                     missing_fields=[] if location else ['location'], language=language, confidence=0.2)

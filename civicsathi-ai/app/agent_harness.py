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
(string or null), service_type (one of the listed form types or null), extracted_fields
(object of explicitly stated form values only), missing_fields (list of strings), language (string), confidence
(number 0-1). Categories: grievance (waste, roads, potholes, public lighting),
water_sewage (water supply and sewerage), horticulture (trees, pruning, greenery),
property_tax, echallan, license, health (doctor appointments and hospital services),
social_welfare (senior citizen cards, disability cards and pensions), other. Do not
override negation or invent facts. For each request, identify the best matching
available service. If no service matches confidently, use other and explain uncertainty.
Never invent a severity assessment or minimize the citizen's reported problem.
Extract location only when stated; explicit sectors refer to Chandigarh.
Use service_type health_appointment for appointments; senior_card, disability_card,
old_age_pension, widow_pension, or disability_pension only when the citizen specifies
that application; horticulture for tree, park or green-space requests. Otherwise use
null. extracted_fields may contain only explicitly stated values with keys applicant_name,
contact_phone, department, preferred_date, reason, beneficiary_name, relationship,
address, or description. Never guess a name, phone, date, relationship, diagnosis,
address, eligibility, or other personal detail. Do not extract Aadhaar, bank, or
detailed medical record information. Use an empty object when no form details were stated.
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
        allowed_fields = {'applicant_name', 'contact_phone', 'department', 'preferred_date', 'reason',
                          'beneficiary_name', 'relationship', 'address', 'description'}
        draft.extracted_fields = {key: value.strip()[:300] for key, value in draft.extracted_fields.items()
                                  if key in allowed_fields and isinstance(value, str) and value.strip()}
        expected_categories = {'health_appointment': 'health', 'senior_card': 'social_welfare',
                               'disability_card': 'social_welfare', 'old_age_pension': 'social_welfare',
                               'widow_pension': 'social_welfare', 'disability_pension': 'social_welfare',
                               'horticulture': 'horticulture'}
        if draft.service_type and expected_categories.get(draft.service_type) != draft.category:
            draft.service_type = None
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
        service_type = None
        if category == 'health':
            service_type = 'health_appointment'
        elif category == 'social_welfare':
            service_type = next((kind for kind, terms in {
                'senior_card': ['senior citizen card', 'elderly card'],
                'disability_card': ['disability card', 'disability id'],
                'widow_pension': ['widow pension'], 'disability_pension': ['disability pension'],
                'old_age_pension': ['old age pension', 'elderly pension', 'pension'],
            }.items() if any(term in lower for term in terms)), None)
        elif category == 'horticulture':
            service_type = 'horticulture'
        return Draft(category=category, summary=text[:500], location=location, service_type=service_type,
                     missing_fields=[] if location else ['location'], language=language, confidence=0.2)

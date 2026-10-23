"""Small Google REST client shared by hosted Gemma text and vision adapters."""
import json
import os
import re
import time
import httpx


class GoogleUnavailable(Exception):
    def __init__(self, code='unavailable', http_status=None):
        self.code = code
        self.http_status = http_status
        super().__init__(code)


def generate(parts, *, model, system=''):
    key = os.getenv('GEMINI_API_KEY', '').strip()
    if not key:
        raise GoogleUnavailable('not_configured')
    if not re.fullmatch(r'[A-Za-z0-9._-]+', model):
        raise GoogleUnavailable('invalid_model')
    config = {'temperature': 0.1, 'maxOutputTokens': 1500}
    if model.startswith('gemma-4'):
        config['thinkingConfig'] = {'thinkingLevel': 'minimal'}
    payload = {'contents': [{'role': 'user', 'parts': parts}], 'generationConfig': config}
    if system:
        payload['systemInstruction'] = {'parts': [{'text': system}]}
    try:
        for attempt in range(2):
            response = httpx.post(
                f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent',
                headers={'x-goog-api-key': key}, json=payload, timeout=25,
            )
            if response.status_code not in {500, 502, 503, 504} or attempt == 1:
                break
            time.sleep(0.5)
        response.raise_for_status()
        result = response.json()
        candidate = result.get('candidates', [{}])[0]
        if candidate.get('finishReason', 'STOP') != 'STOP':
            raise GoogleUnavailable('incomplete_or_blocked')
        text = '\n'.join(
            p['text'] for p in candidate.get('content', {}).get('parts', [])
            if isinstance(p.get('text'), str) and not p.get('thought', False)
        ).strip()
        if not text:
            raise GoogleUnavailable('empty_response')
        return text
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        code = {400: 'invalid_request', 401: 'invalid_key', 403: 'access_denied',
                404: 'model_unavailable', 429: 'quota_exceeded'}.get(status, 'provider_error')
        raise GoogleUnavailable(code, http_status=status) from exc
    except (httpx.RequestError, ValueError, KeyError, IndexError, TypeError, AttributeError) as exc:
        raise GoogleUnavailable('connection_or_response_error') from exc


def parse_object(text):
    text = text.strip()
    if text.startswith('```') and text.endswith('```'):
        text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.I)[:-3].strip()
    obj = json.loads(text)
    if not isinstance(obj, dict):
        raise ValueError('Expected a JSON object')
    return obj


class GoogleGemmaAdapter:
    def generate(self, system, user):
        return generate([{'text': user}], system=system,
                        model=os.getenv('GEMMA_TEXT_MODEL', 'gemma-4-26b-a4b-it'))

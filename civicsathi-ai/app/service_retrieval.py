import json
from pathlib import Path


def all_services():
    path = Path(__file__).resolve().parents[1] / 'data' / 'services.json'
    return json.loads(path.read_text(encoding='utf8'))


DATA = all_services()


def lookup(category):
    return next((item for item in all_services() if item['category'] == category), None)

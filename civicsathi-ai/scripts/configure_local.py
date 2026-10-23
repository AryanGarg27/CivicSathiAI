"""Create local configuration without overwriting existing settings or printing secrets."""
from pathlib import Path
from dotenv import dotenv_values, set_key, unset_key

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / '.env'
if not path.exists():
    path.write_text((ROOT / '.env.example').read_text(encoding='utf8'), encoding='utf8')
values = dotenv_values(path)
if values.get('ADMIN_TOKEN'):
    unset_key(path, 'ADMIN_TOKEN')
if values.get('STAFF_EMAILS') is None:
    set_key(path, 'STAFF_EMAILS', '')
print('Local .env ready. Existing AI and database settings preserved; obsolete shared admin token removed.')

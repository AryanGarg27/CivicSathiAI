import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

_default_data_dir = os.getenv('RAILWAY_VOLUME_MOUNT_PATH', str(Path(__file__).resolve().parents[1]))
DB = Path(os.getenv('DB_PATH', str(Path(_default_data_dir) / 'civicsathi.db')))


@contextmanager
def connect():
    DB.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(DB), timeout=10)
    connection.row_factory = sqlite3.Row
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def initialize():
    with connect() as c:
        c.execute('PRAGMA journal_mode=WAL')
        c.execute('CREATE TABLE IF NOT EXISTS cases (id TEXT PRIMARY KEY, category TEXT NOT NULL, summary TEXT NOT NULL, location TEXT, status TEXT NOT NULL, created_at TEXT NOT NULL)')
        c.execute('CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL)')
        # Additive migration preserves existing demo cases.
        existing = {r['name'] for r in c.execute('PRAGMA table_info(cases)')}
        for name, definition in [('photo_id', 'TEXT'), ('language', "TEXT DEFAULT 'unknown'"), ('request_id', 'TEXT')]:
            if name not in existing:
                c.execute(f'ALTER TABLE cases ADD COLUMN {name} {definition}')
        history_fields = {r['name'] for r in c.execute('PRAGMA table_info(history)')}
        if 'note' not in history_fields:
            c.execute("ALTER TABLE history ADD COLUMN note TEXT DEFAULT ''")
        c.execute('CREATE UNIQUE INDEX IF NOT EXISTS cases_request_id ON cases(request_id)')
        c.execute('CREATE INDEX IF NOT EXISTS history_case ON history(case_id)')
        c.execute('CREATE TABLE IF NOT EXISTS photos (id TEXT PRIMARY KEY, mime_type TEXT NOT NULL, content BLOB NOT NULL, analysis TEXT, created_at TEXT NOT NULL)')
        case_fields = {r['name'] for r in c.execute('PRAGMA table_info(cases)')}
        if 'user_id' not in case_fields:
            c.execute('ALTER TABLE cases ADD COLUMN user_id TEXT REFERENCES users(id)')
        photo_fields = {r['name'] for r in c.execute('PRAGMA table_info(photos)')}
        if 'user_id' not in photo_fields:
            c.execute('ALTER TABLE photos ADD COLUMN user_id TEXT REFERENCES users(id)')
        c.execute('CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, email TEXT NOT NULL UNIQUE COLLATE NOCASE, full_name TEXT NOT NULL, password_hash TEXT NOT NULL, role TEXT NOT NULL DEFAULT \'citizen\', created_at TEXT NOT NULL)')
        c.execute('CREATE TABLE IF NOT EXISTS sessions (token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE, created_at TEXT NOT NULL, expires_at TEXT NOT NULL)')
        c.execute('''CREATE TABLE IF NOT EXISTS service_requests (
            id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id), service_type TEXT NOT NULL,
            applicant_name TEXT NOT NULL, contact_phone TEXT NOT NULL, details TEXT NOT NULL,
            status TEXT NOT NULL, created_at TEXT NOT NULL)''')
        c.execute('''CREATE TABLE IF NOT EXISTS service_request_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT, request_id TEXT NOT NULL REFERENCES service_requests(id),
            status TEXT NOT NULL, created_at TEXT NOT NULL, note TEXT NOT NULL DEFAULT '')''')
        c.execute('CREATE INDEX IF NOT EXISTS cases_user_created ON cases(user_id,created_at)')
        c.execute('CREATE INDEX IF NOT EXISTS sessions_expiry ON sessions(expires_at)')
        c.execute('CREATE INDEX IF NOT EXISTS service_requests_user_created ON service_requests(user_id,created_at)')
        c.execute('CREATE INDEX IF NOT EXISTS service_request_history_request ON service_request_history(request_id)')
    cleanup_photos()


def cleanup_photos():
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    with connect() as c:
        c.execute('DELETE FROM photos WHERE created_at < ? AND id NOT IN (SELECT photo_id FROM cases WHERE photo_id IS NOT NULL)', (cutoff,))


def all_cases(limit=100, offset=0, user_id=None):
    with connect() as c:
        if user_id is None:
            query = 'SELECT id,category,summary,location,status,created_at,photo_id,language,user_id FROM cases ORDER BY created_at DESC LIMIT ? OFFSET ?'
            args = (limit, offset)
        else:
            query = 'SELECT id,category,summary,location,status,created_at,photo_id,language,user_id FROM cases WHERE user_id=? ORDER BY created_at DESC LIMIT ? OFFSET ?'
            args = (user_id, limit, offset)
        return [dict(r) for r in c.execute(query, args)]


def get_case(case_id):
    with connect() as c:
        row = c.execute('SELECT id,category,summary,location,status,created_at,photo_id,language,user_id FROM cases WHERE id=?', (case_id,)).fetchone()
        if not row:
            return None
        obj = dict(row)
        obj['history'] = [dict(r) for r in c.execute('SELECT status,created_at,note FROM history WHERE case_id=? ORDER BY id', (case_id,))]
        if obj['photo_id']:
            photo = c.execute('SELECT analysis FROM photos WHERE id=?', (obj['photo_id'],)).fetchone()
            obj['photo_analysis'] = json.loads(photo['analysis']) if photo and photo['analysis'] else None
        return obj


def get_photo(photo_id, user_id=None):
    with connect() as c:
        if user_id is None:
            row = c.execute('SELECT * FROM photos WHERE id=?', (str(photo_id),)).fetchone()
        else:
            row = c.execute('SELECT * FROM photos WHERE id=? AND user_id=?', (str(photo_id), user_id)).fetchone()
        if not row:
            return None
        obj = dict(row)
        obj['analysis'] = json.loads(obj['analysis']) if obj['analysis'] else None
        return obj


def service_requests(user_id=None, limit=100):
    with connect() as c:
        if user_id is None:
            rows = c.execute('SELECT * FROM service_requests ORDER BY created_at DESC LIMIT ?', (limit,)).fetchall()
        else:
            rows = c.execute('SELECT * FROM service_requests WHERE user_id=? ORDER BY created_at DESC LIMIT ?', (user_id, limit)).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item['details'] = json.loads(item['details'])
            item['history'] = [dict(h) for h in c.execute('SELECT status,created_at,note FROM service_request_history WHERE request_id=? ORDER BY id', (item['id'],))]
            result.append(item)
        return result


def get_service_request(request_id):
    items = service_requests(limit=1000)
    return next((item for item in items if item['id'] == request_id), None)

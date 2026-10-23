"""Password hashing and opaque, database-backed login sessions."""
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from app.database import connect

SESSION_DAYS = 14


def password_hash(password, salt=None):
    salt = salt or secrets.token_bytes(16)
    derived = hashlib.scrypt(password.encode('utf-8'), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return 'scrypt$' + salt.hex() + '$' + derived.hex()


def verify_password(password, encoded):
    try:
        algorithm, salt, expected = encoded.split('$')
        if algorithm != 'scrypt':
            return False
        actual = password_hash(password, bytes.fromhex(salt)).split('$')[2]
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def session_digest(token):
    return hashlib.sha256(token.encode('ascii')).hexdigest()


def create_session(user_id):
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    expires = now + timedelta(days=SESSION_DAYS)
    with connect() as c:
        c.execute('DELETE FROM sessions WHERE expires_at < ?', (now.isoformat(),))
        c.execute('INSERT INTO sessions(token_hash,user_id,created_at,expires_at) VALUES (?,?,?,?)',
                  (session_digest(token), user_id, now.isoformat(), expires.isoformat()))
    return token, expires


def current_user(token):
    if not token or len(token) > 100:
        return None
    with connect() as c:
        row = c.execute('SELECT users.id,users.email,users.full_name,users.role FROM sessions JOIN users ON users.id=sessions.user_id WHERE sessions.token_hash=? AND sessions.expires_at>?',
                        (session_digest(token), datetime.now(timezone.utc).isoformat())).fetchone()
        return dict(row) if row else None


def revoke_session(token):
    if token:
        with connect() as c:
            c.execute('DELETE FROM sessions WHERE token_hash=?', (session_digest(token),))


def assigned_role(email):
    staff = {x.strip().casefold() for x in os.getenv('STAFF_EMAILS', '').split(',') if x.strip()}
    return 'staff' if email.casefold() in staff else 'citizen'

import base64
import hmac
import json
import os
import time
from collections import defaultdict, deque
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID
from fastapi import FastAPI, HTTPException, Header, Query, Request, Response as FastResponse
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from app.schemas import IntakeRequest, SubmitRequest, UpdateRequest, PhotoRequest, Draft, RegisterRequest, LoginRequest, ServiceRequest
from app.agent_harness import CivicHarness, extract_location
from app.permissions import require
from app.database import initialize, connect, all_cases, get_case, get_photo, cleanup_photos, service_requests, get_service_request
from app.duplicate_detection import find_duplicates
from app.audit_log import append
from app.service_retrieval import all_services, lookup
from app.gemmavision_adapter import analyze_gemma_photo, GemmaVisionUnavailable
from app.images import normalize_image
from app.auth import password_hash, verify_password, create_session, current_user, revoke_session, assigned_role, SESSION_DAYS

ROOT = Path(__file__).resolve().parents[1]
TRANSITIONS = {
    'received': ['under_review', 'rejected'],
    'under_review': ['in_progress', 'resolved', 'rejected'],
    'in_progress': ['under_review', 'resolved', 'rejected'],
    'resolved': ['under_review'], 'rejected': ['under_review'],
}
AUTH_ATTEMPTS = defaultdict(deque)


def limit_auth(request, limit):
    now = time.monotonic()
    for stale_key in [k for k, values in AUTH_ATTEMPTS.items() if not values or now - values[-1] > 600]:
        AUTH_ATTEMPTS.pop(stale_key, None)
    key = (request.client.host if request.client else 'unknown', request.url.path)
    attempts = AUTH_ATTEMPTS[key]
    while attempts and now - attempts[0] > 600:
        attempts.popleft()
    if len(attempts) >= limit:
        raise HTTPException(429, 'Too many attempts. Wait a few minutes and try again.')
    attempts.append(now)


@asynccontextmanager
async def lifespan(app):
    initialize()
    yield


app = FastAPI(title='CivicSathi AI', version='0.2.0', lifespan=lifespan)
app.mount('/static', StaticFiles(directory=str(ROOT / 'web')), name='static')


@app.middleware('http')
async def protect_local_app(request: Request, call_next):
    # Browsers on another site must not trigger local writes or spend API quota.
    origin = request.headers.get('origin')
    if request.method in {'POST', 'PATCH', 'PUT', 'DELETE'} and origin and origin != str(request.base_url).rstrip('/'):
        return JSONResponse({'detail': 'Cross-origin writes are not allowed'}, status_code=403)
    if request.method in {'POST', 'PATCH', 'PUT'}:
        size = 0
        chunks = []
        async for chunk in request.stream():
            size += len(chunk)
            if size > 3_500_000:
                return JSONResponse({'detail': 'Request exceeds upload limit'}, status_code=413)
            chunks.append(chunk)
        request._body = b''.join(chunks)
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Content-Security-Policy'] = "default-src 'self'; img-src 'self' data: blob:; style-src 'self'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    if request.url.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-store'
    return response


@app.get('/')
@app.get('/services')
@app.get('/report')
@app.get('/track')
@app.get('/account')
@app.get('/sign-in')
@app.get('/sign-up')
@app.get('/staff')
@app.get('/apply')
@app.get('/help')
@app.get('/ask')
def page(request: Request):
    names = {'/': 'index.html', '/services': 'services.html', '/report': 'report.html',
             '/track': 'track.html', '/account': 'account.html', '/sign-in': 'auth.html',
             '/sign-up': 'auth.html', '/staff': 'staff.html', '/apply': 'apply.html',
             '/help': 'help.html', '/ask': 'ask.html'}
    response = FileResponse(ROOT / 'web' / names[request.url.path])
    response.headers['X-Page-Mode'] = 'sign-up' if request.url.path == '/sign-up' else 'sign-in'
    return response


@app.get('/api/health')
def health():
    return {'status': 'ok', 'model_provider': os.getenv('TEXT_PROVIDER', os.getenv('MODEL_PROVIDER', 'google-gemma')),
            'vision_model': os.getenv('GEMMA_VISION_MODEL', 'gemma-4-26b-a4b-it'),
            'google_configured': bool(os.getenv('GEMINI_API_KEY', '').strip()),
            'authentication': 'individual-accounts',
            'official_integration': False}


@app.get('/api/services')
def services():
    return all_services()


def user_from_request(request):
    user = current_user(request.cookies.get('civic_session'))
    if not user:
        raise HTTPException(401, 'Sign in to continue.')
    return user


def cookie_is_secure(request):
    forwarded = request.headers.get('x-forwarded-proto', '').split(',')[0].strip().casefold()
    return request.url.scheme == 'https' or forwarded == 'https'


@app.get('/api/auth/me')
def auth_me(request: Request):
    user = current_user(request.cookies.get('civic_session'))
    return {'authenticated': bool(user), 'user': user}


@app.post('/api/auth/register', status_code=201)
def auth_register(body: RegisterRequest, request: Request, response: FastResponse):
    limit_auth(request, 8)
    email = body.email.strip().casefold()
    if '@' not in email or email.startswith('@') or email.endswith('@'):
        raise HTTPException(422, 'Enter a valid email address.')
    if len(body.password) < 12 or not any(ch.isalpha() for ch in body.password) or not any(ch.isdigit() for ch in body.password):
        raise HTTPException(422, 'Password must be at least 12 characters and include a letter and a number.')
    user_id = str(uuid.uuid4())
    try:
        with connect() as c:
            c.execute('INSERT INTO users(id,email,full_name,password_hash,role,created_at) VALUES (?,?,?,?,?,?)',
                      (user_id, email, body.full_name.strip(), password_hash(body.password), assigned_role(email), datetime.now(timezone.utc).isoformat()))
    except Exception as exc:
        if 'unique' in str(exc).casefold():
            raise HTTPException(409, 'An account with this email already exists.') from exc
        raise
    token, expires = create_session(user_id)
    response.set_cookie('civic_session', token, httponly=True, secure=cookie_is_secure(request),
                        samesite='lax', path='/', max_age=SESSION_DAYS * 86400)
    append('user_registered', {'user_id': user_id, 'role': assigned_role(email)})
    return {'authenticated': True, 'user': {'id': user_id, 'email': email, 'full_name': body.full_name.strip(), 'role': assigned_role(email)}}


@app.post('/api/auth/login')
def auth_login(body: LoginRequest, request: Request, response: FastResponse):
    limit_auth(request, 15)
    email = body.email.strip().casefold()
    with connect() as c:
        row = c.execute('SELECT id,email,full_name,password_hash,role FROM users WHERE email=?', (email,)).fetchone()
    if not row or not verify_password(body.password, row['password_hash']):
        raise HTTPException(401, 'Email or password is incorrect.')
    token, _ = create_session(row['id'])
    response.set_cookie('civic_session', token, httponly=True, secure=cookie_is_secure(request),
                        samesite='lax', path='/', max_age=SESSION_DAYS * 86400)
    append('user_login', {'user_id': row['id']})
    return {'authenticated': True, 'user': {'id': row['id'], 'email': row['email'], 'full_name': row['full_name'], 'role': row['role']}}


@app.post('/api/auth/logout')
def auth_logout(request: Request, response: FastResponse):
    revoke_session(request.cookies.get('civic_session'))
    response.delete_cookie('civic_session', path='/', httponly=True, secure=cookie_is_secure(request), samesite='lax')
    return {'authenticated': False}


def enrich(draft, mode, user_id, **extra):
    return {'draft': draft, 'mode': mode, 'service': lookup(draft.category),
            'possible_duplicates': find_duplicates(draft, all_cases(limit=1000, user_id=user_id)), **extra}


@app.post('/api/intake')
def intake(body: IntakeRequest, request: Request):
    user = user_from_request(request)
    photo = get_photo(body.photo_id, user['id']) if body.photo_id else None
    if body.photo_id and not photo:
        raise HTTPException(404, 'Photo expired or was not found. Please upload it again.')
    analysis = photo['analysis'] if photo else None
    if analysis:
        # Photo evidence already has a validated category; no second LLM call is needed.
        location = extract_location(body.text)
        summary = analysis['description'] + ('\nCitizen: ' + body.text if body.text else '')
        draft = Draft(category=analysis['category'], summary=summary[:500],
                      location=location, missing_fields=[] if location else ['location'],
                      photo_id=body.photo_id, language='citizen_text' if body.text else 'english')
        return enrich(draft, 'photo-assisted', user['id'], photo_analysis=analysis)
    if len(body.text) < 5:
        raise HTTPException(400, 'Describe the issue in at least 5 characters, or analyze a photograph first.')
    result = CivicHarness().intake(body.text)
    result['draft'].photo_id = body.photo_id
    return enrich(result['draft'], result['mode'], user['id'], provider=result['provider'])


@app.post('/api/duplicates')
def duplicates(body: Draft, request: Request):
    user = user_from_request(request)
    return find_duplicates(body, all_cases(limit=1000, user_id=None if user['role'] == 'staff' else user['id']))


@app.post('/api/analyze-photo')
def photo(body: PhotoRequest, request: Request):
    user = user_from_request(request)
    try:
        content, mime = normalize_image(body.image_base64, body.mime_type)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    analysis, code, upstream_status = None, None, None
    try:
        analysis = analyze_gemma_photo(base64.b64encode(content).decode(), mime, body.text)
    except GemmaVisionUnavailable as exc:
        code = exc.code
        upstream_status = exc.http_status
    cleanup_photos()
    photo_id = str(uuid.uuid4())
    with connect() as c:
        c.execute('INSERT INTO photos(id,mime_type,content,analysis,created_at,user_id) VALUES (?,?,?,?,?,?)',
                  (photo_id, mime, content, json.dumps(analysis) if analysis else None, datetime.now(timezone.utc).isoformat(), user['id']))
    append('photo_analysis', {'photo_id': photo_id, 'available': bool(analysis), 'reason': code, 'upstream_status': upstream_status})
    return {'status': 'analyzed' if analysis else 'unavailable', 'analysis_available': bool(analysis),
            'analysis': analysis, 'photo_id': photo_id, 'reason': code,
            'message': 'Review the suggested findings.' if analysis else 'AI photo analysis is unavailable. Your photo can still be attached; describe the issue manually.'}


@app.get('/api/photos/{photo_id}')
def photo_content(photo_id: UUID, request: Request):
    user = user_from_request(request)
    item = get_photo(photo_id, user['id'])
    if not item:
        raise HTTPException(404, 'Photo not found')
    return Response(item['content'], media_type=item['mime_type'])


@app.post('/api/cases', status_code=201)
def submit(body: SubmitRequest, request: Request):
    user = user_from_request(request)
    require(user['role'], 'submit')
    if not body.confirmed:
        raise HTTPException(400, 'Citizen confirmation required')
    draft = body.draft
    if draft.category == 'other':
        raise HTTPException(400, 'The request could not be matched to a service. Add a little more detail and try again.')
    if not draft.location or not draft.location.strip():
        raise HTTPException(400, 'Add the location or nearest landmark before submitting.')
    case_id = 'DEMO-' + uuid.uuid4().hex.upper()
    now = datetime.now(timezone.utc).isoformat()
    photo_id = str(draft.photo_id) if draft.photo_id else None
    with connect() as c:
        c.execute('BEGIN IMMEDIATE')
        existing = c.execute('SELECT * FROM cases WHERE request_id=? AND user_id=?', (str(body.request_id), user['id'])).fetchone()
        if existing:
            if any(existing[k] != v for k, v in {'category': draft.category, 'summary': draft.summary, 'location': draft.location, 'photo_id': photo_id}.items()):
                raise HTTPException(409, 'This request was already submitted with different details. Start a new complaint.')
            case_id = existing['id']
        else:
            if photo_id and not c.execute('SELECT id FROM photos WHERE id=? AND user_id=?', (photo_id, user['id'])).fetchone():
                raise HTTPException(400, 'Photo expired. Please upload it again.')
            c.execute('INSERT INTO cases(id,category,summary,location,status,created_at,photo_id,language,request_id,user_id) VALUES (?,?,?,?,?,?,?,?,?,?)',
                      (case_id, draft.category, draft.summary, draft.location, 'received', now, photo_id, draft.language, str(body.request_id), user['id']))
            c.execute('INSERT INTO history(case_id,status,created_at,note) VALUES (?,?,?,?)', (case_id, 'received', now, 'Created locally after citizen confirmation.'))
    append('case_created', {'id': case_id, 'category': draft.category})
    return get_case(case_id)


@app.get('/api/cases/{case_id}')
def case(case_id: str, request: Request):
    user = user_from_request(request)
    item = get_case(case_id)
    if not item or (item['user_id'] != user['id'] and user['role'] != 'staff'):
        raise HTTPException(404, 'Case not found')
    return item


@app.get('/api/admin/cases')
def admin_cases(request: Request, offset: int = Query(0, ge=0)):
    user = user_from_request(request)
    if user['role'] != 'staff':
        raise HTTPException(403, 'Staff account required.')
    return {'cases': all_cases(limit=100, offset=offset), 'transitions': TRANSITIONS}


@app.patch('/api/admin/cases/{case_id}')
def update(case_id: str, body: UpdateRequest, request: Request):
    user = user_from_request(request)
    if user['role'] != 'staff':
        raise HTTPException(403, 'Staff account required.')
    now = datetime.now(timezone.utc).isoformat()
    with connect() as c:
        c.execute('BEGIN IMMEDIATE')
        item = c.execute('SELECT status FROM cases WHERE id=?', (case_id,)).fetchone()
        if not item:
            raise HTTPException(404, 'Case not found')
        if body.status not in TRANSITIONS[item['status']]:
            raise HTTPException(409, 'Status changed or transition is invalid. Refresh the staff list.')
        if body.status in {'resolved', 'rejected'} and not body.note:
            raise HTTPException(400, 'A resolution or rejection note is required.')
        c.execute('UPDATE cases SET status=? WHERE id=?', (body.status, case_id))
        c.execute('INSERT INTO history(case_id,status,created_at,note) VALUES (?,?,?,?)', (case_id, body.status, now, body.note))
    append('case_updated', {'id': case_id, 'status': body.status})
    return get_case(case_id)


@app.get('/api/my/cases')
def my_cases(request: Request):
    user = user_from_request(request)
    # The list endpoint includes history because the Track UI renders the
    # timeline for every case. Keep the account filter from all_cases intact.
    return [get_case(item['id']) for item in all_cases(limit=100, user_id=user['id'])]


SERVICE_LABELS = {
    'health_appointment': 'GMSH-16 appointment request', 'senior_card': 'Senior citizen card',
    'disability_card': 'Disability identity card', 'old_age_pension': 'Old-age pension application',
    'widow_pension': 'Widow pension application', 'disability_pension': 'Disability pension application',
    'horticulture': 'Horticulture request',
}


@app.post('/api/service-requests', status_code=201)
def create_service_request(body: ServiceRequest, request: Request):
    user = user_from_request(request)
    if body.service_type not in SERVICE_LABELS:
        raise HTTPException(400, 'Choose a supported service.')
    if not body.contact_phone.replace('+', '').replace(' ', '').replace('-', '').isdigit():
        raise HTTPException(422, 'Enter a phone number using digits, spaces, + or hyphens.')
    details = {str(k)[:40]: str(v).strip()[:500] for k, v in body.details.items() if str(v).strip()}
    if body.service_type == 'health_appointment' and not all(details.get(k) for k in ('department', 'preferred_date')):
        raise HTTPException(422, 'Choose a department and preferred date.')
    if body.service_type == 'horticulture' and not all(details.get(k) for k in ('location', 'description')):
        raise HTTPException(422, 'Add a location and short description for the horticulture request.')
    if body.service_type not in {'health_appointment', 'horticulture'} and not details.get('beneficiary_name'):
        raise HTTPException(422, 'Enter the beneficiary name.')
    request_id = 'SRV-' + uuid.uuid4().hex[:12].upper()
    now = datetime.now(timezone.utc).isoformat()
    with connect() as c:
        c.execute('INSERT INTO service_requests(id,user_id,service_type,applicant_name,contact_phone,details,status,created_at) VALUES (?,?,?,?,?,?,?,?)',
                  (request_id, user['id'], body.service_type, body.applicant_name.strip(), body.contact_phone.strip(), json.dumps(details), 'received', now))
        c.execute('INSERT INTO service_request_history(request_id,status,created_at,note) VALUES (?,?,?,?)',
                  (request_id, 'received', now, 'Request recorded in the CivicSathi demo. Not submitted to a government system.'))
    append('service_request_created', {'id': request_id, 'service_type': body.service_type, 'user_id': user['id']})
    return get_service_request(request_id)


@app.get('/api/my/service-requests')
def my_service_requests(request: Request):
    user = user_from_request(request)
    return service_requests(user_id=user['id'])


@app.get('/api/my/requests/{request_id}')
def my_request_status(request_id: str, request: Request):
    user = user_from_request(request)
    if request_id.startswith('SRV-'):
        item = get_service_request(request_id)
        if not item or (item['user_id'] != user['id'] and user['role'] != 'staff'):
            raise HTTPException(404, 'Request not found in your account.')
        return {'id': item['id'], 'kind': SERVICE_LABELS.get(item['service_type'], 'Service request'),
                'status': item['status'], 'created_at': item['created_at'], 'history': item['history']}
    item = get_case(request_id)
    if not item or (item['user_id'] != user['id'] and user['role'] != 'staff'):
        raise HTTPException(404, 'Request not found in your account.')
    return {'id': item['id'], 'kind': lookup(item['category'])['name'] if lookup(item['category']) else item['category'],
            'status': item['status'], 'created_at': item['created_at'], 'location': item['location'],
            'summary': item['summary'], 'history': item['history']}


@app.get('/api/admin/service-requests')
def admin_service_requests(request: Request):
    user = user_from_request(request)
    if user['role'] != 'staff':
        raise HTTPException(403, 'Staff account required.')
    return {'requests': service_requests(), 'labels': SERVICE_LABELS, 'transitions': TRANSITIONS}


@app.patch('/api/admin/service-requests/{request_id}')
def update_service_request(request_id: str, body: UpdateRequest, request: Request):
    user = user_from_request(request)
    if user['role'] != 'staff':
        raise HTTPException(403, 'Staff account required.')
    now = datetime.now(timezone.utc).isoformat()
    with connect() as c:
        c.execute('BEGIN IMMEDIATE')
        item = c.execute('SELECT status FROM service_requests WHERE id=?', (request_id,)).fetchone()
        if not item:
            raise HTTPException(404, 'Service request not found.')
        if body.status not in TRANSITIONS[item['status']]:
            raise HTTPException(409, 'Status transition is invalid. Refresh the staff list.')
        if body.status in {'resolved', 'rejected'} and not body.note:
            raise HTTPException(400, 'A resolution or rejection note is required.')
        c.execute('UPDATE service_requests SET status=? WHERE id=?', (body.status, request_id))
        c.execute('INSERT INTO service_request_history(request_id,status,created_at,note) VALUES (?,?,?,?)', (request_id, body.status, now, body.note))
    append('service_request_updated', {'id': request_id, 'status': body.status})
    return get_service_request(request_id)

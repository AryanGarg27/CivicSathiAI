import base64
import io
import json
import uuid
import httpx
import pytest
from PIL import Image
from fastapi.testclient import TestClient
from app import database, google_client
from app.main import app
from app.agent_harness import CivicHarness
from app.gemmavision_adapter import analyze_gemma_photo

ANALYSIS = {'description': 'A depression is visible in the road surface.',
            'category': 'grievance', 'visible_evidence': ['Broken road surface'],
            'uncertainty': 'Depth and exact location cannot be determined.',
            'needs_clarification': True, 'follow_up_question': 'Where is this road?'}
@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(database, 'DB', tmp_path / 'cases.db')
    monkeypatch.setenv('STAFF_EMAILS', 'staff@example.test')
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    monkeypatch.setenv('TEXT_PROVIDER', 'google-gemma')
    with TestClient(app) as client:
        response = client.post('/api/auth/register', json={'email':'citizen@example.test','full_name':'Demo Citizen','password':'citizen-demo-password-82'})
        assert response.status_code == 201
        yield client


def login_staff(client):
    client.post('/api/auth/logout')
    response = client.post('/api/auth/register', json={'email':'staff@example.test','full_name':'Demo Staff','password':'staff-demo-password-82'})
    assert response.status_code == 201


def photo_payload():
    output = io.BytesIO()
    Image.new('RGB', (32, 24), 'gray').save(output, format='PNG')
    return {'image_base64': base64.b64encode(output.getvalue()).decode(), 'mime_type': 'image/png'}


def submit_payload(draft):
    return {'draft': draft, 'confirmed': True, 'request_id': str(uuid.uuid4())}


def test_complete_photo_to_staff_to_tracking(client, monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY', 'test-key-not-real')
    calls = []
    def google_response(url, **kwargs):
        calls.append(kwargs)
        return httpx.Response(200, request=httpx.Request('POST', url), json={
            'candidates': [{'finishReason': 'STOP', 'content': {'parts': [
                {'thought': True, 'text': 'private reasoning'}, {'text': json.dumps(ANALYSIS)}]}}]})
    monkeypatch.setattr(google_client.httpx, 'post', google_response)
    photo = client.post('/api/analyze-photo', json=photo_payload()).json()
    assert photo['analysis_available'] and photo['analysis']['category'] == 'grievance'
    sent = calls[0]['json']['contents'][0]['parts'][1]['inline_data']
    assert sent['mime_type'] == 'image/jpeg'
    assert 'private reasoning' not in json.dumps(photo)
    intake = client.post('/api/intake', json={'text': 'Sector 22 near bus stop', 'photo_id': photo['photo_id']})
    assert intake.status_code == 200
    assert len(calls) == 1  # No second cloud call for a photo-derived draft.
    draft = intake.json()['draft']
    assert draft['location'] == 'Sector 22, Chandigarh'
    assert ANALYSIS['description'] in draft['summary']
    assert draft['photo_id'] == photo['photo_id']
    draft['summary'] = ANALYSIS['description']
    body = submit_payload(draft)
    created = client.post('/api/cases', json=body)
    assert created.status_code == 201, created.text
    item = created.json()
    assert client.post('/api/cases', json=body).json()['id'] == item['id']
    assert client.get('/api/photos/' + item['photo_id']).headers['content-type'] == 'image/jpeg'
    login_staff(client)
    cases = client.get('/api/admin/cases').json()['cases']
    assert len(cases) == 1
    for status in ['under_review', 'in_progress', 'resolved']:
        response = client.patch('/api/admin/cases/' + item['id'],
                                json={'status': status, 'note': 'Demo repair recorded.'})
        assert response.status_code == 200, response.text
    tracked = client.get('/api/cases/' + item['id']).json()
    assert tracked['status'] == 'resolved'
    assert len(tracked['history']) == 4
    assert tracked['photo_analysis']['description'] == ANALYSIS['description']
    assert client.post('/api/duplicates', json=draft).json()[0]['id'] == item['id']
    # Reopening the database preserves case and evidence.
    database.initialize()
    assert database.get_case(item['id'])['status'] == 'resolved'


def test_photo_only_and_offline_paths(client, monkeypatch):
    photo = client.post('/api/analyze-photo', json=photo_payload()).json()
    assert not photo['analysis_available'] and photo['reason'] == 'not_configured'
    assert client.post('/api/intake', json={'photo_id': photo['photo_id']}).status_code == 400
    intake = client.post('/api/intake', json={'text': 'Garbage at Sector 17', 'photo_id': photo['photo_id']}).json()
    assert intake['mode'] == 'safe-fallback'
    assert intake['draft']['photo_id'] == photo['photo_id']
    assert client.post('/api/cases', json=submit_payload(intake['draft'])).status_code == 201
    monkeypatch.setattr('app.main.analyze_gemma_photo', lambda *args: ANALYSIS)
    photo = client.post('/api/analyze-photo', json=photo_payload()).json()
    draft = client.post('/api/intake', json={'photo_id': photo['photo_id']}).json()['draft']
    assert draft['summary'] == ANALYSIS['description'] and draft['location'] is None


def test_invalid_uploads_and_output(client, monkeypatch):
    bad = photo_payload(); bad['image_base64'] = '!' * 100
    assert client.post('/api/analyze-photo', json=bad).status_code == 400
    bad = photo_payload(); bad['mime_type'] = 'image/jpeg'
    assert client.post('/api/analyze-photo', json=bad).status_code == 400
    bad = photo_payload(); bad['mime_type'] = 'image/svg+xml'
    assert client.post('/api/analyze-photo', json=bad).status_code == 422
    monkeypatch.setattr('app.gemmavision_adapter.generate', lambda *a, **k: '{"category":"imaginary"}')
    response = client.post('/api/analyze-photo', json=photo_payload()).json()
    assert response['reason'] == 'invalid_output' and response['analysis'] is None


def test_human_confirmation_and_permissions(client):
    draft = client.post('/api/intake', json={'text': 'Broken streetlight in Sector 22'}).json()['draft']
    assert draft['category'] == 'grievance'
    body = submit_payload(draft); body['confirmed'] = False
    assert client.post('/api/cases', json=body).status_code == 400
    body['confirmed'] = True; body['draft']['location'] = '   '
    assert client.post('/api/cases', json=body).status_code == 400
    body['draft']['location'] = 'Sector 22'
    item = client.post('/api/cases', json=body).json()
    assert client.get('/api/admin/cases').status_code == 403
    assert client.patch('/api/admin/cases/' + item['id'], json={'status': 'resolved'}).status_code == 403
    body['draft']['summary'] = 'Different complaint'
    assert client.post('/api/cases', json=body).status_code == 409
    login_staff(client)
    assert client.patch('/api/admin/cases/' + item['id'], json={'status': 'resolved', 'note': 'done'}).status_code == 409
    assert client.patch('/api/admin/cases/' + item['id'], json={'status': 'rejected'}).status_code == 400


def test_request_bounds_and_cross_origin(client):
    assert client.post('/api/intake', json={'text': 'x' * 3001}).status_code == 422
    assert client.post('/api/intake', json={'text': '   '}).status_code == 400
    assert client.post('/api/intake', content=b'x' * 3_500_001).status_code == 413
    assert client.post('/api/intake', headers={'Origin': 'https://unrelated.example'}, json={'text': 'pothole'}).status_code == 403
    assert client.get('/api/health').headers['cache-control'] == 'no-store'


@pytest.mark.parametrize('status,code', [(403,'access_denied'), (404,'model_unavailable'), (429,'quota_exceeded'), (503,'provider_error')])
def test_upstream_errors_are_sanitized(monkeypatch, status, code):
    monkeypatch.setenv('GEMINI_API_KEY', 'private-test-secret')
    monkeypatch.setattr(google_client.httpx, 'post', lambda url, **kwargs: httpx.Response(status,
                        request=httpx.Request('POST', url), text='private upstream body'))
    with pytest.raises(google_client.GoogleUnavailable) as error:
        analyze_gemma_photo('abc', 'image/jpeg')
    assert str(error.value) == code


def test_truncated_google_output_rejected(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY', 'test-key')
    monkeypatch.setattr(google_client.httpx, 'post', lambda url, **kwargs: httpx.Response(200,
        request=httpx.Request('POST', url), json={'candidates': [{'finishReason': 'MAX_TOKENS', 'content': {'parts': [{'text': '{}'}]}}]}))
    with pytest.raises(google_client.GoogleUnavailable, match='incomplete_or_blocked'):
        analyze_gemma_photo('abc', 'image/jpeg')


def test_transient_google_failure_retried_once(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY', 'test-key')
    monkeypatch.setattr(google_client.time, 'sleep', lambda _: None)
    calls = []
    def respond(url, **kwargs):
        calls.append(url)
        if len(calls) == 1:
            return httpx.Response(503, request=httpx.Request('POST', url))
        return httpx.Response(200, request=httpx.Request('POST', url), json={
            'candidates': [{'content': {'parts': [{'text': json.dumps(ANALYSIS)}]}}]})
    monkeypatch.setattr(google_client.httpx, 'post', respond)
    assert analyze_gemma_photo('abc', 'image/jpeg')['category'] == 'grievance'
    assert len(calls) == 2


def test_existing_database_migrates_without_loss(tmp_path, monkeypatch):
    monkeypatch.setattr(database, 'DB', tmp_path / 'legacy.db')
    with database.connect() as c:
        c.execute('CREATE TABLE cases (id TEXT PRIMARY KEY, category TEXT NOT NULL, summary TEXT NOT NULL, location TEXT, status TEXT NOT NULL, created_at TEXT NOT NULL)')
        c.execute("INSERT INTO cases VALUES ('DEMO-OLD','grievance','Old complaint','Sector 1','received','2026-01-01')")
    database.initialize(); database.initialize()
    assert database.get_case('DEMO-OLD')['summary'] == 'Old complaint'


def test_expired_unsubmitted_photos_are_cleaned(client):
    photo = client.post('/api/analyze-photo', json=photo_payload()).json()
    with database.connect() as c:
        c.execute("UPDATE photos SET created_at='2000-01-01' WHERE id=?", (photo['photo_id'],))
    database.cleanup_photos()
    assert client.get('/api/photos/' + photo['photo_id']).status_code == 404


def test_same_words_in_different_sectors_are_not_duplicates():
    from app.schemas import Draft
    from app.duplicate_detection import find_duplicates
    assert find_duplicates(Draft(category='grievance', summary='Broken streetlight', location='Sector 22'),
        [{'id':'test','category':'grievance','summary':'Broken streetlight','location':'Sector 17'}]) == []

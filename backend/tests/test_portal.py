import json
from datetime import timedelta
import pytest
from fastapi import HTTPException
from sqlalchemy import select, func
from app import ai
from app.config import BACKEND_DIR, settings
from app.database import SessionLocal
from app.models import User, Book, Ticket, Message, utcnow
from app.seed import seed_data
from app.serializers import book_view
from app.security import RateLimiter, hash_password, verify_password


def test_seed_exact_records_and_idempotency(client):
    original = json.loads((BACKEND_DIR / 'data' / 'bookleaf_sample_data.json').read_text(encoding='utf-8'))
    with SessionLocal() as db:
        seed_data(db)
        assert db.scalar(select(func.count()).select_from(User).where(User.role == 'author')) == 10
        assert db.scalar(select(func.count()).select_from(Book)) == 18
        for author in original['authors']:
            user = db.get(User, author['author_id'])
            assert (user.name, user.email, user.city, user.phone, user.joined_date.isoformat()) == (
                author['name'], author['email'], author['city'], author['phone'], author['joined_date'])
            for source in author['books']:
                saved = book_view(db.get(Book, source['book_id']))
                assert {key: saved[key] for key in source} == source
        assert db.get(Book, 'BK013').mrp is None
        assert db.get(Book, 'BK016').royalty_pending == 850


def test_authentication_and_ownership(client, headers, make_ticket):
    assert client.get('/api/books').status_code == 401
    assert client.get('/api/admin/tickets', headers=headers['author']).status_code == 403
    assert client.post('/api/auth/login', json={'email': 'unknown@email.com', 'password': 'wrong'}).status_code == 401
    books = client.get('/api/books', headers=headers['author']).json()['items']
    assert {b['book_id'] for b in books} == {'BK001', 'BK002'}
    assert client.get('/api/books/BK003', headers=headers['author']).status_code == 404
    forged = client.post('/api/tickets', headers=headers['author'], json={'book_id': 'BK003', 'subject': 'Not my book', 'description': 'This should be rejected.'})
    assert forged.status_code == 404
    ticket_id = make_ticket()
    assert client.get(f'/api/tickets/{ticket_id}', headers=headers['other']).status_code == 404
    assert client.post(f'/api/tickets/{ticket_id}/messages', headers=headers['other'], json={'body': 'Unauthorized', 'version': 1}).status_code == 404
    leaked = client.get('/api/tickets', headers=headers['other']).json()['items']
    assert not leaked


def test_validation_rejects_mass_assignment_and_invalid_values(client, headers):
    response = client.post('/api/tickets', headers=headers['author'], json={'subject': 'X', 'description': ' ', 'author_id': 'AUTH002'})
    assert response.status_code == 422
    assert 'error' in response.json()
    assert client.get('/api/admin/tickets?priority=Extreme', headers=headers['admin']).status_code == 422
    assert client.get('/api/admin/tickets?date_from=2026-10-23&date_to=2026-10-20', headers=headers['admin']).status_code == 422


def test_ticket_persisted_before_ai_work(client, headers, monkeypatch, make_ticket):
    original = ai.classify
    def check_persistence(subject, description):
        with SessionLocal() as db:
            assert db.scalar(select(Ticket).where(Ticket.subject == subject)) is not None
        return original(subject, description)
    monkeypatch.setattr(ai, 'classify', check_persistence)
    ticket_id = make_ticket()
    detail = client.get(f'/api/admin/tickets/{ticket_id}', headers=headers['admin']).json()
    assert detail['triage_status'] == 'fallback'
    assert detail['triage_source'] == 'fallback'


def test_ticket_lifecycle_and_private_notes(client, headers, make_ticket):
    ticket_id = make_ticket()
    admin_path = f'/api/admin/tickets/{ticket_id}'
    author_path = f'/api/tickets/{ticket_id}'
    detail = client.get(admin_path, headers=headers['admin']).json()
    updated = client.patch(admin_path, headers=headers['admin'], json={'version': detail['version'], 'assignment': 'self', 'category': 'Royalty & Payments', 'priority': 'High', 'status': 'In Progress'})
    assert updated.status_code == 200
    assert updated.json()['assigned_to'] == 'ADMIN001'
    note = client.post(admin_path + '/messages', headers=headers['admin'], json={'version': updated.json()['version'], 'kind': 'note', 'body': 'PRIVATE_NOTE_TOKEN finance verification required'})
    assert note.status_code == 201
    draft = client.post(admin_path + '/draft', headers=headers['admin'], json={})
    assert draft.status_code == 200
    current = client.get(admin_path, headers=headers['admin']).json()
    reply = client.post(admin_path + '/messages', headers=headers['admin'], json={'version': current['version'], 'body': 'We will verify the applicable royalty period with the team.', 'resolve': True})
    assert reply.status_code == 201 and reply.json()['status'] == 'Resolved'
    visible = client.get(author_path, headers=headers['author'])
    assert 'PRIVATE_NOTE_TOKEN' not in visible.text
    assert 'draft_text' not in visible.text and 'events' not in visible.json() and 'ai_error' not in visible.json()
    assert len(visible.json()['messages']) == 1
    reopened = client.post(author_path + '/messages', headers=headers['author'], json={'version': visible.json()['version'], 'body': 'Thank you; I have another question about this period.'})
    assert reopened.status_code == 201 and reopened.json()['status'] == 'Open'
    closed = client.patch(admin_path, headers=headers['admin'], json={'version': reopened.json()['version'], 'status': 'Closed'})
    assert closed.status_code == 200
    assert client.post(author_path + '/messages', headers=headers['author'], json={'version': closed.json()['version'], 'body': 'A new question'}).status_code == 409


def test_author_cannot_add_note_or_resolve(client, headers, make_ticket):
    ticket_id = make_ticket()
    path = f'/api/tickets/{ticket_id}'
    version = client.get(path, headers=headers['author']).json()['version']
    for payload in [{'kind': 'note'}, {'resolve': True}]:
        assert client.post(path + '/messages', headers=headers['author'], json={'body': 'Forbidden change', 'version': version, **payload}).status_code == 403
    assert client.post(f'/api/admin/tickets/{ticket_id}/draft', headers=headers['author'], json={}).status_code == 403


def test_optimistic_concurrency(client, headers, make_ticket):
    ticket_id = make_ticket()
    path = f'/api/admin/tickets/{ticket_id}'
    version = client.get(path, headers=headers['admin']).json()['version']
    assert client.patch(path, headers=headers['admin'], json={'version': version, 'status': 'In Progress'}).status_code == 200
    stale = client.patch(path, headers=headers['admin'], json={'version': version, 'status': 'Closed'})
    assert stale.status_code == 409
    assert client.get(path, headers=headers['admin']).json()['status'] == 'In Progress'


def test_queue_filters_ordering_and_pagination(client, headers, make_ticket):
    first = make_ticket(subject='Older normal query')
    high = make_ticket(subject='Urgent ISBN mismatch', description='A different ISBN is linked to the wrong book on Amazon.')
    resolved = make_ticket(subject='Finished request')
    with SessionLocal() as db:
        db.get(Ticket, first).created_at = utcnow() - timedelta(days=3)
        db.get(Ticket, resolved).status = 'Resolved'
        db.get(Ticket, resolved).priority = 'Critical'
        db.commit()
    result = client.get('/api/admin/tickets', headers=headers['admin']).json()
    assert [t['id'] for t in result['items']] == [high, first, resolved]
    result = client.get('/api/admin/tickets?priority=High&category=ISBN%20%26%20Metadata%20Issues', headers=headers['admin']).json()
    assert result['total'] == 1 and result['items'][0]['id'] == high
    assert client.get('/api/admin/tickets?q=Priya', headers=headers['admin']).json()['total'] == 3
    assert client.get('/api/admin/tickets?q=pRIyA', headers=headers['admin']).json()['total'] == 3
    assert client.get('/api/admin/tickets?date_to=9999-12-31', headers=headers['admin']).json()['total'] == 3
    assert client.get('/api/admin/tickets?page_size=1&page=2', headers=headers['admin']).json()['items'][0]['id'] == first
    overview = client.get('/api/admin/overview', headers=headers['admin']).json()
    assert overview['waiting_over_48h'] == 1 and overview['urgent'] == 1


def test_human_override_survives_retriage(client, headers, make_ticket):
    ticket_id = make_ticket(subject='ISBN mismatch', description='My ISBN is different on Amazon; please fix this issue.')
    path = f'/api/admin/tickets/{ticket_id}'
    version = client.get(path, headers=headers['admin']).json()['version']
    client.patch(path, headers=headers['admin'], json={'version': version, 'category': 'General Inquiry', 'priority': 'Low'})
    assert client.post(path + '/triage', headers=headers['admin']).status_code == 202
    detail = client.get(path, headers=headers['admin']).json()
    assert (detail['category'], detail['priority']) == ('General Inquiry', 'Low')
    assert (detail['ai_category'], detail['ai_priority']) == ('ISBN & Metadata Issues', 'High')


def test_recover_interrupted_triage(client, make_ticket):
    ticket_id = make_ticket()
    with SessionLocal() as db:
        db.get(Ticket, ticket_id).triage_status = 'pending'
        db.commit()
        ai.recover_interrupted_triage(db)
        assert db.get(Ticket, ticket_id).triage_status == 'fallback'


def test_health_api_docs_and_static_build(client):
    assert client.get('/health').json() == {'status': 'ok'}
    spec = client.get('/openapi.json').json()
    assert '/api/admin/tickets/{ticket_id}/draft' in spec['paths']
    assert 'HTTPBearer' in spec['components']['securitySchemes']
    assert client.get('/api/does-not-exist').status_code == 404


def test_password_hashing_and_rate_limit():
    encoded = hash_password('Some password!')
    assert 'Some password!' not in encoded
    assert verify_password('Some password!', encoded)
    assert not verify_password('Wrong', encoded)
    limiter = RateLimiter()
    limiter.check('x', 2)
    limiter.check('x', 2)
    with pytest.raises(HTTPException) as exc:
        limiter.check('x', 2)
    assert exc.value.status_code == 429

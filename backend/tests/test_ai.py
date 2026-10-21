import json
import httpx
import pytest
from app import ai
from app.config import settings
from app.database import SessionLocal
from app.models import Ticket, Message, utcnow


def provider_response(result):
    return {'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps(result)}}],
            'usage': {'prompt_tokens': 120, 'completion_tokens': 40}}


@pytest.mark.parametrize('text,category,priority', [
    ('The ISBN is wrong on my listing', 'ISBN & Metadata Issues', 'High'),
    ('I have not received royalties for 6 months', 'Royalty & Payments', 'High'),
    ('The print quality is blurry', 'Printing & Quality', 'High'),
    ('My published book is unavailable on Amazon', 'Distribution & Availability', 'Medium'),
    ('Any update on cover design?', 'Book Status & Production Updates', 'Medium'),
    ('Can I update my author bio?', 'General Inquiry', 'Low'),
])
def test_fallback_triage_examples(text, category, priority):
    result = ai.fallback_triage(text)
    assert (result.category.value, result.priority.value) == (category, priority)


def test_llm_classification_payload_and_validation(monkeypatch):
    monkeypatch.setattr(settings, 'openai_api_key', 'test-only-not-a-real-key')
    seen = []
    def fake(payload):
        seen.append(payload)
        return provider_response({'category': 'Royalty & Payments', 'priority': 'High', 'reason': 'Reported six months of missing royalties.'})
    monkeypatch.setattr(ai, '_provider_request', fake)
    result = ai.classify('No royalty', 'I have received no royalty for six months.')
    assert result.source == 'llm' and result.input_tokens == 120
    assert seen[0]['response_format']['json_schema']['strict'] is True
    assert seen[0]['max_completion_tokens'] == 400
    assert 'untrusted' in seen[0]['messages'][0]['content']


@pytest.mark.parametrize('failure', ['timeout', 'rate_limit', 'invalid_json', 'invalid_enum', 'refusal'])
def test_ai_failure_keeps_tickets_usable(failure, monkeypatch, client, headers, make_ticket):
    monkeypatch.setattr(settings, 'openai_api_key', 'test-only')
    def broken(payload):
        if failure == 'timeout':
            raise httpx.ReadTimeout('timeout')
        if failure == 'rate_limit':
            response = httpx.Response(429, request=httpx.Request('POST', 'https://api.openai.com/v1/chat/completions'))
            raise httpx.HTTPStatusError('rate limited', request=response.request, response=response)
        if failure == 'refusal':
            return {'choices': [{'finish_reason': 'stop', 'message': {'refusal': 'Cannot answer'}}]}
        if failure == 'invalid_enum':
            return provider_response({'category': 'Secret', 'priority': 'Extreme', 'reason': 'Bad'})
        return {'choices': []}
    monkeypatch.setattr(ai, '_provider_request', broken)
    ticket_id = make_ticket()
    path = f'/api/admin/tickets/{ticket_id}'
    detail = client.get(path, headers=headers['admin']).json()
    assert detail['triage_source'] == 'fallback'
    draft = client.post(path + '/draft', headers=headers['admin'], json={})
    assert draft.status_code == 200 and draft.json()['source'] == 'fallback'
    manual = client.post(path + '/messages', headers=headers['admin'], json={'version': draft.json()['version'], 'body': 'A manually reviewed response.'})
    assert manual.status_code == 201


def test_draft_context_isolation_cache_invalidation_and_no_auto_send(monkeypatch, client, headers, make_ticket):
    ticket_id = make_ticket()
    path = f'/api/admin/tickets/{ticket_id}'
    with SessionLocal() as db:
        db.add(Message(ticket_id=ticket_id, sender_id='ADMIN001', kind='note', body='DO_NOT_SEND_PRIVATE_NOTE'))
        db.commit()
    monkeypatch.setattr(settings, 'openai_api_key', 'test-only')
    seen = []
    def fake(payload):
        seen.append(payload)
        return provider_response({'reply': 'Hello Priya, we will verify the royalty period before confirming a date.', 'review_notes': 'Verify bank status and the applicable quarter.'})
    monkeypatch.setattr(ai, '_provider_request', fake)
    first = client.post(path + '/draft', headers=headers['admin'], json={})
    assert first.status_code == 200 and first.json()['source'] == 'llm'
    second = client.post(path + '/draft', headers=headers['admin'], json={})
    assert second.json()['cached'] and len(seen) == 1
    prompt = json.dumps(seen[0])
    assert 'DO_NOT_SEND_PRIVATE_NOTE' not in prompt
    assert 'rohit.kapoor' not in prompt and 'Code & Karma' not in prompt
    assert 'priya.sharma@email.com' not in prompt and '98765' not in prompt
    assert '80% of MRP' in prompt
    author_view = client.get(f'/api/tickets/{ticket_id}', headers=headers['author']).json()
    assert author_view['messages'] == []  # Drafting never sends a reply.
    reply = client.post(path + '/messages', headers=headers['admin'], json={'version': second.json()['version'], 'body': 'Please specify the royalty quarter.'})
    assert reply.status_code == 201
    third = client.post(path + '/draft', headers=headers['admin'], json={})
    assert not third.json()['cached'] and len(seen) == 2


def test_conversation_change_during_draft_returns_conflict(monkeypatch, client, headers, make_ticket):
    ticket_id = make_ticket()
    monkeypatch.setattr(settings, 'openai_api_key', 'test-only')
    def racing_provider(payload):
        with SessionLocal() as db:
            db.add(Message(ticket_id=ticket_id, sender_id='AUTH001', kind='reply', body='Another detail arrived while drafting.'))
            db.get(Ticket, ticket_id).updated_at = utcnow()
            db.commit()
        return provider_response({'reply': 'This draft is based on outdated conversation context.', 'review_notes': 'Check context.'})
    monkeypatch.setattr(ai, '_provider_request', racing_provider)
    response = client.post(f'/api/admin/tickets/{ticket_id}/draft', headers=headers['admin'], json={})
    assert response.status_code == 409


def test_account_threshold_and_missing_data_in_fallback(client, headers):
    response = client.post('/api/auth/login', json={'email': 'kavita.deshmukh@email.com', 'password': 'AuthorDemo!2026'})
    author = {'Authorization': 'Bearer ' + response.json()['access_token']}
    ticket_id = client.post('/api/tickets', headers=author, json={'book_id': 'BK016', 'subject': 'Pending royalty', 'description': 'Why has my royalty not been paid?'}).json()['id']
    draft = client.post(f'/api/admin/tickets/{ticket_id}/draft', headers=headers['admin'], json={}).json()
    assert '850.00' in draft['text'] and 'below the threshold' in draft['text']
    assert 'cannot confirm a payment date' in draft['text']
    assert draft['source'] == 'fallback'


def test_enabling_api_or_changing_model_invalidates_saved_draft(monkeypatch, client, headers, make_ticket):
    ticket_id = make_ticket()
    path = f'/api/admin/tickets/{ticket_id}'
    fallback = client.post(path + '/draft', headers=headers['admin'], json={}).json()
    assert fallback['source'] == 'fallback'
    monkeypatch.setattr(settings, 'openai_api_key', 'test-only')
    monkeypatch.setattr(ai, '_provider_request', lambda payload: provider_response({
        'reply': 'Hello Priya, our team will verify the royalty period and confirm the next step.', 'review_notes': 'Verify the quarter.'}))
    assert client.get(path, headers=headers['admin']).json()['draft_stale'] is True
    live = client.post(path + '/draft', headers=headers['admin'], json={}).json()
    assert live['source'] == 'llm' and live['cached'] is False
    monkeypatch.setattr(settings, 'openai_model', 'a-different-test-model')
    assert client.get(path, headers=headers['admin']).json()['draft_stale'] is True
    regenerated = client.post(path + '/draft', headers=headers['admin'], json={}).json()
    assert regenerated['cached'] is False


def test_mutations_return_current_draft_staleness(client, headers, make_ticket):
    ticket_id = make_ticket()
    path = f'/api/admin/tickets/{ticket_id}'
    draft = client.post(path + '/draft', headers=headers['admin'], json={}).json()
    changed = client.patch(path, headers=headers['admin'], json={'version': draft['version'], 'priority': 'Critical'})
    assert changed.status_code == 200 and changed.json()['draft_stale'] is True
    new_draft = client.post(path + '/draft', headers=headers['admin'], json={}).json()
    reply = client.post(path + '/messages', headers=headers['admin'], json={'version': new_draft['version'], 'body': 'Please confirm the royalty period.'})
    assert reply.status_code == 201 and reply.json()['draft_stale'] is True


def test_live_check_is_opt_in_and_reports_both_calls(monkeypatch, capsys):
    from app import verify_ai
    monkeypatch.setattr('sys.argv', ['verify_ai'])
    seen = []
    def fake(payload):
        seen.append(payload)
        if payload['response_format']['json_schema']['name'] == 'TriageResult':
            return provider_response({'category': 'Royalty & Payments', 'priority': 'High', 'reason': 'Reported missing payments.'})
        return provider_response({'reply': 'Hello Priya, we will verify the royalty period before confirming a payout date.', 'review_notes': 'Verify the quarter and bank status.'})
    monkeypatch.setattr(ai, '_provider_request', fake)
    assert verify_ai.main() == 0 and not seen
    monkeypatch.setattr('sys.argv', ['verify_ai', '--run'])
    assert verify_ai.main() == 1 and not seen
    monkeypatch.setattr(settings, 'openai_api_key', 'test-only-secret-do-not-print')
    assert verify_ai.main() == 0 and len(seen) == 2
    output = capsys.readouterr().out
    assert 'PASS: both live calls succeeded' in output
    assert 'test-only-secret-do-not-print' not in output

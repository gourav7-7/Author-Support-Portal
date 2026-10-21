import pytest
from app import ai
from app.attachments import MAX_ATTACHMENT_BYTES
from app.database import SessionLocal
from app.models import Attachment, Ticket

PDF = b'%PDF-1.4\n%PRIVATE_FILE_CONTENT\n%%EOF'
PNG = b'\x89PNG\r\n\x1a\nimage-placeholder'


def upload(client, headers, ticket_id, filename='proof.pdf', content=PDF, who='author'):
    return client.post(f'/api/tickets/{ticket_id}/attachments', params={'filename': filename},
                       headers={**headers[who], 'Content-Type': 'application/pdf'}, content=content)


def test_upload_download_ownership_and_no_blob_in_ticket_or_ai(client, headers, make_ticket):
    ticket_id = make_ticket()
    response = upload(client, headers, ticket_id, filename='C:\\fakepath\\print proof.pdf')
    assert response.status_code == 201, response.text
    attachment = response.json()
    assert attachment['filename'] == 'print proof.pdf' and attachment['size_bytes'] == len(PDF)
    path = f"/api/tickets/{ticket_id}/attachments/{attachment['id']}"
    for who in ('author', 'admin'):
        downloaded = client.get(path, headers=headers[who])
        assert downloaded.status_code == 200 and downloaded.content == PDF
        assert downloaded.headers['content-disposition'].startswith('attachment;')
        assert downloaded.headers['x-content-type-options'] == 'nosniff'
        assert downloaded.headers['cache-control'] == 'no-store'
    assert client.get(path).status_code == 401
    assert client.get(path, headers=headers['other']).status_code == 404
    assert upload(client, headers, ticket_id, who='other').status_code == 404
    detail = client.get(f'/api/tickets/{ticket_id}', headers=headers['author'])
    assert detail.json()['attachments'] == [attachment]
    assert 'PRIVATE_FILE_CONTENT' not in detail.text
    with SessionLocal() as db:
        saved = db.get(Attachment, attachment['id'])
        assert 'content' not in saved.__dict__  # Bytea/blob is deferred on ordinary queries.
        context, _ = ai.draft_context(db, db.get(Ticket, ticket_id))
        assert context['attachments'][0]['filename'] == 'print proof.pdf'
        assert 'PRIVATE_FILE_CONTENT' not in str(context)
        assert context['attachment_contents_available_to_model'] is False


@pytest.mark.parametrize('filename,content,code', [
    ('malware.exe', PDF, 415), ('photo.png', PDF, 415), ('document.pdf', b'', 422),
    ('document.pdf', b'<html>not a PDF</html>', 415), ('bad\nname.pdf', PDF, 422),
    ('photo.png', PNG, 201), ('photo.jpeg', b'\xff\xd8\xffimage', 201),
])
def test_file_validation(client, headers, make_ticket, filename, content, code):
    ticket_id = make_ticket()
    response = upload(client, headers, ticket_id, filename, content)
    assert response.status_code == code, response.text
    detail = client.get(f'/api/tickets/{ticket_id}', headers=headers['author']).json()
    assert len(detail['attachments']) == (1 if code == 201 else 0)


def test_limit_and_closed_ticket(client, headers, make_ticket):
    ticket_id = make_ticket()
    for _ in range(3):
        assert upload(client, headers, ticket_id).status_code == 201
    assert upload(client, headers, ticket_id).status_code == 409
    with SessionLocal() as db:
        db.get(Ticket, ticket_id).status = 'Closed'
        db.commit()
    assert upload(client, headers, ticket_id).status_code == 409


def test_file_size_is_bounded_with_and_without_content_length(client, headers, make_ticket):
    ticket_id = make_ticket()
    assert upload(client, headers, ticket_id, content=b'%PDF-' + b'x' * MAX_ATTACHMENT_BYTES).status_code == 413
    chunks = (chunk for chunk in [b'%PDF-', b'x' * MAX_ATTACHMENT_BYTES])
    response = upload(client, headers, ticket_id, content=chunks)
    assert response.status_code == 413
    assert not client.get(f'/api/tickets/{ticket_id}', headers=headers['author']).json()['attachments']


def test_attachment_invalidates_draft_and_fallback_acknowledges_it(client, headers, make_ticket):
    ticket_id = make_ticket(subject='Print quality problem', description='My author copies have blurry images and misaligned pages.')
    path = f'/api/admin/tickets/{ticket_id}'
    first = client.post(path + '/draft', headers=headers['admin'], json={}).json()
    assert 'attach clear photos' in first['text']
    assert client.get(path, headers=headers['admin']).json()['draft_stale'] is False
    assert upload(client, headers, ticket_id).status_code == 201
    assert client.get(path, headers=headers['admin']).json()['draft_stale'] is True
    second = client.post(path + '/draft', headers=headers['admin'], json={}).json()
    assert second['cached'] is False and 'Thank you for the supporting attachment' in second['text']
    assert 'cannot upload' not in second['text']

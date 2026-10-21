import os
import tempfile
from uuid import uuid4
import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.schema import CreateSchema, DropSchema

_test_directory = tempfile.TemporaryDirectory(prefix='bookleaf-tests-')
_schema_engine = None
_test_schema = None
_database_url = 'sqlite:///' + _test_directory.name + '/test.db'
if os.environ.get('TEST_DATABASE_URL'):
    # Explicit opt-in only. Never use the project's normal DATABASE_URL for tests.
    _url = make_url(os.environ['TEST_DATABASE_URL'].replace('postgres://', 'postgresql://', 1))
    if _url.get_backend_name() != 'postgresql':
        raise ValueError('TEST_DATABASE_URL must be PostgreSQL; omit it to use temporary SQLite.')
    _url = _url.set(drivername='postgresql+psycopg')
    _schema_engine = create_engine(_url)
    _test_schema = 'bookleaf_test_' + uuid4().hex
    with _schema_engine.begin() as connection:
        connection.execute(CreateSchema(_test_schema))
    _database_url = _url.update_query_dict({'options': '-csearch_path=' + _test_schema}).render_as_string(hide_password=False)

os.environ.update(DATABASE_URL=_database_url,
                  JWT_SECRET='test-secret-only-' + 'x' * 48, OPENAI_API_KEY='', AUTO_SEED='true',
                  ADMIN_EMAIL='admin@bookleaf.demo', DEMO_AUTHOR_PASSWORD='AuthorDemo!2026',
                  DEMO_ADMIN_PASSWORD='AdminDemo!2026')

from fastapi.testclient import TestClient
from sqlalchemy import delete
from app.main import app
from app.database import SessionLocal, engine
from app.models import Ticket, Message, AuditEvent, Attachment
from app.config import settings
from app.security import limiter


@pytest.fixture(scope='session')
def client():
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        engine.dispose()
        if _schema_engine is not None:
            with _schema_engine.begin() as connection:
                connection.execute(DropSchema(_test_schema, cascade=True))
            _schema_engine.dispose()
        _test_directory.cleanup()


@pytest.fixture(autouse=True)
def isolation(client, monkeypatch):
    monkeypatch.setattr(limiter, 'check', lambda *args, **kwargs: None)
    monkeypatch.setattr(settings, 'openai_api_key', '')
    with SessionLocal() as db:
        db.execute(delete(Attachment))
        db.execute(delete(Message))
        db.execute(delete(AuditEvent))
        db.execute(delete(Ticket))
        db.commit()


@pytest.fixture
def headers(client):
    result = {}
    for name, email, password in [('author', 'priya.sharma@email.com', 'AuthorDemo!2026'),
                                  ('other', 'rohit.kapoor@email.com', 'AuthorDemo!2026'),
                                  ('admin', 'admin@bookleaf.demo', 'AdminDemo!2026')]:
        response = client.post('/api/auth/login', json={'email': email, 'password': password})
        assert response.status_code == 200, response.text
        result[name] = {'Authorization': 'Bearer ' + response.json()['access_token']}
    return result


@pytest.fixture
def make_ticket(client, headers):
    def create(subject='Pending royalty question', description='Please help me understand my pending royalty.', book_id='BK001', who='author'):
        response = client.post('/api/tickets', headers=headers[who], json={'subject': subject, 'description': description, 'book_id': book_id})
        assert response.status_code == 201, response.text
        return response.json()['id']
    return create

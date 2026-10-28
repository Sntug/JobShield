"""R2 concurrent writes against migrated PostgreSQL, with a session per request."""
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from threading import Barrier, Event, Lock
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.core.rate_limit import reset_rate_limits
from app.db.session import get_db
from app.main import app
from tests.test_postgres_integration import (
    POSTGRES_TEST_URL, postgres_engine, isolated_schema, run_alembic_migrations,
)


@pytest.fixture
def pg_client(isolated_schema):
    engine = create_engine(POSTGRES_TEST_URL, connect_args={'options': f'-csearch_path={isolated_schema}'})
    factory = sessionmaker(bind=engine, autoflush=False)
    def override():
        with factory() as db:
            yield db
    app.dependency_overrides[get_db] = override
    reset_rate_limits()
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            yield client, engine
    finally:
        app.dependency_overrides.clear()
        reset_rate_limits()
        engine.dispose()


def account(client):
    payload = {'email': f'{uuid4().hex}@example.com', 'password': 'original_password_2026', 'full_name': 'Concurrent Test'}
    res = client.post('/api/v1/auth/register', json=payload)
    assert res.status_code == 201
    return payload, {'Authorization': 'Bearer ' + res.json()['access_token']}


def test_password_change_revokes_login_already_checking_old_password(pg_client, monkeypatch):
    import app.api.routes.auth as auth
    client, _ = pg_client
    credentials, headers = account(client)
    checked, resume = Event(), Event()
    original_verify = auth.verify_password
    def pause_after_verification(*args):
        valid = original_verify(*args)
        checked.set()
        assert resume.wait(10)
        return valid
    monkeypatch.setattr(auth, 'verify_password', pause_after_verification)
    with ThreadPoolExecutor(max_workers=2) as pool:
        login = pool.submit(client.post, '/api/v1/auth/login', json=credentials)
        try:
            assert checked.wait(10)
            change = pool.submit(client.post, '/api/v1/users/me/password', headers=headers, json={
                'old_password': credentials['password'], 'new_password': 'replacement_password_2026',
            })
            try:
                change.result(timeout=2)
            except TimeoutError:
                pass  # A locked login must finish before password rotation can proceed.
        finally:
            resume.set()
        login_result, changed = login.result(10), change.result(10)
    assert login_result.status_code == 200
    assert changed.status_code == 200
    assert client.get('/api/v1/users/me', headers={
        'Authorization': 'Bearer ' + login_result.json()['access_token'],
    }).status_code == 401
    assert client.post('/api/v1/auth/login', json=credentials).status_code == 401


def simultaneous_requests(engine, select_fragment, request):
    """Let the first two SELECTs see the same missing row before either inserts."""
    barrier, lock = Barrier(2), Lock()
    reads = 0
    def synchronize(conn, cursor, statement, parameters, context, executemany):
        nonlocal reads
        if statement.lstrip().startswith('SELECT') and select_fragment in statement:
            with lock:
                reads += 1
                wait = reads <= 2
            if wait:
                barrier.wait(10)
    event.listen(engine, 'after_cursor_execute', synchronize)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            pending = [pool.submit(request) for _ in range(2)]
            return [future.result(15) for future in pending]
    finally:
        event.remove(engine, 'after_cursor_execute', synchronize)


def test_simultaneous_save_is_idempotent(pg_client):
    client, engine = pg_client
    _, headers = account(client)
    created = client.post('/api/v1/analyses', headers=headers, json={'text': 'Công ty Mẫu tuyển Tester. Không thu phí.'})
    assert created.status_code == 201
    path = '/api/v1/saved-analyses/' + created.json()['id']
    results = simultaneous_requests(engine, 'FROM saved_analyses', lambda: client.post(path, headers=headers))
    assert [r.status_code for r in results] == [200, 200]
    assert client.get('/api/v1/saved-analyses', headers=headers).json()['total'] == 1


def test_simultaneous_registration_returns_conflict_not_server_error(pg_client):
    client, engine = pg_client
    payload = {'email': f'{uuid4().hex}@example.com', 'password': 'registration_password_2026', 'full_name': 'Concurrent Test'}
    results = simultaneous_requests(engine, 'WHERE users.email =', lambda: client.post('/api/v1/auth/register', json=payload))
    assert sorted(r.status_code for r in results) == [201, 409]
    assert client.post('/api/v1/auth/login', json=payload).status_code == 200

"""Supabase API roles must not bypass FastAPI's ownership checks."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from tests.test_postgres_integration import postgres_engine


TABLES = (
    'roles', 'users', 'access_sessions', 'saved_analyses', 'guest_sessions',
    'analyses', 'verified_employers', 'verification_sources', 'employer_claims',
    'alembic_version', 'batch_analyses', 'batch_analysis_items',
)
BATCH_TABLES = ('batch_analyses', 'batch_analysis_items')


@pytest.fixture(scope='module')
def api_storage(postgres_engine):
    schemas = ['api_privacy_' + uuid4().hex for _ in range(2)]
    created_roles = []
    try:
        with postgres_engine.begin() as connection:
            for role in ('anon', 'authenticated'):
                if not connection.scalar(text('SELECT 1 FROM pg_roles WHERE rolname = :role'), {'role': role}):
                    connection.execute(text(f'CREATE ROLE {role} NOLOGIN'))
                    created_roles.append(role)
            for schema in schemas:
                connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        for schema in schemas:
            config = Config(str(Path('alembic.ini').resolve()))
            with postgres_engine.begin() as connection:
                connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))
                config.attributes.update(connection=connection, version_table_schema=schema)
                command.upgrade(config, 'c4d5e6f7a8b9')
                connection.execute(text(f'GRANT USAGE ON SCHEMA "{schema}" TO anon, authenticated'))
                connection.execute(text(f'GRANT ALL ON ALL TABLES IN SCHEMA "{schema}" TO anon, authenticated'))
                if schema == schemas[0]:
                    connection.execute(text(
                        f'ALTER DEFAULT PRIVILEGES IN SCHEMA "{schema}" '
                        'GRANT ALL ON TABLES TO anon, authenticated'
                    ))
                    command.upgrade(config, 'head')
        yield postgres_engine, schemas
    finally:
        with postgres_engine.begin() as connection:
            for schema in schemas:
                connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
            for role in created_roles:
                connection.execute(text(f'DROP ROLE {role}'))


@pytest.mark.parametrize('role', ['anon', 'authenticated'])
def test_data_api_roles_cannot_read_write_or_truncate_backend_tables(api_storage, role):
    engine, (secured, control) = api_storage
    for table in TABLES:
        with engine.connect() as connection:
            if table not in BATCH_TABLES:
                assert connection.scalar(text('SELECT has_table_privilege(:role, :table, :privilege)'), {
                    'role': role, 'table': f'{control}.{table}', 'privilege': 'SELECT',
                })
            for privilege in ('SELECT', 'INSERT', 'UPDATE', 'DELETE', 'TRUNCATE', 'REFERENCES', 'TRIGGER'):
                assert not connection.scalar(text('SELECT has_table_privilege(:role, :table, :privilege)'), {
                    'role': role, 'table': f'{secured}.{table}', 'privilege': privilege,
                }), (role, table, privilege)
        with engine.begin() as connection:
            connection.execute(text(f'SET LOCAL ROLE {role}'))
            with pytest.raises(ProgrammingError, match='permission denied'):
                connection.execute(text(f'SELECT count(*) FROM "{secured}".{table}'))


@pytest.mark.parametrize('role', ['anon', 'authenticated'])
def test_rls_still_denies_rows_if_api_select_is_accidentally_regranted(api_storage, role):
    engine, (secured, _) = api_storage
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            now = datetime.now(timezone.utc)
            session_id = uuid4()
            batch_id = uuid4()
            connection.execute(text(f'''
                INSERT INTO "{secured}".guest_sessions (id, token_hash, created_at, expires_at)
                VALUES (:id, :token_hash, :created_at, :expires_at)
            '''), {
                'id': session_id, 'token_hash': uuid4().hex * 2,
                'created_at': now, 'expires_at': now + timedelta(hours=24),
            })
            connection.execute(text(f'''
                INSERT INTO "{secured}".batch_analyses
                    (id, session_id, user_id, status, total_items, processed_items, created_at, updated_at, expires_at)
                VALUES (:id, :session_id, NULL, 'pending', 1, 0, :created_at, :updated_at, :expires_at)
            '''), {
                'id': batch_id, 'session_id': session_id,
                'created_at': now, 'updated_at': now, 'expires_at': now + timedelta(hours=24),
            })
            connection.execute(text(f'''
                INSERT INTO "{secured}".batch_analysis_items
                    (id, batch_id, item_order, input_type, input_value, status, created_at, updated_at)
                VALUES (:id, :batch_id, 0, 'text', 'private job', 'pending', :created_at, :updated_at)
            '''), {'id': uuid4(), 'batch_id': batch_id, 'created_at': now, 'updated_at': now})

            assert connection.scalar(text(f'SELECT count(*) FROM "{secured}".roles')) == 2
            for table in TABLES:
                assert connection.scalar(text('SELECT relrowsecurity FROM pg_class WHERE oid = CAST(:table AS regclass)'), {
                    'table': f'{secured}.{table}',
                })
            for table in ('roles', *BATCH_TABLES):
                connection.execute(text(f'GRANT SELECT ON "{secured}".{table} TO {role}'))
            connection.execute(text(f'SET LOCAL ROLE {role}'))
            assert connection.scalar(text(f'SELECT count(*) FROM "{secured}".roles')) == 0
            for table in BATCH_TABLES:
                assert connection.scalar(text(f'SELECT count(*) FROM "{secured}".{table}')) == 0
        finally:
            transaction.rollback()

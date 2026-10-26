from copy import deepcopy

import pytest
from sqlalchemy import select

from app.db.preview import preview_schema, validate_preview_database
from app.cli.import_sources import SourceManifest, import_sources
from app.models.verifications import EmployerClaim
from tests.test_verification_import import manifest
from tests.test_verification_store import verification_db


def test_render_metadata_selects_only_dev_pr():
    for number in (8, 9):
        assert preview_schema({'IS_PULL_REQUEST': 'true', 'RENDER_EXTERNAL_HOSTNAME': f'jobshield-pr-{number}.onrender.com'}) == f'preview_pr_{number}'
    assert preview_schema({}) is None
    assert preview_schema({'IS_PULL_REQUEST': 'false'}) is None
    assert preview_schema({'IS_PULL_REQUEST': 'true', 'RENDER_EXTERNAL_HOSTNAME': 'jobshield-backend-pr-8.onrender.com'}) is None


@pytest.mark.parametrize('host', ['', 'jobshield-pr-0.onrender.com', 'jobshield-pr-08.onrender.com', 'jobshield-pr-8.onrender.com.attacker.example'])
def test_bad_preview_metadata_is_rejected(host):
    with pytest.raises(ValueError):
        preview_schema({'IS_PULL_REQUEST': 'true', 'RENDER_EXTERNAL_HOSTNAME': host})


@pytest.mark.parametrize('url', [
    'postgresql+psycopg://postgres.production:secret@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres',
    'postgresql+psycopg://postgres.vleyapvlgnukcawgxozg:secret@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres',
    'postgresql+psycopg://postgres.vleyapvlgnukcawgxozg:secret@localhost:5432/postgres',
    'postgresql+psycopg://postgres.vleyapvlgnukcawgxozg:secret@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres?options=-csearch_path=public',
    'postgresql+psycopg://postgres.vleyapvlgnukcawgxozg:secret@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres?sslmode=disable',
])
def test_preview_cannot_use_production_or_unsafe_connection(url):
    with pytest.raises(ValueError, match='approved DEV') as error:
        validate_preview_database(url)
    assert 'secret' not in str(error.value)


def test_dev_connection_enforces_tls():
    url = validate_preview_database('postgresql+psycopg://postgres.vleyapvlgnukcawgxozg:secret@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres')
    assert url.query['sslmode'] == 'require'


def test_bootstrap_import_is_repeatable_but_rejects_changed_revision(verification_db):
    data = manifest()
    parsed = SourceManifest.model_validate(data)
    import_sources(verification_db, parsed, skip_unchanged=True)
    import_sources(verification_db, parsed, skip_unchanged=True)
    assert len(verification_db.scalars(select(EmployerClaim)).all()) == 2
    changed = deepcopy(data)
    changed['employers'][0]['sources'][0]['evidence_excerpt_vi'] = 'Changed without revision bump'
    with pytest.raises(ValueError):
        import_sources(verification_db, SourceManifest.model_validate(changed), skip_unchanged=True)
    changed['employers'][0]['sources'][0]['source_revision'] = 2
    import_sources(verification_db, SourceManifest.model_validate(changed), skip_unchanged=True)
    import_sources(verification_db, SourceManifest.model_validate(changed), skip_unchanged=True)


def test_bootstrap_cannot_silently_change_employer_identity(verification_db):
    data = manifest()
    import_sources(verification_db, SourceManifest.model_validate(data), skip_unchanged=True)
    data['employers'][0]['legal_name'] = 'Different legal subject'
    with pytest.raises(ValueError):
        import_sources(verification_db, SourceManifest.model_validate(data), skip_unchanged=True)


def test_lazy_engine_is_not_published_before_scope_guard_is_attached(monkeypatch):
    from types import SimpleNamespace
    from app.db import session
    engine = object()
    monkeypatch.setattr(session, '_engine', None)
    monkeypatch.setattr(session, 'Settings', lambda: SimpleNamespace(database_url=SimpleNamespace(get_secret_value=lambda: 'unused')))
    monkeypatch.setattr(session, 'preview_schema', lambda: 'preview_pr_8')
    monkeypatch.setattr(session, 'validate_preview_database', lambda raw: 'safe-url')
    monkeypatch.setattr(session, 'create_engine', lambda *args, **kwargs: engine)
    def attach_scope(candidate, schema):
        assert session._engine is None, 'Another request can use the unscoped engine during hook registration'
        assert candidate is engine and schema == 'preview_pr_8'
    monkeypatch.setattr(session, 'scope_engine', attach_scope)
    assert session.get_engine() is engine

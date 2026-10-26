import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.db.preview import scope_engine
from app.cli.start import bootstrap_preview
from app.cli.import_sources import SourceManifest
from app.services.readiness import check_readiness
from tests.test_postgres_integration import postgres_engine


@pytest.fixture
def preview_engines(postgres_engine):
    schemas = [f'preview_pr_{int(uuid.uuid4().hex[:8], 16)}' for _ in range(2)]
    engines = [create_engine(postgres_engine.url, pool_pre_ping=True) for _ in schemas]
    for engine, schema in zip(engines, schemas):
        scope_engine(engine, schema)
    yield list(zip(engines, schemas))
    for engine in engines:
        engine.dispose()
    with postgres_engine.begin() as c:
        for schema in schemas:
            c.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))


def real_manifest():
    return SourceManifest.model_validate_json(Path('data/verified_sources.json').read_bytes())


def test_two_prs_bootstrap_repeatedly_and_do_not_share_data(preview_engines):
    for engine, schema in preview_engines:
        bootstrap_preview(engine, schema, real_manifest())
        bootstrap_preview(engine, schema, real_manifest())
        with engine.connect() as c:
            assert check_readiness(c)['schema'] == 'current'
            assert c.scalar(text('SELECT count(*) FROM verification_sources')) == 1
            assert c.scalar(text('SELECT count(*) FROM employer_claims')) == 4
    first, second = preview_engines
    with first[0].begin() as c:
        c.execute(text("UPDATE verified_employers SET legal_name='Only first PR'"))
    with second[0].connect() as c:
        assert c.scalar(text('SELECT legal_name FROM verified_employers')) == 'FPT Software Company Limited'


def test_pool_reset_cannot_fall_back_to_public(preview_engines):
    engine, schema = preview_engines[0]
    with engine.connect() as c:
        c.execute(text("SELECT set_config('search_path', 'public', false)"))
        c.commit()
    with engine.connect() as c:
        assert c.scalar(text("SELECT current_setting('search_path')")) == schema
        assert c.scalar(text("SELECT to_regclass('guest_sessions')")) is None


def test_readiness_rejects_missing_old_revision_and_missing_columns(preview_engines):
    engine, schema = preview_engines[0]
    with engine.connect() as c:
        with pytest.raises(Exception):
            check_readiness(c)
    bootstrap_preview(engine, schema, real_manifest())
    with engine.begin() as c:
        c.execute(text("UPDATE alembic_version SET version_num='f0c67067b2b0'"))
        with pytest.raises(ValueError, match='SCHEMA_OUTDATED'):
            check_readiness(c)
        c.execute(text("UPDATE alembic_version SET version_num='71b91d2c6a40'"))
        c.execute(text('ALTER TABLE verification_sources DROP COLUMN evidence_excerpt_vi'))
    with engine.connect() as c:
        with pytest.raises(Exception):
            check_readiness(c)


def test_concurrent_bootstrap_is_serialized(preview_engines):
    engine, schema = preview_engines[0]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: bootstrap_preview(engine, schema, real_manifest()), range(2)))
    with engine.connect() as c:
        assert c.scalar(text('SELECT count(*) FROM verification_sources')) == 1


def test_bad_manifest_rolls_back_new_schema_and_migration(preview_engines):
    engine, schema = preview_engines[0]
    data = real_manifest().model_dump()
    data['employers'][0]['sources'][0]['claims'] *= 2
    with pytest.raises(Exception):
        bootstrap_preview(engine, schema, SourceManifest.model_validate(data))
    with engine.connect() as c:
        assert c.scalar(text('SELECT to_regnamespace(:schema)'), {'schema': schema}) is None

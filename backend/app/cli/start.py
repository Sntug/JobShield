"""Prepare isolated DEV PR storage before serving; other environments only exec Uvicorn."""

import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.cli.import_sources import SourceManifest, import_sources
from app.db.preview import preview_schema
from app.db.session import get_engine

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def bootstrap_preview(engine, schema, manifest):
    # Validate even when called outside startup; SQL identifiers below are fixed numeric PR names.
    import re
    if not re.fullmatch(r'preview_pr_[1-9][0-9]{0,9}', schema):
        raise ValueError('Invalid PR schema.')
    if any(entry.is_demo or any(source.is_demo for source in entry.sources) for entry in manifest.employers):
        raise ValueError('DEMO sources cannot bootstrap a cloud Preview.')
    with engine.begin() as connection:
        if connection.scalar(text("SELECT current_setting('search_path')")) != schema:
            raise ValueError('PR database scope mismatch.')
        connection.execute(text("SET LOCAL lock_timeout = '30s'"))
        connection.execute(text("SET LOCAL statement_timeout = '120s'"))
        connection.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"), {'key': 'jobshield:' + schema})
        connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
        config = Config(str(BACKEND_ROOT / 'alembic.ini'))
        config.set_main_option('script_location', str(BACKEND_ROOT / 'alembic'))
        config.attributes['connection'] = connection
        config.attributes['version_table_schema'] = schema
        command.upgrade(config, 'head')
        with Session(bind=connection) as db:
            import_sources(db, manifest, skip_unchanged=True)


def main():
    try:
        schema = preview_schema()
        if schema:
            manifest = SourceManifest.model_validate_json((BACKEND_ROOT / 'data/verified_sources.json').read_bytes())
            bootstrap_preview(get_engine(), schema, manifest)
            print(f'DEV Preview ready: {schema}', flush=True)
    except Exception:
        # Driver and validation exceptions can include credentials or manifest data.
        raise SystemExit('Preview bootstrap failed; refusing to start. Check DEV target, migrations and source revisions.') from None
    port = os.environ.get('PORT', '8000')
    os.execvp('uvicorn', ['uvicorn', 'app.main:app', '--host', '0.0.0.0', '--port', port])


if __name__ == '__main__':
    main()

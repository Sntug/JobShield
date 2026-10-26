"""Schema readiness, shared by deployment health checks and smoke tests."""

from functools import lru_cache
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import select, text

from app.models import Base


@lru_cache(maxsize=1)
def migration_heads():
    config = Config()
    config.set_main_option('script_location', str(Path(__file__).resolve().parents[2] / 'alembic'))
    return set(ScriptDirectory.from_config(config).get_heads())


def check_readiness(connection):
    revisions = set(connection.execute(text('SELECT version_num FROM alembic_version')).scalars())
    if revisions != migration_heads():
        raise ValueError('SCHEMA_OUTDATED')
    for table in Base.metadata.sorted_tables:
        connection.execute(select(table).limit(0))
    return {'schema': 'current'}

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import Settings

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

from app.models import Base

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata


def get_url() -> str:
    """Lấy DATABASE_URL từ config, biến môi trường, hoặc Settings."""
    ini_url = config.get_main_option("sqlalchemy.url")
    if ini_url and ini_url != "driver://user:pass@localhost/dbname":
        return ini_url
    env_url = os.getenv("DATABASE_URL")
    if env_url:
        return env_url
    try:
        settings = Settings()
        return settings.database_url.get_secret_value()
    except Exception:
        return ""


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_url()
    version_table_schema = config.attributes.get("version_table_schema", None)
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table_schema=version_table_schema,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    # Kiểm tra xem có connection truyền trực tiếp trong attributes từ test suite không
    connectable = config.attributes.get("connection", None)
    version_table_schema = config.attributes.get("version_table_schema", None)

    if connectable is None:
        url = get_url()
        from app.db.preview import preview_schema, validate_preview_database, scope_engine
        schema = preview_schema()
        if schema:
            url = validate_preview_database(url)
            version_table_schema = schema
        configuration = config.get_section(config.config_ini_section, {})
        configuration["sqlalchemy.url"] = url

        connectable = engine_from_config(
            configuration,
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )
        if schema:
            scope_engine(connectable, schema)

        with connectable.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                version_table_schema=version_table_schema,
            )
            with context.begin_transaction():
                context.run_migrations()
    else:
        context.configure(
            connection=connectable,
            target_metadata=target_metadata,
            version_table_schema=version_table_schema,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

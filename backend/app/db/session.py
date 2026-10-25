"""Database session management."""

from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.core.config import Settings

_engine = None
_SessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        settings = Settings()
        _engine = create_engine(
            settings.database_url.get_secret_value(),
            pool_pre_ping=True,
            connect_args={"connect_timeout": 10},
        )
    return _engine


def get_session_local():
    global _SessionLocal
    if _SessionLocal is None:
        engine = get_engine()
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return _SessionLocal


def get_db() -> Generator[Session, None, None]:
    """Dependency cung cấp SQLAlchemy Session cho API routes."""
    session_factory = get_session_local()
    db = session_factory()
    try:
        yield db
    finally:
        db.close()

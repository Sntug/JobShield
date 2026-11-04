"""Unit tests for BatchAnalysis and BatchAnalysisItem models and constraints."""

from datetime import datetime, timedelta, timezone
import uuid
import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.analyses import Analysis
from app.models.batch_analyses import BatchAnalysis, BatchAnalysisItem
from app.models.guest_sessions import GuestSession
from app.models.users import Role, User


@pytest.fixture
def db_session():
    """Isolated SQLite in-memory database with foreign keys enabled."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()

    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def test_create_batch_analysis_guest(db_session):
    now = datetime.now(timezone.utc)
    expires = now + timedelta(hours=24)

    guest = GuestSession(
        id=uuid.uuid4(),
        token_hash="hash_1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
        created_at=now,
        expires_at=expires,
    )
    db_session.add(guest)
    db_session.commit()

    batch = BatchAnalysis(
        id=uuid.uuid4(),
        session_id=guest.id,
        status="pending",
        total_items=2,
        processed_items=0,
        created_at=now,
        updated_at=now,
        expires_at=expires,
    )
    db_session.add(batch)
    db_session.commit()

    saved_batch = db_session.get(BatchAnalysis, batch.id)
    assert saved_batch is not None
    assert saved_batch.session_id == guest.id
    assert saved_batch.user_id is None
    assert saved_batch.expires_at is not None
    # SQLite drops timezone info, compare in UTC
    saved_expires = saved_batch.expires_at if saved_batch.expires_at.tzinfo else saved_batch.expires_at.replace(tzinfo=timezone.utc)
    assert saved_expires == expires
    assert saved_batch.status == "pending"
    assert saved_batch.total_items == 2
    assert saved_batch.processed_items == 0
    assert saved_batch.session.id == guest.id
    assert len(guest.batch_analyses) == 1
    assert guest.batch_analyses[0].id == batch.id


def test_create_batch_analysis_authenticated_user(db_session):
    now = datetime.now(timezone.utc)

    role = Role(id=uuid.uuid4(), name="user", description="Normal user")
    db_session.add(role)
    db_session.flush()

    user = User(
        id=uuid.uuid4(),
        role_id=role.id,
        email="test_batch_user@example.com",
        password_hash="hashed_pw",
        full_name="Batch Test User",
        created_at=now,
        updated_at=now,
    )
    db_session.add(user)
    db_session.commit()

    batch = BatchAnalysis(
        id=uuid.uuid4(),
        user_id=user.id,
        status="pending",
        total_items=3,
        processed_items=0,
        created_at=now,
        updated_at=now,
        expires_at=None,
    )
    db_session.add(batch)
    db_session.commit()

    saved_batch = db_session.get(BatchAnalysis, batch.id)
    assert saved_batch is not None
    assert saved_batch.user_id == user.id
    assert saved_batch.session_id is None
    assert saved_batch.expires_at is None
    assert saved_batch.user.id == user.id
    assert len(user.batch_analyses) == 1
    assert user.batch_analyses[0].id == batch.id


def test_owner_constraint_violation_both_null(db_session):
    now = datetime.now(timezone.utc)

    batch = BatchAnalysis(
        id=uuid.uuid4(),
        session_id=None,
        user_id=None,
        status="pending",
        total_items=1,
        processed_items=0,
        created_at=now,
        updated_at=now,
        expires_at=now + timedelta(hours=24),
    )
    db_session.add(batch)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_owner_constraint_violation_both_set(db_session):
    now = datetime.now(timezone.utc)
    expires = now + timedelta(hours=24)

    guest = GuestSession(
        id=uuid.uuid4(),
        token_hash="hash_guest_owner_conflict",
        created_at=now,
        expires_at=expires,
    )
    role = Role(id=uuid.uuid4(), name="user", description="Normal user")
    db_session.add_all([guest, role])
    db_session.flush()

    user = User(
        id=uuid.uuid4(),
        role_id=role.id,
        email="conflict_user@example.com",
        password_hash="hashed_pw",
        full_name="Conflict User",
        created_at=now,
        updated_at=now,
    )
    db_session.add(user)
    db_session.commit()

    batch = BatchAnalysis(
        id=uuid.uuid4(),
        session_id=guest.id,
        user_id=user.id,
        status="pending",
        total_items=1,
        processed_items=0,
        created_at=now,
        updated_at=now,
        expires_at=expires,
    )
    db_session.add(batch)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_expiry_constraint_violation_user_with_expires_at(db_session):
    now = datetime.now(timezone.utc)

    role = Role(id=uuid.uuid4(), name="user", description="Normal user")
    db_session.add(role)
    db_session.flush()

    user = User(
        id=uuid.uuid4(),
        role_id=role.id,
        email="expiry_user@example.com",
        password_hash="hashed_pw",
        full_name="Expiry User",
        created_at=now,
        updated_at=now,
    )
    db_session.add(user)
    db_session.commit()

    # User cannot have non-null expires_at
    batch = BatchAnalysis(
        id=uuid.uuid4(),
        user_id=user.id,
        status="pending",
        total_items=1,
        processed_items=0,
        created_at=now,
        updated_at=now,
        expires_at=now + timedelta(hours=24),
    )
    db_session.add(batch)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_expiry_constraint_violation_guest_without_expires_at(db_session):
    now = datetime.now(timezone.utc)
    expires = now + timedelta(hours=24)

    guest = GuestSession(
        id=uuid.uuid4(),
        token_hash="hash_guest_no_expiry",
        created_at=now,
        expires_at=expires,
    )
    db_session.add(guest)
    db_session.commit()

    # Guest must have non-null expires_at
    batch = BatchAnalysis(
        id=uuid.uuid4(),
        session_id=guest.id,
        status="pending",
        total_items=1,
        processed_items=0,
        created_at=now,
        updated_at=now,
        expires_at=None,
    )
    db_session.add(batch)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_batch_items_and_cascading_deletion(db_session):
    now = datetime.now(timezone.utc)
    expires = now + timedelta(hours=24)

    guest = GuestSession(
        id=uuid.uuid4(),
        token_hash="hash_guest_cascade",
        created_at=now,
        expires_at=expires,
    )
    db_session.add(guest)
    db_session.commit()

    batch = BatchAnalysis(
        id=uuid.uuid4(),
        session_id=guest.id,
        status="processing",
        total_items=2,
        processed_items=1,
        created_at=now,
        updated_at=now,
        expires_at=expires,
    )
    db_session.add(batch)
    db_session.commit()

    analysis = Analysis(
        id=uuid.uuid4(),
        session_id=guest.id,
        raw_text="Tuyển nhân viên",
        risk_label_vi="Thấp",
        verification_label_vi="Chưa xác minh",
        finding_vi="Không phát hiện bất thường",
        job={"title": "Developer"},
        indicators=[],
        evidence={},
        actions_vi=[],
        created_at=now,
        expires_at=expires,
    )
    db_session.add(analysis)
    db_session.commit()

    item1 = BatchAnalysisItem(
        id=uuid.uuid4(),
        batch_id=batch.id,
        item_order=1,
        input_type="text",
        input_value="Tuyển nhân viên lập trình",
        status="success",
        analysis_id=analysis.id,
        created_at=now,
        updated_at=now,
    )
    item2 = BatchAnalysisItem(
        id=uuid.uuid4(),
        batch_id=batch.id,
        item_order=2,
        input_type="url",
        input_value="https://example.com/job/1",
        status="pending",
        created_at=now,
        updated_at=now,
    )
    db_session.add_all([item1, item2])
    db_session.commit()

    # Verify items relationship
    refreshed_batch = db_session.get(BatchAnalysis, batch.id)
    assert len(refreshed_batch.items) == 2
    assert item1.batch.id == batch.id
    assert item1.analysis.id == analysis.id

    # Verify cascading deletion when batch is deleted
    db_session.delete(refreshed_batch)
    db_session.commit()

    remaining_items = db_session.scalars(
        select(BatchAnalysisItem).where(BatchAnalysisItem.batch_id == batch.id)
    ).all()
    assert len(remaining_items) == 0

    # Analysis record remains intact
    assert db_session.get(Analysis, analysis.id) is not None

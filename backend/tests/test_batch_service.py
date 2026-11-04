"""Unit tests for batch analysis service and schemas."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
import uuid
import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.analyses import Analysis
from app.models.batch_analyses import BatchAnalysis, BatchAnalysisItem
from app.models.guest_sessions import GuestSession
from app.models.indicators import RiskIndicator
from app.models.users import Role, User
from app.schemas.batch_analyses import (
    BatchAnalysisCreate,
    BatchAnalysisResponse,
    BatchItemInput,
    BatchItemResponse,
)
from app.services.batch_analysis import (
    cancel_batch,
    create_batch,
    get_batch_by_id,
    process_batch_in_background,
)
from app.services.url_extraction import URLExtractionResult


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
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSession()

    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def guest_session_record(db_session):
    now = datetime.now(timezone.utc)
    guest = GuestSession(
        id=uuid.uuid4(),
        token_hash="hash_test_batch_service_" + uuid.uuid4().hex,
        created_at=now,
        expires_at=now + timedelta(hours=24),
    )
    db_session.add(guest)
    db_session.commit()
    return guest


@pytest.fixture
def user_record(db_session):
    now = datetime.now(timezone.utc)
    role = Role(id=uuid.uuid4(), name="user_" + uuid.uuid4().hex[:6], description="User")
    db_session.add(role)
    db_session.flush()

    user = User(
        id=uuid.uuid4(),
        role_id=role.id,
        email=f"user_{uuid.uuid4().hex[:6]}@example.com",
        password_hash="hashed_pw",
        full_name="Batch Test User",
        created_at=now,
        updated_at=now,
    )
    db_session.add(user)
    db_session.commit()
    return user


def test_batch_schema_validation():
    # Empty items not allowed
    with pytest.raises(ValidationError):
        BatchAnalysisCreate(items=[])

    # More than 10 items not allowed
    with pytest.raises(ValidationError):
        BatchAnalysisCreate(items=[BatchItemInput(type="text", value=f"Job {i}") for i in range(11)])

    # Whitespace only item value not allowed
    with pytest.raises(ValidationError):
        BatchItemInput(type="text", value="   ")

    # Invalid input type not allowed
    with pytest.raises(ValidationError):
        BatchItemInput(type="audio", value="something")


def test_create_batch_guest(db_session, guest_session_record):
    payload = BatchAnalysisCreate(
        items=[
            BatchItemInput(type="text", value="Tuyển dụng nhân viên kinh doanh lương 15tr"),
            BatchItemInput(type="url", value="https://example.com/job/1"),
        ],
        use_ai=False,
        ai_consent=False,
    )

    batch = create_batch(
        db=db_session,
        payload=payload,
        session_id=guest_session_record.id,
        expires_at=guest_session_record.expires_at,
    )

    assert batch.id is not None
    assert batch.session_id == guest_session_record.id
    assert batch.user_id is None
    assert batch.status == "pending"
    assert batch.total_items == 2
    assert batch.processed_items == 0
    assert len(batch.items) == 2

    assert batch.items[0].item_order == 0
    assert batch.items[0].input_type == "text"
    assert batch.items[0].input_value == "Tuyển dụng nhân viên kinh doanh lương 15tr"
    assert batch.items[0].status == "pending"

    assert batch.items[1].item_order == 1
    assert batch.items[1].input_type == "url"
    assert batch.items[1].input_value == "https://example.com/job/1"
    assert batch.items[1].status == "pending"

    # Schema serialization test
    resp = BatchAnalysisResponse.model_validate(batch)
    assert resp.id == batch.id
    assert resp.status == "pending"
    assert len(resp.items) == 2
    assert resp.items[0].item_order == 0


def test_create_batch_user(db_session, user_record):
    payload = BatchAnalysisCreate(
        items=[
            BatchItemInput(type="text", value="Tuyển kỹ sư phần mềm backend Python"),
        ]
    )

    batch = create_batch(
        db=db_session,
        payload=payload,
        user_id=user_record.id,
        expires_at=None,
    )

    assert batch.id is not None
    assert batch.user_id == user_record.id
    assert batch.session_id is None
    assert batch.expires_at is None
    assert batch.status == "pending"
    assert batch.total_items == 1
    assert len(batch.items) == 1


def test_get_batch_by_id(db_session, guest_session_record):
    payload = BatchAnalysisCreate(
        items=[BatchItemInput(type="text", value="Tuyển kế toán kho")]
    )
    batch = create_batch(
        db=db_session,
        payload=payload,
        session_id=guest_session_record.id,
        expires_at=guest_session_record.expires_at,
    )

    found = get_batch_by_id(db_session, batch.id)
    assert found is not None
    assert found.id == batch.id

    not_found = get_batch_by_id(db_session, uuid.uuid4())
    assert not_found is None


def test_cancel_batch(db_session, guest_session_record):
    payload = BatchAnalysisCreate(
        items=[
            BatchItemInput(type="text", value="Job 1"),
            BatchItemInput(type="text", value="Job 2"),
        ]
    )
    batch = create_batch(
        db=db_session,
        payload=payload,
        session_id=guest_session_record.id,
        expires_at=guest_session_record.expires_at,
    )

    # Cancel pending batch
    cancelled = cancel_batch(db_session, batch.id)
    assert cancelled is not None
    assert cancelled.status == "cancelled"
    for item in cancelled.items:
        assert item.status == "cancelled"

    # Cancel on already cancelled returns it
    cancelled_again = cancel_batch(db_session, batch.id)
    assert cancelled_again.status == "cancelled"

    # Cancel on non-existent batch
    assert cancel_batch(db_session, uuid.uuid4()) is None


def test_cancel_batch_partial_preserves_completed_items(db_session, guest_session_record):
    payload = BatchAnalysisCreate(
        items=[
            BatchItemInput(type="text", value="Job 1"),
            BatchItemInput(type="text", value="Job 2"),
        ]
    )
    batch = create_batch(
        db=db_session,
        payload=payload,
        session_id=guest_session_record.id,
        expires_at=guest_session_record.expires_at,
    )

    # Mark first item as success
    batch.items[0].status = "success"
    db_session.commit()

    cancelled = cancel_batch(db_session, batch.id)
    assert cancelled.status == "cancelled"
    assert cancelled.items[0].status == "success"
    assert cancelled.items[1].status == "cancelled"


def test_cancel_batch_leaves_started_item_to_settle(db_session, guest_session_record):
    batch = create_batch(
        db=db_session,
        payload=BatchAnalysisCreate(
            items=[BatchItemInput(type="text", value="Job 1"), BatchItemInput(type="text", value="Job 2")]
        ),
        session_id=guest_session_record.id,
        expires_at=guest_session_record.expires_at,
    )
    batch.items[0].status = "processing"
    db_session.commit()

    cancelled = cancel_batch(db_session, batch.id)

    assert cancelled.status == "cancelled"
    assert cancelled.items[0].status == "processing"
    assert cancelled.items[1].status == "cancelled"


def test_batch_worker_result_commit_is_atomic(db_session, guest_session_record):
    batch = create_batch(
        db=db_session,
        payload=BatchAnalysisCreate(items=[BatchItemInput(type="text", value="Job 1")]),
        session_id=guest_session_record.id,
        expires_at=guest_session_record.expires_at,
    )
    item = batch.items[0]
    commit = db_session.commit

    def fail_success_commit():
        if item.status == "success":
            raise RuntimeError("injected result commit failure")
        commit()

    with patch.object(db_session, "commit", side_effect=fail_success_commit):
        process_batch_in_background(batch.id, db=db_session)

    db_session.refresh(batch)
    assert db_session.query(Analysis).filter_by(id=item.analysis_id).first() is None
    assert batch.items[0].status == "error"
    assert batch.items[0].error_code == "ANALYSIS_FAILED"
    assert batch.processed_items == 1


def test_outer_worker_failure_marks_unfinished_items_failed(db_session, guest_session_record):
    batch = create_batch(
        db=db_session,
        payload=BatchAnalysisCreate(
            items=[BatchItemInput(type="text", value="Job 1"), BatchItemInput(type="text", value="Job 2")]
        ),
        session_id=guest_session_record.id,
        expires_at=guest_session_record.expires_at,
    )
    query = db_session.query
    failed = False

    def fail_rule_query(model, *args, **kwargs):
        nonlocal failed
        if model is RiskIndicator and not failed:
            failed = True
            raise RuntimeError("injected worker failure")
        return query(model, *args, **kwargs)

    with patch.object(db_session, "query", side_effect=fail_rule_query):
        process_batch_in_background(batch.id, db=db_session)

    db_session.refresh(batch)
    assert batch.status == "failed"
    assert batch.processed_items == 2
    assert [item.status for item in batch.items] == ["error", "error"]


def test_fail_stale_batch_preserves_completed_items(db_session, guest_session_record):
    batch = create_batch(
        db=db_session,
        payload=BatchAnalysisCreate(
            items=[
                BatchItemInput(type="text", value="Job 1"),
                BatchItemInput(type="text", value="Job 2"),
            ]
        ),
        session_id=guest_session_record.id,
        expires_at=guest_session_record.expires_at,
    )
    batch.items[0].status = "success"
    batch.processed_items = 1
    batch.status = "processing"
    batch.updated_at = datetime.now(timezone.utc) - timedelta(hours=1)
    db_session.commit()

    from app.services import batch_analysis

    fail_stale_batch = getattr(batch_analysis, "fail_stale_batch", None)
    assert callable(fail_stale_batch)
    assert fail_stale_batch(db_session, batch.id)

    db_session.refresh(batch)
    assert batch.status == "failed"
    assert batch.items[0].status == "success"
    assert batch.items[1].status == "error"
    assert batch.processed_items == 2


def test_stale_cancelled_batch_settles_processing_item_without_reopening(db_session, guest_session_record):
    batch = create_batch(
        db=db_session,
        payload=BatchAnalysisCreate(items=[BatchItemInput(type="text", value="Job 1")]),
        session_id=guest_session_record.id,
        expires_at=guest_session_record.expires_at,
    )
    batch.status = "cancelled"
    batch.items[0].status = "processing"
    stale_time = datetime.now(timezone.utc) - timedelta(hours=1)
    batch.items[0].updated_at = stale_time
    batch.updated_at = stale_time
    db_session.commit()

    from app.services import batch_analysis

    fail_stale_batch = getattr(batch_analysis, "fail_stale_batch", None)
    assert callable(fail_stale_batch)
    assert fail_stale_batch(db_session, batch.id)

    db_session.refresh(batch)
    assert batch.status == "cancelled"
    assert batch.items[0].status == "error"
    assert batch.processed_items == 1


def test_process_batch_in_background_text_success(db_session, guest_session_record):
    payload = BatchAnalysisCreate(
        items=[
            BatchItemInput(type="text", value="Công ty ABC tuyển thực tập sinh IT có lương."),
            BatchItemInput(type="text", value="Việc nhẹ lương cao 50 triệu/ngày, cọc trước 500k."),
        ]
    )
    batch = create_batch(
        db=db_session,
        payload=payload,
        session_id=guest_session_record.id,
        expires_at=guest_session_record.expires_at,
    )

    process_batch_in_background(batch.id, use_ai=False, ai_consent=False, db=db_session)

    db_session.refresh(batch)
    assert batch.status == "completed"
    assert batch.processed_items == 2
    assert len(batch.items) == 2

    for item in batch.items:
        assert item.status == "success"
        assert item.analysis_id is not None
        assert item.analysis is not None
        assert item.analysis.risk_label_vi in ["Thấp", "Trung bình", "Cao", "Rất cao", "Không đủ thông tin"]

    # Verify AnalysisResponse serialization
    resp = BatchAnalysisResponse.model_validate(batch)
    assert resp.status == "completed"
    assert resp.processed_items == 2
    assert resp.items[0].analysis is not None
    assert resp.items[0].analysis.id == batch.items[0].analysis_id


def test_process_batch_in_background_url_success(db_session, guest_session_record):
    payload = BatchAnalysisCreate(
        items=[
            BatchItemInput(type="url", value="https://example.com/jobs/dev"),
        ]
    )
    batch = create_batch(
        db=db_session,
        payload=payload,
        session_id=guest_session_record.id,
        expires_at=guest_session_record.expires_at,
    )

    with patch("app.services.batch_analysis.extract_text_from_url") as mock_extract:
        mock_extract.return_value = URLExtractionResult(
            success=True,
            text="Tuyển dụng lập trình viên backend Python kinh nghiệm 2 năm, lương thỏa thuận.",
            source_url="https://example.com/jobs/dev",
        )

        process_batch_in_background(batch.id, db=db_session)

    db_session.refresh(batch)
    assert batch.status == "completed"
    assert batch.processed_items == 1
    assert batch.items[0].status == "success"
    assert batch.items[0].analysis_id is not None
    assert batch.items[0].analysis.raw_text == "Tuyển dụng lập trình viên backend Python kinh nghiệm 2 năm, lương thỏa thuận."


def test_process_batch_in_background_url_failure(db_session, guest_session_record):
    payload = BatchAnalysisCreate(
        items=[
            BatchItemInput(type="url", value="https://invalid-job-page.com/404"),
        ]
    )
    batch = create_batch(
        db=db_session,
        payload=payload,
        session_id=guest_session_record.id,
        expires_at=guest_session_record.expires_at,
    )

    with patch("app.services.batch_analysis.extract_text_from_url") as mock_extract:
        mock_extract.return_value = URLExtractionResult(
            success=False,
            text=None,
            source_url="https://invalid-job-page.com/404",
            failure_vi="Trang nguồn trả về lỗi HTTP 404.",
            status_code=404,
        )

        process_batch_in_background(batch.id, db=db_session)

    db_session.refresh(batch)
    assert batch.status == "failed"
    assert batch.processed_items == 1
    assert batch.items[0].status == "error"
    assert batch.items[0].error_code == "EXTRACTION_FAILED"
    assert "404" in (batch.items[0].error_message or "")


def test_process_batch_in_background_partial_success(db_session, guest_session_record):
    payload = BatchAnalysisCreate(
        items=[
            BatchItemInput(type="text", value="Tuyển kỹ sư IT"),
            BatchItemInput(type="url", value="https://bad-url.com"),
        ]
    )
    batch = create_batch(
        db=db_session,
        payload=payload,
        session_id=guest_session_record.id,
        expires_at=guest_session_record.expires_at,
    )

    with patch("app.services.batch_analysis.extract_text_from_url") as mock_extract:
        mock_extract.return_value = URLExtractionResult(
            success=False,
            text=None,
            source_url="https://bad-url.com",
            failure_vi="Không thể kết nối",
        )

        process_batch_in_background(batch.id, db=db_session)

    db_session.refresh(batch)
    assert batch.status == "completed"  # 1 success + 1 error = completed
    assert batch.processed_items == 2
    assert batch.items[0].status == "success"
    assert batch.items[1].status == "error"


def test_process_batch_in_background_analysis_exception(db_session, guest_session_record):
    payload = BatchAnalysisCreate(
        items=[
            BatchItemInput(type="text", value="Tuyển nhân viên phục vụ"),
        ]
    )
    batch = create_batch(
        db=db_session,
        payload=payload,
        session_id=guest_session_record.id,
        expires_at=guest_session_record.expires_at,
    )

    with patch("app.services.batch_analysis.perform_text_analysis") as mock_analysis:
        mock_analysis.side_effect = RuntimeError("Rule engine internal error")

        process_batch_in_background(batch.id, db=db_session)

    db_session.refresh(batch)
    assert batch.status == "failed"
    assert batch.processed_items == 1
    assert batch.items[0].status == "error"
    assert batch.items[0].error_code == "ANALYSIS_FAILED"
    assert "Rule engine internal error" not in (batch.items[0].error_message or "")
    assert batch.items[0].error_message == "Không thể phân tích nội dung này do lỗi nội bộ."


def test_process_batch_in_background_with_ai(db_session, user_record):
    payload = BatchAnalysisCreate(
        items=[
            BatchItemInput(type="text", value="Tuyển trợ lý giám đốc"),
        ],
        use_ai=True,
        ai_consent=True,
    )
    batch = create_batch(
        db=db_session,
        payload=payload,
        user_id=user_record.id,
        expires_at=None,
    )

    with patch("app.services.batch_analysis.perform_analysis_with_ai") as mock_ai:
        from app.schemas.analyses import AIInsightsData, EvidenceData, JobExtracted
        mock_ai.return_value = (
            JobExtracted(job_title="Trợ lý"),
            [],
            "Thấp",
            "Chưa xác minh",
            "Đánh giá ổn",
            EvidenceData(matched_sources=[]),
            ["Xác minh thêm"],
            AIInsightsData(
                status="success",
                provider="gemini",
                model="gemini-2.0-flash",
                semantic_summary_vi="Nội dung bình thường",
                suspicious_patterns_vi=[],
                reasoning_vi="Hợp lý",
                confidence_note_vi="Độ tin cậy cao",
                limitations_vi=[],
            ),
        )

        process_batch_in_background(batch.id, use_ai=True, ai_consent=True, db=db_session)

    db_session.refresh(batch)
    assert batch.status == "completed"
    assert batch.items[0].status == "success"
    assert batch.items[0].analysis is not None
    assert batch.items[0].analysis.ai_insights is not None
    assert batch.items[0].analysis.ai_insights.get("model") == "gemini-2.0-flash"


def test_process_batch_in_background_cancelled_early(db_session, guest_session_record):
    payload = BatchAnalysisCreate(
        items=[BatchItemInput(type="text", value="Job to be cancelled")]
    )
    batch = create_batch(
        db=db_session,
        payload=payload,
        session_id=guest_session_record.id,
        expires_at=guest_session_record.expires_at,
    )

    cancel_batch(db_session, batch.id)
    # Now run background processing
    process_batch_in_background(batch.id, db=db_session)

    db_session.refresh(batch)
    assert batch.status == "cancelled"
    assert batch.processed_items == 0
    assert batch.items[0].status == "cancelled"


def test_process_batch_in_background_cancelled_during_run(db_session, guest_session_record):
    payload = BatchAnalysisCreate(
        items=[
            BatchItemInput(type="text", value="Job 1"),
            BatchItemInput(type="text", value="Job 2"),
        ]
    )
    batch = create_batch(
        db=db_session,
        payload=payload,
        session_id=guest_session_record.id,
        expires_at=guest_session_record.expires_at,
    )

    original_load = app_services_load = None
    from app.services import batch_analysis

    # Hook load_for_job on the first item to trigger cancellation
    call_count = 0

    def mock_load_for_job(db, job):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            cancel_batch(db, batch.id)
        return []

    with patch("app.services.batch_analysis.load_for_job", side_effect=mock_load_for_job):
        process_batch_in_background(batch.id, db=db_session)

    db_session.refresh(batch)
    assert batch.status == "cancelled"
    # Item 1 was processed before break, Item 2 was cancelled
    assert batch.items[0].status == "success"
    assert batch.items[1].status == "cancelled"


def test_process_batch_in_background_default_session(db_session, guest_session_record):
    payload = BatchAnalysisCreate(
        items=[BatchItemInput(type="text", value="Job default session")]
    )
    batch = create_batch(
        db=db_session,
        payload=payload,
        session_id=guest_session_record.id,
        expires_at=guest_session_record.expires_at,
    )

    # Supply a worker-owned session through the existing session factory.
    mock_session = MagicMock(wraps=db_session)
    mock_session.close = MagicMock()
    session_factory = MagicMock(return_value=mock_session)

    with patch("app.services.batch_analysis.get_session_local", return_value=session_factory):
        process_batch_in_background(batch.id)
        assert mock_session.close.called

    db_session.refresh(batch)
    assert batch.status == "completed"

"""Automated PostgreSQL 17 integration tests on isolated test container.

Kiểm chứng di chuyển lược đồ (Alembic migration), cách ly phiên khách (foreign session denied),
cố định TTL 24h, cascade purge và snapshot GET trên PostgreSQL thật.
Tất cả kiểm thử chạy trong schema riêng biệt được dọn dẹp sau khi kết thúc.
"""

import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from alembic import command
from alembic.config import Config
from app.core.rate_limit import reset_rate_limits
from app.core.security import generate_guest_token, hash_guest_token
from app.db.session import get_db
from app.main import app
from app.models.analyses import Analysis
from app.models.guest_sessions import GuestSession
from app.cli.cleanup import purge_expired_sessions

EXPLICIT_TEST_URL = os.getenv("POSTGRES_TEST_URL")
POSTGRES_TEST_URL = EXPLICIT_TEST_URL or "postgresql+psycopg://r11_review:r11_local_test@127.0.0.1:55432/jobshield_r11_review"


@pytest.fixture(scope="module")
def postgres_engine():
    """Tạo engine PostgreSQL; fail nếu URL được cấu hình tường minh nhưng không kết nối được."""
    try:
        engine = create_engine(POSTGRES_TEST_URL, connect_args={"connect_timeout": 3})
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return engine
    except Exception as e:
        if EXPLICIT_TEST_URL:
            pytest.fail(f"Lỗi kết nối tới test container PostgreSQL tại 127.0.0.1:55432: {type(e).__name__}")
        else:
            pytest.skip(f"PostgreSQL test container 127.0.0.1:55432 không khả dụng: {type(e).__name__}")


@pytest.fixture(scope="module")
def isolated_schema(postgres_engine):
    """Tạo một schema riêng biệt (test_xxxxxxxx) cho module kiểm thử và tự động xóa sau khi xong."""
    schema_name = f"test_{uuid.uuid4().hex[:8]}"
    with postgres_engine.connect() as conn:
        conn.execute(text(f"CREATE SCHEMA {schema_name}"))
        conn.commit()

    yield schema_name

    with postgres_engine.connect() as conn:
        conn.execute(text(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE"))
        conn.commit()


@pytest.fixture(scope="module", autouse=True)
def run_alembic_migrations(postgres_engine, isolated_schema):
    """Chạy và kiểm chứng migration Alembic trên connection trỏ vào schema test cô lập."""
    alembic_ini_path = Path(__file__).parent.parent / "alembic.ini"
    alembic_cfg = Config(str(alembic_ini_path))
    alembic_cfg.set_main_option("sqlalchemy.url", POSTGRES_TEST_URL)

    with postgres_engine.connect() as conn:
        conn.execute(text(f'SET search_path TO "{isolated_schema}"'))
        alembic_cfg.attributes["connection"] = conn
        alembic_cfg.attributes["version_table_schema"] = isolated_schema
        command.upgrade(alembic_cfg, "head")
        conn.commit()

        # Kiểm tra các bảng đã được Alembic tạo thành công trong schema test
        tables = conn.execute(
            text(
                "SELECT table_name FROM information_schema.tables "
                f"WHERE table_schema = '{isolated_schema}'"
            )
        ).scalars().all()
        assert "guest_sessions" in tables
        assert "analyses" in tables
        assert "alembic_version" in tables


@pytest.fixture
def pg_db(postgres_engine, isolated_schema):
    """Cung cấp session DB riêng trỏ vào schema test và override get_db."""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=postgres_engine)
    db = SessionLocal()
    db.execute(text(f'SET search_path TO "{isolated_schema}"'))

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    reset_rate_limits()

    try:
        yield db
    finally:
        db.close()
        app.dependency_overrides.clear()
        reset_rate_limits()


def test_postgres_live_end_to_end_flow(pg_db):
    """Kiểm chứng luồng thực tế trên PostgreSQL 17:

    - POST cấp phiên và lưu token_hash
    - Fixed expiry (analysis kế thừa expires_at cố định của session)
    - Reused session trả guest_session_token là None
    - Snapshot GET khớp chính xác kết quả POST
    - Foreign VALID session denied (Session B có token hợp lệ nhưng bị 404 khi GET analysis của Session A)
    - Token sai hoặc thiếu header trả 404
    """
    with TestClient(app) as client:
        # 1. Guest A: POST tạo phân tích mới
        res_a = client.post(
            "/api/v1/analyses",
            json={
                "text": (
                    "Công ty Mẫu A (DEMO) tuyển Thực tập sinh kiểm thử. Lương: 4–6 triệu đồng/tháng. "
                    "Email: tuyendung@mau-a.example. Website: https://mau-a.example/tuyen-dung. "
                    "Không thu phí hoặc đặt cọc."
                )
            },
        )
        assert res_a.status_code == 201
        data_a = res_a.json()
        analysis_id_a = data_a["id"]
        token_a = data_a["guest_session_token"]
        assert token_a is not None

        # 2. Guest A: POST lần 2 với cùng token -> phiên được tái sử dụng (token trả về None, expires_at cố định)
        res_a2 = client.post(
            "/api/v1/analyses",
            headers={"X-Guest-Session-Token": token_a},
            json={"text": "Công ty Bình An tuyển Tester. Lương: 8 triệu đồng/tháng. Email: hr@binhan.example."},
        )
        assert res_a2.status_code == 201
        data_a2 = res_a2.json()
        assert data_a2["guest_session_token"] is None
        assert data_a2["expires_at"] == data_a["expires_at"]

        # 3. Snapshot GET: đọc lại analysis_a với token_a, dữ liệu khớp snapshot POST
        get_res = client.get(
            f"/api/v1/analyses/{analysis_id_a}",
            headers={"X-Guest-Session-Token": token_a},
        )
        assert get_res.status_code == 200
        snapshot = get_res.json()
        assert snapshot["id"] == analysis_id_a
        assert snapshot["risk_label_vi"] == data_a["risk_label_vi"]
        assert snapshot["verification_label_vi"] == data_a["verification_label_vi"]
        assert snapshot["job"] == data_a["job"]
        assert snapshot["rules_version"] == data_a["rules_version"]
        assert snapshot["guest_session_token"] is None
        assert get_res.headers.get("Cache-Control") == "no-store"

        # 4. Guest B: tạo một phiên khách hợp lệ khác
        res_b = client.post(
            "/api/v1/analyses",
            json={"text": "Công ty B tuyển dụng nhân viên kinh doanh."},
        )
        assert res_b.status_code == 201
        token_b = res_b.json()["guest_session_token"]
        assert token_b != token_a

        # 5. Foreign VALID session denied: Guest B dùng token hợp lệ để đọc tin của Guest A -> 404
        cross_res = client.get(
            f"/api/v1/analyses/{analysis_id_a}",
            headers={"X-Guest-Session-Token": token_b},
        )
        assert cross_res.status_code == 404
        assert cross_res.headers.get("Cache-Control") == "no-store"

        # 6. Token sai hoặc thiếu header -> 404
        assert client.get(f"/api/v1/analyses/{analysis_id_a}").status_code == 404
        assert client.get(
            f"/api/v1/analyses/{analysis_id_a}",
            headers={"X-Guest-Session-Token": "invalid_wrong_token"},
        ).status_code == 404

        # 7. Kiểm tra DB: chỉ lưu token_hash SHA-256
        analysis_db = pg_db.query(Analysis).filter_by(id=uuid.UUID(analysis_id_a)).first()
        session_db = pg_db.query(GuestSession).filter_by(id=analysis_db.session_id).first()
        assert session_db.token_hash != token_a
        assert len(session_db.token_hash) == 64


def test_postgres_cleanup_cascade_purge(pg_db):
    """Kiểm chứng CLI cleanup xóa triệt để session hết hạn kèm cascade analysis trên PostgreSQL 17."""
    now = datetime.now(timezone.utc)
    past = now - timedelta(hours=48)

    # 1. Tạo session đã hết hạn
    token_expired = generate_guest_token()
    session_expired = GuestSession(
        id=uuid.uuid4(),
        token_hash=hash_guest_token(token_expired),
        created_at=past,
        expires_at=past + timedelta(hours=24),
    )
    pg_db.add(session_expired)
    pg_db.flush()

    analysis_expired = Analysis(
        id=uuid.uuid4(),
        session_id=session_expired.id,
        raw_text="Tin hết hạn trên postgres",
        risk_label_vi="Ít dấu hiệu rủi ro",
        verification_label_vi="Chưa xác minh",
        finding_vi="finding",
        job={},
        indicators=[],
        evidence={},
        actions_vi=[],
        engine_version="0.1.0",
        rules_version="2026.10",
        created_at=past,
        expires_at=session_expired.expires_at,
    )
    pg_db.add(analysis_expired)

    # 2. Tạo session còn hạn
    token_active = generate_guest_token()
    session_active = GuestSession(
        id=uuid.uuid4(),
        token_hash=hash_guest_token(token_active),
        created_at=now,
        expires_at=now + timedelta(hours=24),
    )
    pg_db.add(session_active)
    pg_db.flush()

    analysis_active = Analysis(
        id=uuid.uuid4(),
        session_id=session_active.id,
        raw_text="Tin còn hạn trên postgres",
        risk_label_vi="Ít dấu hiệu rủi ro",
        verification_label_vi="Chưa xác minh",
        finding_vi="finding",
        job={},
        indicators=[],
        evidence={},
        actions_vi=[],
        engine_version="0.1.0",
        rules_version="2026.10",
        created_at=now,
        expires_at=session_active.expires_at,
    )
    pg_db.add(analysis_active)
    pg_db.commit()

    expired_session_id = session_expired.id
    expired_analysis_id = analysis_expired.id
    active_session_id = session_active.id
    active_analysis_id = analysis_active.id

    # 3. Chạy hàm purge_expired_sessions (trả về tuple: số sessions xóa, số analyses xóa)
    purged_sessions, purged_analyses = purge_expired_sessions(pg_db)
    assert purged_sessions >= 1
    assert purged_analyses >= 1

    # 4. Kiểm chứng: session hết hạn và analysis liên quan đã bị cascade xóa
    assert pg_db.query(GuestSession).filter_by(id=expired_session_id).first() is None
    assert pg_db.query(Analysis).filter_by(id=expired_analysis_id).first() is None

    # 5. Kiểm chứng: session còn hạn và analysis của nó được bảo toàn nguyên vẹn
    assert pg_db.query(GuestSession).filter_by(id=active_session_id).first() is not None
    assert pg_db.query(Analysis).filter_by(id=active_analysis_id).first() is not None

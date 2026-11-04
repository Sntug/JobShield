"""Integration tests for batch recruitment analysis API endpoints."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.rate_limit import reset_rate_limits
from app.core.security import generate_guest_token, hash_guest_token
from app.db.base import Base
from app.db.session import get_db
from app.main import app
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
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSession()

    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def client(db_session):
    """TestClient overriding get_db and resetting rate limits."""
    reset_rate_limits()

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    reset_rate_limits()


def register_user(client: TestClient, email: str, name: str = "Test User") -> str:
    """Helper đăng ký người dùng và trả về JWT access token."""
    res = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "secure_password_15_chars",
            "full_name": name,
        },
    )
    assert res.status_code == 201
    return res.json()["access_token"]


def test_post_batch_guest_new_session_creates_and_enqueues(client):
    """POST /batches/analyses không kèm token tạo phiên mới và xếp hàng tác vụ nền."""
    payload = {
        "items": [
            {"type": "text", "value": "Tuyển nhân viên bán hàng lương 10 triệu/tháng."},
            {"type": "text", "value": "Cần tuyển lập trình viên Python kinh nghiệm 2 năm."},
        ],
        "use_ai": False,
        "ai_consent": False,
    }

    with patch("app.api.routes.batch_analyses.process_batch_in_background") as mock_worker:
        res = client.post("/api/v1/batches/analyses", json=payload)

    assert res.status_code == 201
    assert res.headers.get("Cache-Control") == "no-store"
    assert "X-Guest-Session-Token" in res.headers
    guest_token = res.headers["X-Guest-Session-Token"]
    assert len(guest_token) >= 40

    data = res.json()
    assert data["guest_session_token"] == guest_token
    assert data["id"]
    assert data["status"] == "pending"
    assert data["total_items"] == 2
    assert data["processed_items"] == 0
    assert data["expires_at"] is not None
    assert len(data["items"]) == 2
    assert data["items"][0]["item_order"] == 0
    assert data["items"][0]["status"] == "pending"
    assert data["items"][1]["item_order"] == 1
    assert data["items"][1]["status"] == "pending"

    # Worker được enqueue với batch_id, use_ai, ai_consent
    mock_worker.assert_called_once_with(uuid.UUID(data["id"]), False, False)


def test_batch_openapi_only_documents_guest_token_on_create(client):
    schemas = client.get("/openapi.json").json()["components"]["schemas"]
    paths = client.get("/openapi.json").json()["paths"]

    create_schema = paths["/api/v1/batches/analyses"]["post"]["responses"]["201"]["content"]["application/json"]["schema"]["$ref"]
    get_schema = paths["/api/v1/batches/analyses/{batch_id}"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
    cancel_schema = paths["/api/v1/batches/analyses/{batch_id}/cancel"]["post"]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]

    assert create_schema.endswith("/BatchAnalysisCreatedResponse")
    assert "guest_session_token" in schemas["BatchAnalysisCreatedResponse"]["properties"]
    assert get_schema.endswith("/BatchAnalysisResponse")
    assert cancel_schema.endswith("/BatchAnalysisResponse")
    assert "guest_session_token" not in schemas["BatchAnalysisResponse"]["properties"]


def test_post_batch_releases_read_transaction_before_background_task(client, db_session):
    with patch("app.api.routes.batch_analyses.process_batch_in_background"):
        res = client.post(
            "/api/v1/batches/analyses",
            json={"items": [{"type": "text", "value": "Tin tuyển dụng kiểm thử"}]},
        )

    assert res.status_code == 201
    assert not db_session.in_transaction()


def test_post_batch_guest_existing_valid_session(client, db_session):
    """POST /batches/analyses kèm X-Guest-Session-Token hợp lệ tái sử dụng phiên."""
    now = datetime.now(timezone.utc)
    raw_token = generate_guest_token()
    token_hash = hash_guest_token(raw_token)
    session = GuestSession(
        id=uuid.uuid4(),
        token_hash=token_hash,
        created_at=now,
        expires_at=now + timedelta(hours=24),
    )
    db_session.add(session)
    db_session.commit()

    payload = {
        "items": [{"type": "text", "value": "Tuyển thực tập sinh marketing"}],
        "use_ai": True,
        "ai_consent": True,
    }

    with patch("app.api.routes.batch_analyses.process_batch_in_background") as mock_worker:
        res = client.post(
            "/api/v1/batches/analyses",
            json=payload,
            headers={"X-Guest-Session-Token": raw_token},
        )

    assert res.status_code == 201
    data = res.json()
    assert "guest_session_token" not in data
    mock_worker.assert_called_once_with(uuid.UUID(data["id"]), True, True)

    # Đợt phân tích gắn đúng session_id
    saved_batch = db_session.get(BatchAnalysis, uuid.UUID(data["id"]))
    assert saved_batch.session_id == session.id
    assert saved_batch.user_id is None


def test_post_batch_guest_invalid_token_returns_401(client):
    """POST /batches/analyses kèm token không hợp lệ hoặc rỗng trả 401 SESSION_INVALID."""
    payload = {"items": [{"type": "text", "value": "Tuyển dụng nhân viên"}]}

    # Token không tồn tại
    res1 = client.post(
        "/api/v1/batches/analyses",
        json=payload,
        headers={"X-Guest-Session-Token": "invalid_token_does_not_exist"},
    )
    assert res1.status_code == 401
    assert res1.json()["detail"] == "SESSION_INVALID"

    # Token rỗng
    res2 = client.post(
        "/api/v1/batches/analyses",
        json=payload,
        headers={"X-Guest-Session-Token": "   "},
    )
    assert res2.status_code == 401
    assert res2.json()["detail"] == "SESSION_INVALID"


def test_post_batch_authenticated_user(client, db_session):
    """POST /batches/analyses với người dùng đăng nhập không có expires_at."""
    token = register_user(client, "user_batch_api@example.com")

    payload = {
        "items": [{"type": "text", "value": "Tuyển dụng quản lý kỹ thuật"}],
    }

    with patch("app.api.routes.batch_analyses.process_batch_in_background"):
        res = client.post(
            "/api/v1/batches/analyses",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )

    assert res.status_code == 201
    data = res.json()
    assert "guest_session_token" not in data
    assert data["expires_at"] is None

    saved_batch = db_session.get(BatchAnalysis, uuid.UUID(data["id"]))
    assert saved_batch.user_id is not None
    assert saved_batch.session_id is None
    assert saved_batch.expires_at is None


def test_post_batch_validation_rejects_empty_and_excess_items(client):
    """Kiểm tra validation: từ chối 0 mục (422) và từ chối >10 mục (422)."""
    # 0 items
    res1 = client.post("/api/v1/batches/analyses", json={"items": []})
    assert res1.status_code == 422

    # 11 items
    excess_items = [{"type": "text", "value": f"Mô tả công việc thứ {i}"} for i in range(11)]
    res2 = client.post("/api/v1/batches/analyses", json={"items": excess_items})
    assert res2.status_code == 422

    # Item text rỗng
    res3 = client.post(
        "/api/v1/batches/analyses",
        json={"items": [{"type": "text", "value": "   "}]},
    )
    assert res3.status_code == 422

    # Item type không hợp lệ
    res4 = client.post(
        "/api/v1/batches/analyses",
        json={"items": [{"type": "pdf", "value": "data"}]},
    )
    assert res4.status_code == 422


def test_get_batch_by_id_guest_owner(client):
    """GET /batches/analyses/{id} trả về thông tin đợt và danh sách các mục."""
    with patch("app.api.routes.batch_analyses.process_batch_in_background"):
        create_res = client.post(
            "/api/v1/batches/analyses",
            json={
                "items": [
                    {"type": "text", "value": "Tin tuyển dụng số 1"},
                    {"type": "text", "value": "Tin tuyển dụng số 2"},
                ]
            },
        )

    assert create_res.status_code == 201
    batch_id = create_res.json()["id"]
    token = create_res.headers["X-Guest-Session-Token"]

    get_res = client.get(
        f"/api/v1/batches/analyses/{batch_id}",
        headers={"X-Guest-Session-Token": token},
    )
    assert get_res.status_code == 200
    assert get_res.headers.get("Cache-Control") == "no-store"
    data = get_res.json()
    assert "guest_session_token" not in data
    assert data["id"] == batch_id
    assert data["total_items"] == 2
    assert len(data["items"]) == 2
    assert data["items"][0]["input_value"] == "Tin tuyển dụng số 1"
    assert data["items"][1]["input_value"] == "Tin tuyển dụng số 2"


def test_get_batch_with_associated_analysis(client, db_session):
    """GET /batches/analyses/{id} trả về nested AnalysisResponse khi item có analysis_id."""
    with patch("app.api.routes.batch_analyses.process_batch_in_background"):
        create_res = client.post(
            "/api/v1/batches/analyses",
            json={"items": [{"type": "text", "value": "Tin tuyển dụng demo"}]},
        )
    batch_id = create_res.json()["id"]
    token = create_res.headers["X-Guest-Session-Token"]

    # Tạo một record Analysis giả lập kết quả xử lý thành công
    now = datetime.now(timezone.utc)
    batch = db_session.get(BatchAnalysis, uuid.UUID(batch_id))
    analysis = Analysis(
        id=uuid.uuid4(),
        session_id=batch.session_id,
        user_id=None,
        raw_text="Tin tuyển dụng demo",
        risk_label_vi="Thấp",
        verification_label_vi="Đã xác thực",
        finding_vi="Công ty uy tín",
        job={"job_title": "Developer", "company_name": "Tech Corp"},
        indicators=[],
        evidence={"matched_sources": []},
        actions_vi=["Ứng tuyển"],
        ai_insights=None,
        engine_version="1.0.0",
        rules_version="2026.10",
        created_at=now,
        expires_at=batch.expires_at,
    )
    db_session.add(analysis)
    db_session.flush()

    batch_item = (
        db_session.query(BatchAnalysisItem)
        .filter(BatchAnalysisItem.batch_id == uuid.UUID(batch_id))
        .first()
    )
    batch_item.analysis_id = analysis.id
    batch_item.status = "success"
    db_session.commit()

    get_res = client.get(
        f"/api/v1/batches/analyses/{batch_id}",
        headers={"X-Guest-Session-Token": token},
    )
    assert get_res.status_code == 200
    item_data = get_res.json()["items"][0]
    assert item_data["analysis_id"] == str(analysis.id)
    assert item_data["analysis"] is not None
    assert item_data["analysis"]["risk_label_vi"] == "Thấp"
    assert item_data["analysis"]["finding_vi"] == "Công ty uy tín"
    assert item_data["analysis"]["job"]["job_title"] == "Developer"
    assert item_data["analysis"]["job"]["company_name"] == "Tech Corp"


def test_get_batch_not_found(client):
    """GET /batches/analyses/{id} không tìm thấy trả 404."""
    res = client.get(f"/api/v1/batches/analyses/{uuid.uuid4()}")
    assert res.status_code == 404
    assert res.json()["detail"] == "Không tìm thấy lượt phân tích"


def test_get_batch_forbidden_scenarios(client, db_session):
    """Kiểm tra phân quyền truy cập GET: trả 403 khi không đúng chủ sở hữu."""
    # 1. Tạo guest batch A
    with patch("app.api.routes.batch_analyses.process_batch_in_background"):
        res_a = client.post(
            "/api/v1/batches/analyses",
            json={"items": [{"type": "text", "value": "Job A"}]},
        )
    batch_a_id = res_a.json()["id"]
    token_a = res_a.headers["X-Guest-Session-Token"]

    # 2. Tạo guest batch B
    with patch("app.api.routes.batch_analyses.process_batch_in_background"):
        res_b = client.post(
            "/api/v1/batches/analyses",
            json={"items": [{"type": "text", "value": "Job B"}]},
        )
    token_b = res_b.headers["X-Guest-Session-Token"]

    # Guest không gửi token truy cập batch A -> 403
    res_no_token = client.get(f"/api/v1/batches/analyses/{batch_a_id}")
    assert res_no_token.status_code == 403
    assert res_no_token.json()["detail"] == "Không có quyền truy cập lượt phân tích này"

    # Guest B dùng token B truy cập batch A -> 403
    res_wrong_token = client.get(
        f"/api/v1/batches/analyses/{batch_a_id}",
        headers={"X-Guest-Session-Token": token_b},
    )
    assert res_wrong_token.status_code == 403
    assert res_wrong_token.json()["detail"] == "Không có quyền truy cập lượt phân tích này"

    # 3. Tạo batch của User 1
    user1_token = register_user(client, "user1_batch@example.com")
    with patch("app.api.routes.batch_analyses.process_batch_in_background"):
        res_user1 = client.post(
            "/api/v1/batches/analyses",
            json={"items": [{"type": "text", "value": "User 1 Job"}]},
            headers={"Authorization": f"Bearer {user1_token}"},
        )
    batch_user1_id = res_user1.json()["id"]

    # User 2 truy cập batch của User 1 -> 403
    user2_token = register_user(client, "user2_batch@example.com")
    res_user2 = client.get(
        f"/api/v1/batches/analyses/{batch_user1_id}",
        headers={"Authorization": f"Bearer {user2_token}"},
    )
    assert res_user2.status_code == 403
    assert res_user2.json()["detail"] == "Không có quyền truy cập lượt phân tích này"

    # Guest truy cập batch của User 1 -> 403
    res_guest_on_user = client.get(
        f"/api/v1/batches/analyses/{batch_user1_id}",
        headers={"X-Guest-Session-Token": token_a},
    )
    assert res_guest_on_user.status_code == 403
    assert res_guest_on_user.json()["detail"] == "Không có quyền truy cập lượt phân tích này"


def test_cancel_batch_guest(client):
    """POST /batches/analyses/{id}/cancel hủy đợt phân tích của khách."""
    with patch("app.api.routes.batch_analyses.process_batch_in_background"):
        create_res = client.post(
            "/api/v1/batches/analyses",
            json={
                "items": [
                    {"type": "text", "value": "Job to cancel 1"},
                    {"type": "text", "value": "Job to cancel 2"},
                ]
            },
        )
    batch_id = create_res.json()["id"]
    token = create_res.headers["X-Guest-Session-Token"]

    cancel_res = client.post(
        f"/api/v1/batches/analyses/{batch_id}/cancel",
        headers={"X-Guest-Session-Token": token},
    )
    assert cancel_res.status_code == 200
    assert cancel_res.headers.get("Cache-Control") == "no-store"
    data = cancel_res.json()
    assert "guest_session_token" not in data
    assert data["status"] == "cancelled"
    for item in data["items"]:
        assert item["status"] == "cancelled"


def test_cancel_batch_user(client):
    """POST /batches/analyses/{id}/cancel hủy đợt phân tích của người dùng đã đăng nhập."""
    token = register_user(client, "cancel_user@example.com")
    with patch("app.api.routes.batch_analyses.process_batch_in_background"):
        create_res = client.post(
            "/api/v1/batches/analyses",
            json={"items": [{"type": "text", "value": "Job to cancel user"}]},
            headers={"Authorization": f"Bearer {token}"},
        )
    batch_id = create_res.json()["id"]

    cancel_res = client.post(
        f"/api/v1/batches/analyses/{batch_id}/cancel",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "cancelled"


def test_cancel_batch_forbidden(client):
    """POST /batches/analyses/{id}/cancel trả 403 khi người gọi không sở hữu đợt phân tích."""
    with patch("app.api.routes.batch_analyses.process_batch_in_background"):
        create_res = client.post(
            "/api/v1/batches/analyses",
            json={"items": [{"type": "text", "value": "Job"}]},
        )
    batch_id = create_res.json()["id"]

    # Không kèm token
    res1 = client.post(f"/api/v1/batches/analyses/{batch_id}/cancel")
    assert res1.status_code == 403
    assert res1.json()["detail"] == "Không có quyền truy cập lượt phân tích này"

    # Kèm token của tài khoản khác
    user_token = register_user(client, "other_cancel@example.com")
    res2 = client.post(
        f"/api/v1/batches/analyses/{batch_id}/cancel",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert res2.status_code == 403
    assert res2.json()["detail"] == "Không có quyền truy cập lượt phân tích này"


def test_cancel_batch_not_found(client):
    """POST /batches/analyses/{id}/cancel trả 404 khi không tồn tại."""
    res = client.post(f"/api/v1/batches/analyses/{uuid.uuid4()}/cancel")
    assert res.status_code == 404
    assert res.json()["detail"] == "Không tìm thấy lượt phân tích"


def test_cancel_batch_deleted_after_authorization_returns_404(client, monkeypatch):
    from app.api.routes import batch_analyses

    monkeypatch.setattr(batch_analyses, "_authorize_batch_access", lambda *args: object())
    monkeypatch.setattr(batch_analyses, "cancel_batch", lambda *args: None)

    response = client.post(f"/api/v1/batches/analyses/{uuid.uuid4()}/cancel")

    assert response.status_code == 404
    assert response.json()["detail"] == "Không tìm thấy lượt phân tích"


def test_get_batch_deleted_after_authorization_returns_404(client, monkeypatch):
    from app.api.routes import batch_analyses

    monkeypatch.setattr(batch_analyses, "_authorize_batch_access", lambda *args: object())
    monkeypatch.setattr(batch_analyses, "fail_stale_batch", lambda *args: False)
    monkeypatch.setattr(batch_analyses, "get_batch_by_id", lambda *args: None)

    response = client.get(f"/api/v1/batches/analyses/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Không tìm thấy lượt phân tích"


def test_batch_creation_limit_is_two_per_identity_and_separate_from_analyses(client):
    payload = {"items": [{"type": "text", "value": "Tin tuyển dụng kiểm thử"}]}

    def create_batch(headers=None):
        with patch("app.api.routes.batch_analyses.process_batch_in_background"):
            return client.post("/api/v1/batches/analyses", json=payload, headers=headers)

    guest_first = create_batch()
    guest_token = guest_first.headers["X-Guest-Session-Token"]
    guest_headers = {"X-Guest-Session-Token": guest_token}
    assert guest_first.status_code == 201
    assert create_batch(guest_headers).status_code == 201
    assert create_batch(guest_headers).status_code == 429

    # Batch traffic uses its own bucket; the existing single-analysis endpoint still works.
    analysis_res = client.post(
        "/api/v1/analyses",
        headers=guest_headers,
        json={"text": "Công ty tuyển dụng nhân viên kinh doanh, lương 10 triệu đồng/tháng."},
    )
    assert analysis_res.status_code == 201

    user1 = register_user(client, "batch_limit_1@example.com")
    user1_headers = {"Authorization": f"Bearer {user1}"}
    assert create_batch(user1_headers).status_code == 201
    assert create_batch(user1_headers).status_code == 201
    assert create_batch(user1_headers).status_code == 429

    user2 = register_user(client, "batch_limit_2@example.com")
    user2_headers = {"Authorization": f"Bearer {user2}"}
    assert create_batch(user2_headers).status_code == 201
    assert create_batch(user2_headers).status_code == 201

"""Test suite for R2.1 Authentication and Account Management."""

import uuid
from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.rate_limit import reset_rate_limits
from app.core.security import (
    generate_bearer_token,
    hash_bearer_token,
    hash_password,
    verify_password,
)
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.users import AccessSession, Role, User


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()

    # Seed default roles
    user_role = Role(id=uuid.uuid4(), name="user", description="Người dùng thông thường")
    admin_role = Role(id=uuid.uuid4(), name="admin", description="Quản trị viên")
    session.add_all([user_role, admin_role])
    session.commit()

    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session):
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


def test_password_hashing_and_verification():
    """Kiểm tra băm mật khẩu bằng scrypt theo chuẩn OWASP (15-128 ký tự)."""
    password = "a_very_strong_password_15_chars"
    hashed = hash_password(password)

    assert hashed.startswith("scrypt$")
    assert verify_password(password, hashed) is True
    assert verify_password("wrong_password_test", hashed) is False

    # Mật khẩu dưới 15 ký tự bị từ chối
    with pytest.raises(ValueError, match="15"):
        hash_password("short_pwd_1234")

    # Mật khẩu quá 128 ký tự bị từ chối
    with pytest.raises(ValueError, match="128"):
        hash_password("a" * 129)


def test_bearer_token_entropy_and_hash():
    """Kiểm tra sinh bearer token ngẫu nhiên và băm SHA-256."""
    token = generate_bearer_token()
    assert len(token) >= 40
    token_hash = hash_bearer_token(token)
    assert len(token_hash) == 64
    assert hash_bearer_token(token) == token_hash


def test_register_success(client: TestClient):
    """Đăng ký tài khoản thành công trả về 201 và bearer token."""
    payload = {
        "email": "test.user@example.com",
        "password": "valid_secure_password_2026",
        "full_name": "Nguyễn Văn Test",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["token_type"].lower() == "bearer"
    assert data["user"]["email"] == "test.user@example.com"
    assert data["user"]["full_name"] == "Nguyễn Văn Test"
    assert data["user"]["role"] == "user"
    assert "password" not in data["user"]
    assert response.headers.get("cache-control") == "no-store"


def test_register_duplicate_email(client: TestClient):
    """Đăng ký trùng email bị từ chối 409 Conflict."""
    payload = {
        "email": "duplicate@example.com",
        "password": "valid_secure_password_2026",
        "full_name": "Người Dùng 1",
    }
    res1 = client.post("/api/v1/auth/register", json=payload)
    assert res1.status_code == 201

    payload2 = {
        "email": "DUPLICATE@example.com",  # Email phải được chuẩn hóa case-insensitive
        "password": "valid_secure_password_2026",
        "full_name": "Người Dùng 2",
    }
    res2 = client.post("/api/v1/auth/register", json=payload2)
    assert res2.status_code == 409
    assert "tồn tại" in res2.json()["detail"].lower()


def test_register_password_length_validation(client: TestClient):
    """Mật khẩu dưới 15 ký tự trả 422."""
    payload = {
        "email": "short@example.com",
        "password": "short_pwd",
        "full_name": "Short Pwd",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422


def test_login_success_and_cache_control(client: TestClient):
    """Đăng nhập thành công trả về token và header no-store."""
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "login@example.com",
            "password": "secure_login_password_15ch",
            "full_name": "User Login",
        },
    )
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "login@example.com",
            "password": "secure_login_password_15ch",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == "login@example.com"
    assert response.headers.get("cache-control") == "no-store"


def test_login_generic_error_message(client: TestClient):
    """Đăng nhập sai email hoặc sai mật khẩu trả cùng thông báo 401 chung."""
    # Sai email
    res1 = client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@example.com", "password": "random_password_15ch"},
    )
    assert res1.status_code == 401
    assert res1.json()["detail"] == "Email hoặc mật khẩu không chính xác"

    # Đăng ký trước
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "correct@example.com",
            "password": "correct_password_15chars",
            "full_name": "User Correct",
        },
    )
    # Đúng email, sai mật khẩu
    res2 = client.post(
        "/api/v1/auth/login",
        json={"email": "correct@example.com", "password": "wrong_password_15chars"},
    )
    assert res2.status_code == 401
    assert res2.json()["detail"] == "Email hoặc mật khẩu không chính xác"


def test_logout_revokes_token(client: TestClient):
    """Logout thu hồi phiên trên server; gọi lại bằng token đó trả 401."""
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": "logout@example.com",
            "password": "secure_logout_password_15ch",
            "full_name": "User Logout",
        },
    ).json()
    token = reg["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Đọc thông tin cá nhân trước logout: 200
    res_me = client.get("/api/v1/users/me", headers=headers)
    assert res_me.status_code == 200

    # Logout
    res_logout = client.post("/api/v1/auth/logout", headers=headers)
    assert res_logout.status_code == 200

    # Đọc lại: 401
    res_me_after = client.get("/api/v1/users/me", headers=headers)
    assert res_me_after.status_code == 401


def test_expired_token_rejected(client: TestClient, db_session):
    """Token hết hạn (quá 24 giờ) bị từ chối 401."""
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": "expired@example.com",
            "password": "secure_expired_password_15ch",
            "full_name": "User Expired",
        },
    ).json()
    token = reg["access_token"]
    token_hash = hash_bearer_token(token)

    # Chỉnh sửa expires_at về quá khứ trong DB
    session_record = db_session.query(AccessSession).filter_by(token_hash=token_hash).first()
    assert session_record is not None
    session_record.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
    db_session.commit()

    headers = {"Authorization": f"Bearer {token}"}
    res = client.get("/api/v1/users/me", headers=headers)
    assert res.status_code == 401


def test_auth_rate_limiting_protects_hashing(client: TestClient):
    """Kiểm tra rate limit 10 requests / 60 giây trên auth endpoint."""
    for _ in range(10):
        client.post(
            "/api/v1/auth/login",
            json={"email": "spam@example.com", "password": "random_password_15ch"},
        )
    # Lần 11 phải bị 429
    res_blocked = client.post(
        "/api/v1/auth/login",
        json={"email": "spam@example.com", "password": "random_password_15ch"},
    )
    assert res_blocked.status_code == 429
    assert "Retry-After" in res_blocked.headers


def test_password_change_rate_limits_before_hashing(client, monkeypatch):
    import app.api.routes.users as users
    reg = client.post('/api/v1/auth/register', json={
        'email': 'password-limit@example.com', 'password': 'valid_password_2026', 'full_name': 'Test',
    })
    headers = {'Authorization': 'Bearer ' + reg.json()['access_token']}
    attempts = []
    monkeypatch.setattr(users, 'verify_password', lambda *args: attempts.append(True) or False)
    for _ in range(10):
        assert client.post('/api/v1/users/me/password', headers=headers, json={
            'old_password': 'incorrect', 'new_password': 'another_password_2026',
        }).status_code == 400
    limited = client.post('/api/v1/users/me/password', headers=headers, json={
        'old_password': 'incorrect', 'new_password': 'another_password_2026',
    })
    assert limited.status_code == 429
    assert int(limited.headers['Retry-After']) > 0
    assert len(attempts) == 10


def test_password_change_rejects_oversized_old_password(client, monkeypatch):
    import app.api.routes.users as users
    reg = client.post('/api/v1/auth/register', json={
        'email': 'password-bound@example.com', 'password': 'valid_password_2026', 'full_name': 'Test',
    })
    attempts = []
    monkeypatch.setattr(users, 'verify_password', lambda *args: attempts.append(True) or False)
    res = client.post('/api/v1/users/me/password',
        headers={'Authorization': 'Bearer ' + reg.json()['access_token']},
        json={'old_password': 'x' * 129, 'new_password': 'another_password_2026'},
    )
    assert res.status_code == 422
    assert not attempts

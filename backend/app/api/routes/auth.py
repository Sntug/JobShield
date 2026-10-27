"""Authentication endpoints: register, login, logout, and claiming guest sessions."""

import uuid
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.api.dependencies import get_current_session_and_user, get_current_user
from app.core.rate_limit import check_rate_limit
from app.core.security import (
    generate_bearer_token,
    hash_bearer_token,
    hash_guest_token,
    hash_password,
    verify_password,
)
from app.db.session import get_db
from app.models.analyses import Analysis
from app.models.guest_sessions import GuestSession
from app.models.users import AccessSession, Role, User
from app.schemas.auth import (
    ClaimGuestRequest,
    ClaimGuestResponse,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
)
from app.schemas.users import UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Đăng ký tài khoản người dùng mới",
)
def register(
    request: Request,
    response: Response,
    payload: UserRegisterRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Đăng ký tài khoản mới với email và mật khẩu."""
    check_rate_limit(request, bucket="auth")

    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email đã tồn tại trong hệ thống.",
        )

    role = db.query(Role).filter(Role.name == "user").first()
    if not role:
        role = Role(id=uuid.uuid4(), name="user", description="Người dùng chuẩn")
        db.add(role)
        db.flush()

    password_hash = hash_password(payload.password)
    now = datetime.now(timezone.utc)

    user = User(
        id=uuid.uuid4(),
        role_id=role.id,
        email=payload.email,
        password_hash=password_hash,
        full_name=payload.full_name,
        is_demo=False,
        created_at=now,
        updated_at=now,
    )
    db.add(user)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        if db.query(User).filter(User.email == payload.email).first():
            raise HTTPException(status_code=409, detail="Email đã tồn tại trong hệ thống.") from None
        raise

    raw_token = generate_bearer_token()
    token_hash = hash_bearer_token(raw_token)
    session = AccessSession(
        id=uuid.uuid4(),
        user_id=user.id,
        token_hash=token_hash,
        created_at=now,
        expires_at=now + timedelta(hours=24),
    )
    db.add(session)
    db.commit()
    db.refresh(user)

    response.headers["Cache-Control"] = "no-store"

    return TokenResponse(
        access_token=raw_token,
        token_type="bearer",
        expires_in=86400,
        user=UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=role.name,
            created_at=user.created_at,
        ),
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Đăng nhập tài khoản",
)
def login(
    request: Request,
    response: Response,
    payload: UserLoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Đăng nhập bằng email và mật khẩu, trả về Bearer token và thông tin người dùng."""
    check_rate_limit(request, bucket="auth")

    # Serialize session creation with password rotation, including its revocations.
    user = db.query(User).filter(User.email == payload.email).with_for_update().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email hoặc mật khẩu không chính xác",
        )

    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email hoặc mật khẩu không chính xác",
        )

    now = datetime.now(timezone.utc)
    raw_token = generate_bearer_token()
    token_hash = hash_bearer_token(raw_token)
    session = AccessSession(
        id=uuid.uuid4(),
        user_id=user.id,
        token_hash=token_hash,
        created_at=now,
        expires_at=now + timedelta(hours=24),
    )
    db.add(session)
    db.commit()

    response.headers["Cache-Control"] = "no-store"

    return TokenResponse(
        access_token=raw_token,
        token_type="bearer",
        expires_in=86400,
        user=UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role.name if user.role else "user",
            created_at=user.created_at,
        ),
    )


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Đăng xuất và thu hồi phiên",
)
def logout(
    response: Response,
    session_and_user=Depends(get_current_session_and_user),
    db: Session = Depends(get_db),
) -> dict:
    """Thu hồi phiên làm việc hiện tại trên máy chủ."""
    session, _ = session_and_user
    session.revoked_at = datetime.now(timezone.utc)
    db.commit()

    response.headers["Cache-Control"] = "no-store"
    return {"status": "ok", "message": "Đăng xuất thành công"}


@router.post(
    "/claim-guest",
    response_model=ClaimGuestResponse,
    status_code=status.HTTP_200_OK,
    summary="Nhận quyền sở hữu từ phiên khách sang tài khoản người dùng",
)
def claim_guest(
    response: Response,
    payload: ClaimGuestRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ClaimGuestResponse:
    """Nhận quyền tất cả các phân tích từ phiên khách sang tài khoản đăng nhập."""
    now = datetime.now(timezone.utc)
    token_hash = hash_guest_token(payload.guest_session_token)

    guest_session = (
        db.query(GuestSession)
        .filter(GuestSession.token_hash == token_hash, GuestSession.expires_at > now)
        .with_for_update()
        .first()
    )
    if not guest_session:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phiên khách không tồn tại, đã hết hạn hoặc đã được nhận quyền trước đó.",
        )

    # Lấy các phân tích hợp lệ của phiên khách
    analyses = (
        db.query(Analysis)
        .filter(Analysis.session_id == guest_session.id, Analysis.expires_at > now)
        .all()
    )

    claimed_ids = []
    for a in analyses:
        a.user_id = current_user.id
        a.session_id = None
        a.expires_at = None
        claimed_ids.append(a.id)

    # Xóa phiên khách để chống replay
    db.delete(guest_session)
    db.commit()

    response.headers["Cache-Control"] = "no-store"
    return ClaimGuestResponse(
        claimed_count=len(claimed_ids),
        claimed_ids=claimed_ids,
    )

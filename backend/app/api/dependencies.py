"""FastAPI dependencies for authentication and authorization."""

from datetime import datetime, timezone
from typing import Optional, Tuple
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import hash_bearer_token
from app.db.session import get_db
from app.models.users import AccessSession, User


def get_current_session_and_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> Tuple[AccessSession, User]:
    """Trích xuất và xác thực Bearer token từ Authorization header.

    Trả về tuple (AccessSession, User).
    Từ chối 401 nếu token thiếu, sai định dạng, hết hạn hoặc đã bị thu hồi.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Yêu cầu xác thực tài khoản",
            headers={"WWW-Authenticate": "Bearer"},
        )

    raw_token = authorization[7:].strip()
    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không hợp lệ",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_hash = hash_bearer_token(raw_token)
    now = datetime.now(timezone.utc)

    session = (
        db.query(AccessSession)
        .filter(
            AccessSession.token_hash == token_hash,
            AccessSession.revoked_at.is_(None),
            AccessSession.expires_at > now,
        )
        .first()
    )

    if not session or not session.user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Phiên đăng nhập không hợp lệ hoặc đã hết hạn",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return session, session.user


def get_current_user(
    session_and_user: Tuple[AccessSession, User] = Depends(get_current_session_and_user),
) -> User:
    """Dependency lấy người dùng hiện tại đang đăng nhập."""
    return session_and_user[1]


def get_optional_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Dependency lấy người dùng tùy chọn.

    Nếu Authorization header được gửi: bắt buộc phải hợp lệ (nếu hỏng/hết hạn thì trả 401, không tự rơi về guest).
    Nếu không gửi Authorization header: trả về None.
    """
    if not authorization:
        return None
    _, user = get_current_session_and_user(authorization=authorization, db=db)
    return user


def require_admin(
    user: User = Depends(get_current_user),
) -> User:
    """Dependency chỉ cho phép tài khoản có quyền admin truy cập."""
    if not user.role or user.role.name != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Yêu cầu quyền quản trị viên",
        )
    return user

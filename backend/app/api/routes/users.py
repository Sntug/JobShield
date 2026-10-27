"""User endpoints: profile, updates, stats, password changes."""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.security import hash_password, verify_password
from app.core.rate_limit import check_rate_limit
from app.db.session import get_db
from app.models.analyses import Analysis
from app.models.saved_analyses import SavedAnalysis
from app.models.users import AccessSession, User
from app.schemas.users import (
    PasswordChangeRequest,
    UserResponse,
    UserStatsResponse,
    UserUpdateRequest,
)

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Lấy thông tin tài khoản hiện tại",
)
def get_me(
    response: Response,
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Trả về thông tin hồ sơ của người dùng đăng nhập."""
    response.headers["Cache-Control"] = "no-store"
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role.name if current_user.role else "user",
        created_at=current_user.created_at,
    )


@router.patch(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Cập nhật họ và tên tài khoản",
)
def update_me(
    response: Response,
    payload: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserResponse:
    """Cập nhật tên hiển thị của người dùng (email là bất biến)."""
    current_user.full_name = payload.full_name
    current_user.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(current_user)

    response.headers["Cache-Control"] = "no-store"
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role.name if current_user.role else "user",
        created_at=current_user.created_at,
    )


@router.post(
    "/me/password",
    status_code=status.HTTP_200_OK,
    summary="Đổi mật khẩu tài khoản và thu hồi toàn bộ phiên",
)
def change_password(
    request: Request,
    response: Response,
    payload: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Đổi mật khẩu người dùng. Thu hồi tất cả các phiên đang hoạt động."""
    check_rate_limit(request, bucket="auth-password")
    # The dependency may have cached a password that changed while waiting for this lock.
    current_user = (
        db.query(User).filter(User.id == current_user.id)
        .populate_existing().with_for_update().one()
    )
    if not verify_password(payload.old_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mật khẩu cũ không chính xác.",
        )

    now = datetime.now(timezone.utc)
    new_hash = hash_password(payload.new_password)
    current_user.password_hash = new_hash
    current_user.updated_at = now

    # Thu hồi mọi phiên của người dùng trên toàn hệ thống
    db.query(AccessSession).filter(
        AccessSession.user_id == current_user.id,
        AccessSession.revoked_at.is_(None),
    ).update({"revoked_at": now})

    db.commit()

    response.headers["Cache-Control"] = "no-store"
    return {"status": "ok", "message": "Đổi mật khẩu thành công. Vui lòng đăng nhập lại."}


@router.get(
    "/me/stats",
    response_model=UserStatsResponse,
    status_code=status.HTTP_200_OK,
    summary="Thống kê phân tích của người dùng hiện tại",
)
def get_user_stats(
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserStatsResponse:
    """Trả về thống kê số lượng bài phân tích, số bài lưu và phân bổ rủi ro."""
    total_analyses = (
        db.query(Analysis).filter(Analysis.user_id == current_user.id).count()
    )
    saved_analyses = (
        db.query(SavedAnalysis).filter(SavedAnalysis.user_id == current_user.id).count()
    )

    # Phân bổ rủi ro theo risk_label_vi
    analyses = (
        db.query(Analysis.risk_label_vi)
        .filter(Analysis.user_id == current_user.id)
        .all()
    )
    risk_distribution = {}
    for (label,) in analyses:
        risk_distribution[label] = risk_distribution.get(label, 0) + 1

    response.headers["Cache-Control"] = "no-store"
    return UserStatsResponse(
        total_analyses=total_analyses,
        saved_analyses=saved_analyses,
        risk_distribution=risk_distribution,
    )

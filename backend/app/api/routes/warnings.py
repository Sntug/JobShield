"""API routes for public warnings: publication, superseding, and withdrawal."""

from datetime import datetime, timezone
from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session
from sqlalchemy import update

from app.api.dependencies import require_admin
from app.db.session import get_db
from app.models.reports import PublicWarning, Report, ModerationAction
from app.models.users import User
from app.schemas.reports import (
    PublicWarningCreate,
    PublicWarningListResponse,
    PublicWarningResponse,
    PublicWarningSupersede,
    PublicWarningWithdraw,
)

router = APIRouter(tags=["warnings"])


# ---------------------------------------------------------
# 1. Public Endpoints (Không yêu cầu đăng nhập)
# ---------------------------------------------------------

@router.get(
    "/warnings",
    response_model=PublicWarningListResponse,
    status_code=status.HTTP_200_OK,
    summary="Danh sách cảnh báo cộng đồng công khai",
)
def list_public_warnings(
    response: Response,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
) -> PublicWarningListResponse:
    """Tra cứu các bản cảnh báo tuyển dụng lừa đảo đang có hiệu lực công khai."""
    response.headers["Cache-Control"] = "no-store"
    query = db.query(PublicWarning).filter(PublicWarning.status == "published")
    total = query.count()
    offset = (page - 1) * page_size
    items = (
        query.order_by(PublicWarning.published_at.desc(), PublicWarning.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )
    return PublicWarningListResponse(
        items=[PublicWarningResponse.model_validate(w) for w in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/warnings/{warning_id}",
    response_model=PublicWarningResponse,
    status_code=status.HTTP_200_OK,
    summary="Xem chi tiết một bản cảnh báo công khai",
)
def get_public_warning(
    warning_id: uuid.UUID,
    response: Response,
    db: Session = Depends(get_db),
) -> PublicWarningResponse:
    """Xem chi tiết nội dung và căn cứ của một bản cảnh báo cộng đồng."""
    response.headers["Cache-Control"] = "no-store"
    warning = db.query(PublicWarning).filter(PublicWarning.id == warning_id).first()
    if not warning:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bản cảnh báo không tồn tại hoặc đã bị thu hồi.",
        )
    result = PublicWarningResponse.model_validate(warning)
    if warning.status != "published":
        successor = db.query(PublicWarning).filter(PublicWarning.previous_warning_id == warning.id).first()
        result = result.model_copy(update={"title_vi": "Cảnh báo đã được đính chính hoặc thu hồi", "public_summary_vi": "", "public_sources_snapshot": [], "next_warning_id": successor.id if successor else None})
    return result


@router.get("/admin/warnings", response_model=PublicWarningListResponse)
def list_admin_warnings(response: Response, page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=50), admin_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store"
    query = db.query(PublicWarning)
    return PublicWarningListResponse(items=[PublicWarningResponse.model_validate(w) for w in query.order_by(PublicWarning.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()], total=query.count(), page=page, page_size=page_size)


# ---------------------------------------------------------
# 2. Admin Management Endpoints
# ---------------------------------------------------------

@router.post(
    "/admin/warnings",
    response_model=PublicWarningResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Xuất bản cảnh báo cộng đồng mới",
)
def create_public_warning(
    payload: PublicWarningCreate,
    response: Response,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> PublicWarningResponse:
    """Quản trị viên xuất bản một bản cảnh báo cộng đồng mới (đã lược bỏ PII người báo cáo)."""
    response.headers["Cache-Control"] = "no-store"
    decision_id = payload.decision_id
    if payload.report_id is not None:
        report = db.query(Report).filter(Report.id == payload.report_id).first()
        decision = db.query(ModerationAction).filter(ModerationAction.report_id == payload.report_id, ModerationAction.report_version_after == report.version).first() if report else None
        if not report or report.status != "verified" or not decision or decision.to_status != "verified" or (decision_id is not None and decision_id != decision.id):
            raise HTTPException(status_code=422, detail="Chỉ xuất bản từ quyết định xác minh hiện hành của đúng báo cáo.")
        decision_id = decision.id
    elif decision_id is not None:
        raise HTTPException(status_code=422, detail="Quyết định kiểm duyệt cần đi kèm báo cáo.")
    now = datetime.now(timezone.utc)
    warning = PublicWarning(
        title_vi=payload.title_vi,
        public_summary_vi=payload.public_summary_vi,
        report_id=payload.report_id,
        decision_id=decision_id,
        public_sources_snapshot=[source.model_dump() for source in payload.public_sources_snapshot],
        status="published",
        revision=1,
        created_by=admin_user.id,
        published_at=now,
    )
    db.add(warning)
    db.commit()
    db.refresh(warning)
    return PublicWarningResponse.model_validate(warning)


@router.post(
    "/admin/warnings/{warning_id}/supersede",
    response_model=PublicWarningResponse,
    status_code=status.HTTP_200_OK,
    summary="Đính chính / thay thế bản cảnh báo",
)
def supersede_public_warning(
    warning_id: uuid.UUID,
    payload: PublicWarningSupersede,
    response: Response,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> PublicWarningResponse:
    """Tạo bản cảnh báo phiên bản mới thay thế bản cũ (superseded) khi có thông tin đính chính."""
    response.headers["Cache-Control"] = "no-store"
    old_warning = (
        db.query(PublicWarning).filter(PublicWarning.id == warning_id).first()
    )
    if not old_warning:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bản cảnh báo không tồn tại.",
        )
    if old_warning.status != "published":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Chỉ có thể đính chính bản cảnh báo đang ở trạng thái published.",
        )

    now = datetime.now(timezone.utc)
    changed = db.execute(update(PublicWarning).where(PublicWarning.id == warning_id, PublicWarning.status == "published").values(status="superseded").execution_options(synchronize_session=False)).rowcount
    if changed != 1:
        db.rollback()
        raise HTTPException(status_code=409, detail="Cảnh báo đã thay đổi. Vui lòng tải lại.")

    new_warning = PublicWarning(
        title_vi=payload.title_vi,
        public_summary_vi=payload.public_summary_vi,
        report_id=old_warning.report_id,
        decision_id=old_warning.decision_id,
        previous_warning_id=old_warning.id,
        revision=old_warning.revision + 1,
        status="published",
        public_sources_snapshot=[source.model_dump() for source in payload.public_sources_snapshot],
        created_by=admin_user.id,
        published_at=now,
    )
    db.add(new_warning)
    db.commit()
    db.refresh(new_warning)
    return PublicWarningResponse.model_validate(new_warning)


@router.post(
    "/admin/warnings/{warning_id}/withdraw",
    response_model=PublicWarningResponse,
    status_code=status.HTTP_200_OK,
    summary="Thu hồi bản cảnh báo cộng đồng",
)
def withdraw_public_warning(
    warning_id: uuid.UUID,
    payload: PublicWarningWithdraw,
    response: Response,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> PublicWarningResponse:
    """Thu hồi bản cảnh báo kèm lý do thu hồi minh bạch."""
    response.headers["Cache-Control"] = "no-store"
    warning = db.query(PublicWarning).filter(PublicWarning.id == warning_id).first()
    if not warning:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bản cảnh báo không tồn tại.",
        )
    if warning.status != "published":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Chỉ có thể thu hồi revision đang công khai.",
        )

    now = datetime.now(timezone.utc)
    changed = db.execute(update(PublicWarning).where(PublicWarning.id == warning_id, PublicWarning.status == "published").values(status="withdrawn", withdrawn_by=admin_user.id, withdrawal_actor_type="admin", withdrawn_at=now, withdrawal_reason_vi=payload.withdrawal_reason_vi).execution_options(synchronize_session=False)).rowcount
    if changed != 1:
        db.rollback()
        raise HTTPException(status_code=409, detail="Cảnh báo đã thay đổi. Vui lòng tải lại.")

    db.commit()
    db.refresh(warning)
    return PublicWarningResponse.model_validate(warning)

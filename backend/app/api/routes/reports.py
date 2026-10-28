"""API routes for user report submissions and tracking."""

from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.users import User
from app.schemas.reports import (
    ModerationActionResponse,
    ReportCreate,
    ReportEvidenceResponse,
    ReportListResponse,
    ReportResponse,
)
from app.services import report_moderation

router = APIRouter(prefix="/reports", tags=["reports"])


def serialize_user_report(report) -> ReportResponse:
    """Chuyển đổi report entity thành ReportResponse an toàn cho người dùng (không chứa private_note)."""
    evidences = [
        ReportEvidenceResponse(
            id=ev.id,
            evidence_type=ev.evidence_type,
            content=ev.content,
            source_url=ev.source_url,
            file_name=ev.file_name,
            mime_type=ev.mime_type,
            size_bytes=ev.size_bytes,
            created_at=ev.created_at,
        )
        for ev in (report.evidences or [])
    ]

    moderation_actions = [
        ModerationActionResponse(
            id=act.id,
            action_type=act.action_type,
            from_status=act.from_status,
            to_status=act.to_status,
            decision_summary=act.decision_summary,
            created_at=act.created_at,
        )
        for act in (report.moderation_actions or [])
    ]

    return ReportResponse(
        id=report.id,
        reason=report.reason,
        description=report.description,
        status=report.status,
        version=report.version,
        analysis_id=report.analysis_id,
        created_at=report.created_at,
        updated_at=report.updated_at,
        evidences=evidences,
        moderation_actions=moderation_actions,
    )


@router.post(
    "",
    response_model=ReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Gửi báo cáo tin tuyển dụng đáng ngờ",
)
def submit_report(
    response: Response,
    payload: ReportCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReportResponse:
    """Người dùng đăng nhập gửi báo cáo kèm lý do, mô tả và bằng chứng."""
    response.headers["Cache-Control"] = "no-store"
    report = report_moderation.create_report(db=db, reporter=current_user, payload=payload)
    return serialize_user_report(report)


@router.get(
    "",
    response_model=ReportListResponse,
    status_code=status.HTTP_200_OK,
    summary="Lấy danh sách báo cáo của tôi",
)
def list_my_reports(
    response: Response,
    page: int = Query(1, ge=1, description="Số trang"),
    page_size: int = Query(10, ge=1, le=50, description="Số lượng mỗi trang"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReportListResponse:
    """Xem danh sách các báo cáo do chính người dùng hiện tại đã gửi."""
    response.headers["Cache-Control"] = "no-store"
    items, total = report_moderation.get_user_reports(
        db=db, user_id=current_user.id, page=page, page_size=page_size
    )
    return ReportListResponse(
        items=[serialize_user_report(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{report_id}",
    response_model=ReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Xem chi tiết báo cáo của tôi",
)
def get_my_report(
    report_id: uuid.UUID,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReportResponse:
    """Xem chi tiết và kết quả xử lý của một báo cáo thuộc về người dùng."""
    response.headers["Cache-Control"] = "no-store"
    report = report_moderation.get_user_report_by_id(
        db=db, report_id=report_id, user_id=current_user.id
    )
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Báo cáo không tồn tại hoặc bạn không có quyền truy cập.",
        )
    return serialize_user_report(report)

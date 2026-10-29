"""Service for community reports and moderation workflow."""

from datetime import datetime, timezone
from typing import List, Optional, Tuple
import uuid
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import update

from app.models.analyses import Analysis
from app.models.reports import ModerationAction, Report, ReportEvidence
from app.models.users import User
from app.schemas.reports import ModerationActionCreate, ReportCreate


def create_report(db: Session, reporter: User, payload: ReportCreate) -> Report:
    """Tạo báo cáo tuyển dụng mới từ người dùng đăng nhập."""
    if payload.analysis_id:
        analysis = db.query(Analysis).filter(Analysis.id == payload.analysis_id, Analysis.user_id == reporter.id).first()
        if not analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bản ghi phân tích liên kết không tồn tại.",
            )

    report = Report(
        reporter_id=reporter.id,
        analysis_id=payload.analysis_id,
        reason=payload.reason,
        description=payload.description,
        status="pending",
        version=1,
    )
    db.add(report)
    db.flush()

    for ev in payload.evidences:
        evidence_record = ReportEvidence(
            report_id=report.id,
            evidence_type=ev.evidence_type,
            content=ev.content,
            source_url=ev.source_url,
            storage_key=ev.storage_key,
            file_name=ev.file_name,
            mime_type=ev.mime_type,
            size_bytes=ev.size_bytes,
        )
        db.add(evidence_record)

    db.commit()
    db.refresh(report)
    return report


def get_user_reports(
    db: Session, user_id: uuid.UUID, page: int = 1, page_size: int = 10
) -> Tuple[List[Report], int]:
    """Lấy danh sách báo cáo do chính người dùng gửi, phân trang."""
    query = db.query(Report).filter(Report.reporter_id == user_id)
    total = query.count()
    offset = (page - 1) * page_size
    items = (
        query.order_by(Report.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )
    return items, total


def get_user_report_by_id(
    db: Session, report_id: uuid.UUID, user_id: uuid.UUID
) -> Optional[Report]:
    """Lấy chi tiết báo cáo của người dùng (từ chối nếu không phải chủ sở hữu)."""
    return (
        db.query(Report)
        .filter(Report.id == report_id, Report.reporter_id == user_id)
        .first()
    )


def get_admin_reports(
    db: Session,
    status_filter: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
) -> Tuple[List[Report], int]:
    """Danh sách hàng đợi kiểm duyệt dành cho quản trị viên."""
    query = db.query(Report)
    if status_filter:
        query = query.filter(Report.status == status_filter)
    total = query.count()
    offset = (page - 1) * page_size
    items = (
        query.order_by(Report.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )
    return items, total


def get_admin_report_by_id(db: Session, report_id: uuid.UUID) -> Optional[Report]:
    """Lấy chi tiết báo cáo dành cho quản trị viên."""
    return db.query(Report).filter(Report.id == report_id).first()


def moderate_report(
    db: Session,
    report_id: uuid.UUID,
    moderator: User,
    payload: ModerationActionCreate,
) -> Report:
    """Xử lý kiểm duyệt báo cáo kèm cơ chế khóa lạc quan chống ghi đè đồng thời."""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Báo cáo không tồn tại.",
        )

    # Chống ghi đè đồng thời giữa hai quản trị viên
    if report.version != payload.expected_version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="REPORT_VERSION_CONFLICT: Báo cáo đã được chỉnh sửa bởi quản trị viên khác. Vui lòng tải lại dữ liệu mới nhất.",
        )

    from_status = report.status
    to_status = payload.to_status

    changed = db.execute(
        update(Report).where(Report.id == report_id, Report.version == payload.expected_version)
        .values(status=to_status, version=Report.version + 1, updated_at=datetime.now(timezone.utc))
        .execution_options(synchronize_session=False)
    ).rowcount
    if changed != 1:
        db.rollback()
        raise HTTPException(status_code=409, detail="REPORT_VERSION_CONFLICT: Vui lòng tải lại báo cáo.")

    action = ModerationAction(
        report_id=report.id,
        moderator_id=moderator.id,
        action_type=payload.action_type,
        from_status=from_status,
        to_status=to_status,
        report_version_after=payload.expected_version + 1,
        reviewed_evidence_ids=payload.reviewed_evidence_ids,
        decision_summary=payload.decision_summary,
        private_note=payload.private_note,
    )
    db.add(action)

    db.commit()
    db.refresh(report)
    return report

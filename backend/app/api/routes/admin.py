"""API routes for administrative functions: moderation, employer curation, rules, and statistics."""

from datetime import datetime, timezone
from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_admin
from app.db.session import get_db
from app.models.indicators import RiskIndicator
from app.models.reports import Report
from app.models.users import User
from app.models.verifications import EmployerClaim, EmployerSource, VerifiedEmployer
from app.schemas.employers import (
    EmployerAdminCreate,
    EmployerAdminListResponse,
    EmployerAdminResponse,
    EmployerAdminUpdate,
    EmployerClaimAdminCreate,
    EmployerSourceAdminCreate,
    EmployerSourceAdminResponse,
)
from app.schemas.reports import (
    ModerationActionAdminResponse,
    ModerationActionCreate,
    ReportAdminListResponse,
    ReportAdminResponse,
    ReportEvidenceResponse,
)
from app.schemas.risk import (
    RiskIndicatorListResponse,
    RiskIndicatorResponse,
    RiskIndicatorUpdateRequest,
)
from app.schemas.statistics import AdminStatsResponse
from app.services import report_moderation, statistics
from app.services.verification_values import claim_key

router = APIRouter(prefix="/admin", tags=["admin"])


def serialize_admin_report(report: Report) -> ReportAdminResponse:
    """Chuyển đổi report entity thành ReportAdminResponse đầy đủ thông tin (gồm private_note và reporter)."""
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
        ModerationActionAdminResponse(
            id=act.id,
            action_type=act.action_type,
            from_status=act.from_status,
            to_status=act.to_status,
            decision_summary=act.decision_summary,
            created_at=act.created_at,
            moderator_id=act.moderator_id,
            moderator_name=act.moderator.full_name if act.moderator else None,
            report_version_after=act.report_version_after,
            reviewed_evidence_ids=act.reviewed_evidence_ids,
            private_note=act.private_note,
        )
        for act in (report.moderation_actions or [])
    ]

    return ReportAdminResponse(
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
        reporter_id=report.reporter_id,
        reporter_email=report.reporter.email if report.reporter else None,
        reporter_name=report.reporter.full_name if report.reporter else None,
    )


# ---------------------------------------------------------
# 1. Moderation Queue & Detail
# ---------------------------------------------------------

@router.get(
    "/reports",
    response_model=ReportAdminListResponse,
    status_code=status.HTTP_200_OK,
    summary="Hàng đợi kiểm duyệt báo cáo",
)
def list_reports(
    response: Response,
    status_filter: Optional[str] = Query(None, alias="status", description="Lọc theo trạng thái"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ReportAdminListResponse:
    """Xem danh sách toàn bộ báo cáo cần kiểm duyệt."""
    response.headers["Cache-Control"] = "no-store"
    items, total = report_moderation.get_admin_reports(
        db=db, status_filter=status_filter, page=page, page_size=page_size
    )
    return ReportAdminListResponse(
        items=[serialize_admin_report(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/reports/{report_id}",
    response_model=ReportAdminResponse,
    status_code=status.HTTP_200_OK,
    summary="Chi tiết báo cáo cho quản trị viên",
)
def get_report(
    report_id: uuid.UUID,
    response: Response,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ReportAdminResponse:
    """Xem chi tiết báo cáo kèm bằng chứng, thông tin người gửi và lịch sử duyệt."""
    response.headers["Cache-Control"] = "no-store"
    report = report_moderation.get_admin_report_by_id(db=db, report_id=report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Báo cáo không tồn tại.",
        )
    return serialize_admin_report(report)


@router.post(
    "/reports/{report_id}/moderation",
    response_model=ReportAdminResponse,
    status_code=status.HTTP_200_OK,
    summary="Thực hiện kiểm duyệt báo cáo",
)
def moderate_report(
    report_id: uuid.UUID,
    payload: ModerationActionCreate,
    response: Response,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ReportAdminResponse:
    """Cập nhật trạng thái báo cáo, ghi nhận lý do và kiểm tra phiên bản chống ghi đè."""
    response.headers["Cache-Control"] = "no-store"
    updated_report = report_moderation.moderate_report(
        db=db, report_id=report_id, moderator=admin_user, payload=payload
    )
    return serialize_admin_report(updated_report)


# ---------------------------------------------------------
# 2. Employer & Source Curation
# ---------------------------------------------------------

@router.get(
    "/employers",
    response_model=EmployerAdminListResponse,
    status_code=status.HTTP_200_OK,
    summary="Danh sách nhà tuyển dụng trong kho nguồn",
)
def list_employers(
    response: Response,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    search: Optional[str] = Query(None),
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> EmployerAdminListResponse:
    """Lấy danh sách các nhà tuyển dụng đã được quản lý trong kho xác minh."""
    response.headers["Cache-Control"] = "no-store"
    query = db.query(VerifiedEmployer)
    if search:
        search_term = f"%{search.strip()}%"
        query = query.filter(
            (VerifiedEmployer.legal_name.ilike(search_term))
            | (VerifiedEmployer.tax_id.ilike(search_term))
        )
    total = query.count()
    offset = (page - 1) * page_size
    employers = (
        query.order_by(VerifiedEmployer.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    items = []
    for emp in employers:
        sources_cnt = (
            db.query(EmployerSource)
            .filter(EmployerSource.employer_id == emp.id)
            .count()
        )
        items.append(
            EmployerAdminResponse(
                id=emp.id,
                legal_name=emp.legal_name,
                tax_id=emp.tax_id,
                is_active=emp.is_active,
                created_at=emp.created_at,
                updated_at=emp.updated_at,
                sources_count=sources_cnt,
            )
        )

    return EmployerAdminListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/employers",
    response_model=EmployerAdminResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Thêm nhà tuyển dụng mới vào kho nguồn",
)
def create_employer(
    payload: EmployerAdminCreate,
    response: Response,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> EmployerAdminResponse:
    """Tạo hồ sơ nhà tuyển dụng mới để chuẩn bị xác minh nguồn."""
    response.headers["Cache-Control"] = "no-store"
    if payload.tax_id:
        existing = (
            db.query(VerifiedEmployer)
            .filter(VerifiedEmployer.tax_id == payload.tax_id)
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mã số thuế này đã tồn tại trong hệ thống.",
            )

    employer = VerifiedEmployer(
        legal_name=payload.legal_name,
        tax_id=payload.tax_id,
        is_active=True,
    )
    db.add(employer)
    db.commit()
    db.refresh(employer)
    return EmployerAdminResponse(
        id=employer.id,
        legal_name=employer.legal_name,
        tax_id=employer.tax_id,
        is_active=employer.is_active,
        created_at=employer.created_at,
        updated_at=employer.updated_at,
        sources_count=0,
    )


@router.patch(
    "/employers/{employer_id}",
    response_model=EmployerAdminResponse,
    status_code=status.HTTP_200_OK,
    summary="Cập nhật thông tin nhà tuyển dụng",
)
def update_employer(
    employer_id: uuid.UUID,
    payload: EmployerAdminUpdate,
    response: Response,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> EmployerAdminResponse:
    """Cập nhật tên, mã số thuế hoặc trạng thái kích hoạt của nhà tuyển dụng."""
    response.headers["Cache-Control"] = "no-store"
    employer = db.query(VerifiedEmployer).filter(VerifiedEmployer.id == employer_id).first()
    if not employer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nhà tuyển dụng không tồn tại.",
        )

    if payload.legal_name is not None:
        employer.legal_name = payload.legal_name
    if "tax_id" in payload.model_fields_set:
        if payload.tax_id is not None and payload.tax_id != employer.tax_id:
            existing = (
                db.query(VerifiedEmployer)
                .filter(VerifiedEmployer.tax_id == payload.tax_id)
                .first()
            )
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Mã số thuế này đã tồn tại trong hệ thống.",
                )
        employer.tax_id = payload.tax_id
    if payload.is_active is not None:
        employer.is_active = payload.is_active

    employer.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(employer)

    sources_cnt = (
        db.query(EmployerSource)
        .filter(EmployerSource.employer_id == employer.id)
        .count()
    )
    return EmployerAdminResponse(
        id=employer.id,
        legal_name=employer.legal_name,
        tax_id=employer.tax_id,
        is_active=employer.is_active,
        created_at=employer.created_at,
        updated_at=employer.updated_at,
        sources_count=sources_cnt,
    )


@router.get("/employers/{employer_id}/sources", response_model=List[EmployerSourceAdminResponse])
def list_employer_sources(employer_id: uuid.UUID, response: Response, admin_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store"
    return db.query(EmployerSource).filter(EmployerSource.employer_id == employer_id).order_by(EmployerSource.verified_at.desc()).all()


@router.post(
    "/employers/{employer_id}/sources",
    status_code=status.HTTP_201_CREATED,
    summary="Thêm nguồn xác minh cho nhà tuyển dụng",
)
def add_employer_source(
    employer_id: uuid.UUID,
    payload: EmployerSourceAdminCreate,
    response: Response,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    """Thêm tài liệu hoặc liên kết nguồn xác minh kèm trích đoạn bằng chứng."""
    response.headers["Cache-Control"] = "no-store"
    employer = db.query(VerifiedEmployer).filter(VerifiedEmployer.id == employer_id).first()
    if not employer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nhà tuyển dụng không tồn tại.",
        )

    source = EmployerSource(
        employer_id=employer.id,
        url=payload.url,
        label_vi=payload.label_vi,
        evidence_excerpt_vi=payload.evidence_excerpt_vi,
        reviewed_by=admin_user.full_name or admin_user.email,
        verified_at=datetime.now(timezone.utc),
        valid_until=payload.valid_until,
        source_revision=1,
        is_active=True,
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return {"id": str(source.id), "employer_id": str(employer.id), "status": "created"}


@router.post(
    "/employers/{employer_id}/claims",
    status_code=status.HTTP_201_CREATED,
    summary="Thêm claim đối chiếu cho nhà tuyển dụng",
)
def add_employer_claim(
    employer_id: uuid.UUID,
    payload: EmployerClaimAdminCreate,
    response: Response,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    """Thêm claim trường dữ liệu (email, website, tax_id...) được bảo chứng bởi nguồn."""
    response.headers["Cache-Control"] = "no-store"
    source = (
        db.query(EmployerSource)
        .filter(EmployerSource.id == payload.source_id, EmployerSource.employer_id == employer_id, EmployerSource.is_active.is_(True))
        .first()
    )
    if not source:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nhà tuyển dụng cần có ít nhất một nguồn xác minh hoạt động trước khi thêm claim.",
        )

    now = datetime.now(timezone.utc)
    expiry = source.valid_until
    if expiry is not None and (expiry.replace(tzinfo=timezone.utc) if expiry.tzinfo is None else expiry) <= now:
        raise HTTPException(status_code=400, detail="Nguồn xác minh đã hết hạn.")
    if payload.field == "bank_account":
        from app.services.verification_values import bank_private_values
        public = " ".join((source.url, source.label_vi, source.evidence_excerpt_vi)).casefold()
        if any(value.casefold() in public for value in bank_private_values(payload.value)):
            raise HTTPException(status_code=422, detail="Nguồn public chứa dữ liệu ngân hàng chưa lược bỏ.")
    key = claim_key(payload.field, payload.value)
    existing = db.query(EmployerClaim).filter_by(source_id=source.id, field=payload.field, value_key=key, assertion=payload.assertion).first()
    if existing:
        raise HTTPException(status_code=409, detail="Claim đã tồn tại trong nguồn này.")
    claim = EmployerClaim(
        employer_id=employer_id,
        source_id=source.id,
        field=payload.field,
        value_key=key,
        assertion=payload.assertion,
        is_active=True,
    )
    db.add(claim)
    db.commit()
    db.refresh(claim)
    return {"id": str(claim.id), "field": payload.field, "status": "created"}


# ---------------------------------------------------------
# 3. Detection Rule Configuration
# ---------------------------------------------------------

@router.get(
    "/rules",
    response_model=RiskIndicatorListResponse,
    status_code=status.HTTP_200_OK,
    summary="Danh sách các quy tắc phát hiện rủi ro",
)
def list_rules(
    response: Response,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> RiskIndicatorListResponse:
    """Lấy danh sách 8 quy tắc chỉ dấu rủi ro và trạng thái bật/tắt hiện tại."""
    response.headers["Cache-Control"] = "no-store"
    rules = db.query(RiskIndicator).order_by(RiskIndicator.code).all()
    return RiskIndicatorListResponse(
        items=[RiskIndicatorResponse.model_validate(r) for r in rules]
    )


@router.patch(
    "/rules/{code}",
    response_model=RiskIndicatorResponse,
    status_code=status.HTTP_200_OK,
    summary="Cập nhật trạng thái hoặc trọng số quy tắc",
)
def update_rule(
    code: str,
    payload: RiskIndicatorUpdateRequest,
    response: Response,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> RiskIndicatorResponse:
    """Bật/tắt quy tắc hoặc điều chỉnh trọng số đánh giá rủi ro."""
    response.headers["Cache-Control"] = "no-store"
    rule = db.query(RiskIndicator).filter(RiskIndicator.code == code).first()
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quy tắc {code} không tồn tại.",
        )

    if payload.enabled is not None:
        rule.enabled = payload.enabled
    if payload.weight is not None:
        rule.weight = payload.weight
    if payload.description is not None:
        rule.description = payload.description

    rule.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(rule)
    return RiskIndicatorResponse.model_validate(rule)


# ---------------------------------------------------------
# 4. System Statistics
# ---------------------------------------------------------

@router.get(
    "/statistics",
    response_model=AdminStatsResponse,
    status_code=status.HTTP_200_OK,
    summary="Thống kê tổng hợp toàn hệ thống",
)
def get_admin_statistics(
    response: Response,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminStatsResponse:
    """Lấy số liệu thống kê tổng quát về người dùng, phân tích, báo cáo và kho nguồn."""
    response.headers["Cache-Control"] = "no-store"
    return statistics.get_admin_statistics(db=db)

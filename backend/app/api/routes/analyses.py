"""API endpoints for recruitment text analysis."""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.core.rate_limit import check_rate_limit
from app.core.security import generate_guest_token, hash_guest_token
from app.db.session import get_db
from app.models.analyses import Analysis
from app.models.guest_sessions import GuestSession
from app.schemas.analyses import AnalysisCreate, AnalysisResponse, JobExtracted, IndicatorItem, EvidenceData
from app.services.analysis import perform_text_analysis

router = APIRouter(prefix="/analyses", tags=["analyses"])


@router.post(
    "",
    response_model=AnalysisResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Phân tích tin tuyển dụng cho khách",
)
def create_analysis(
    request: Request,
    response: Response,
    payload: AnalysisCreate,
    x_guest_session_token: Optional[str] = Header(None, alias="X-Guest-Session-Token"),
    db: Session = Depends(get_db),
) -> AnalysisResponse:
    """Tạo phân tích mới từ văn bản, gán phiên khách và trả về kết quả kèm dấu hiệu."""
    # Kiểm tra giới hạn tần suất request (chống spam)
    check_rate_limit(request)

    now = datetime.now(timezone.utc)
    issued_token: Optional[str] = None

    if x_guest_session_token is not None:
        # Client gửi header nhưng rỗng hoặc sai -> 401 SESSION_INVALID
        if not x_guest_session_token.strip():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="SESSION_INVALID",
            )
        token_hash = hash_guest_token(x_guest_session_token)
        session = (
            db.query(GuestSession)
            .filter(GuestSession.token_hash == token_hash, GuestSession.expires_at > now)
            .first()
        )
        if not session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="SESSION_INVALID",
            )
    else:
        # Client không gửi header -> cấp phiên mới với TTL 24h
        raw_token = generate_guest_token()
        token_hash = hash_guest_token(raw_token)
        expires_at = now + timedelta(hours=24)
        session = GuestSession(
            token_hash=token_hash,
            created_at=now,
            expires_at=expires_at,
        )
        db.add(session)
        db.flush()
        issued_token = raw_token

    # Thực hiện phân tích văn bản thuần
    job, indicators, risk_label_vi, verification_label_vi, finding_vi, evidence, actions_vi = (
        perform_text_analysis(payload.text, is_demo=False)
    )

    # Lưu snapshot bất biến vào cơ sở dữ liệu
    analysis = Analysis(
        id=uuid.uuid4(),
        session_id=session.id,
        raw_text=payload.text,
        risk_label_vi=risk_label_vi,
        verification_label_vi=verification_label_vi,
        finding_vi=finding_vi,
        job=job.model_dump(),
        indicators=[ind.model_dump() for ind in indicators],
        evidence=evidence.model_dump(),
        actions_vi=actions_vi,
        engine_version="0.1.0",
        rules_version="2026.10",
        created_at=now,
        expires_at=session.expires_at,
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    # Đặt header chống cache
    response.headers["Cache-Control"] = "no-store"

    return AnalysisResponse(
        id=analysis.id,
        guest_session_token=issued_token,
        risk_label_vi=analysis.risk_label_vi,
        verification_label_vi=analysis.verification_label_vi,
        finding_vi=analysis.finding_vi,
        job=JobExtracted(**analysis.job),
        indicators=[IndicatorItem(**ind) for ind in analysis.indicators],
        evidence=EvidenceData(**analysis.evidence),
        actions_vi=analysis.actions_vi,
        engine_version=analysis.engine_version,
        rules_version=analysis.rules_version,
        created_at=analysis.created_at,
        expires_at=analysis.expires_at,
    )


@router.get(
    "/{analysis_id}",
    response_model=AnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Đọc lại kết quả phân tích theo phiên khách",
)
def get_analysis(
    analysis_id: uuid.UUID,
    response: Response,
    x_guest_session_token: Optional[str] = Header(None, alias="X-Guest-Session-Token"),
    db: Session = Depends(get_db),
) -> AnalysisResponse:
    """Đọc lại kết quả phân tích. Bắt buộc token phiên khách hợp lệ; sai hoặc quá hạn trả 404."""
    if not x_guest_session_token:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")

    now = datetime.now(timezone.utc)
    token_hash = hash_guest_token(x_guest_session_token)

    session = (
        db.query(GuestSession)
        .filter(GuestSession.token_hash == token_hash, GuestSession.expires_at > now)
        .first()
    )
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")

    analysis = (
        db.query(Analysis)
        .filter(
            Analysis.id == analysis_id,
            Analysis.session_id == session.id,
            Analysis.expires_at > now,
        )
        .first()
    )
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")

    response.headers["Cache-Control"] = "no-store"

    return AnalysisResponse(
        id=analysis.id,
        guest_session_token=None,  # Tuyệt đối không trả lại token trên GET
        risk_label_vi=analysis.risk_label_vi,
        verification_label_vi=analysis.verification_label_vi,
        finding_vi=analysis.finding_vi,
        job=JobExtracted(**analysis.job),
        indicators=[IndicatorItem(**ind) for ind in analysis.indicators],
        evidence=EvidenceData(**analysis.evidence),
        actions_vi=analysis.actions_vi,
        engine_version=analysis.engine_version,
        rules_version=analysis.rules_version,
        created_at=analysis.created_at,
        expires_at=analysis.expires_at,
    )

"""API endpoints for recruitment text analysis."""

import uuid
import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_optional_current_user
from app.core.rate_limit import check_rate_limit
from app.core.security import generate_guest_token, hash_guest_token
from app.db.session import get_db
from app.models.analyses import Analysis
from app.models.indicators import RiskIndicator
from app.models.guest_sessions import GuestSession
from app.models.saved_analyses import SavedAnalysis
from app.models.users import User
from app.schemas.analyses import (
    AIInsightsData,
    AnalysisCreate,
    AnalysisListResponse,
    AnalysisResponse,
    EvidenceData,
    IndicatorItem,
    JobExtracted,
)
from app.services.analysis import perform_analysis_with_ai, perform_text_analysis
from app.services.extraction import extract_job_fields
from app.services.verification_store import load_for_job

router = APIRouter(prefix="/analyses", tags=["analyses"])


def _to_analysis_response(
    analysis: Analysis,
    guest_session_token: Optional[str] = None,
    is_saved: bool = False,
) -> AnalysisResponse:
    """Helper chuyển đổi ORM Analysis sang AnalysisResponse."""
    ai_insights = None
    if analysis.ai_insights:
        ai_insights = AIInsightsData(**analysis.ai_insights)

    return AnalysisResponse(
        id=analysis.id,
        guest_session_token=guest_session_token,
        risk_label_vi=analysis.risk_label_vi,
        verification_label_vi=analysis.verification_label_vi,
        finding_vi=analysis.finding_vi,
        job=JobExtracted(**analysis.job),
        indicators=[IndicatorItem(**ind) for ind in analysis.indicators],
        evidence=EvidenceData(**analysis.evidence),
        actions_vi=analysis.actions_vi,
        ai_insights=ai_insights,
        engine_version=analysis.engine_version,
        rules_version=analysis.rules_version,
        created_at=analysis.created_at,
        expires_at=analysis.expires_at,
        is_saved=is_saved,
    )


@router.post(
    "",
    response_model=AnalysisResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Phân tích tin tuyển dụng cho khách hoặc người dùng đăng nhập",
)
def create_analysis(
    request: Request,
    response: Response,
    payload: AnalysisCreate,
    x_guest_session_token: Optional[str] = Header(None, alias="X-Guest-Session-Token"),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
) -> AnalysisResponse:
    """Tạo phân tích mới từ văn bản.

    - Nếu đã đăng nhập: gắn user_id, expires_at=None, lưu vĩnh viễn đến khi xóa.
    - Nếu là khách: gắn session_id, expires_at=24h, cấp token nếu chưa có.
    """
    check_rate_limit(request)

    now = datetime.now(timezone.utc)
    issued_token: Optional[str] = None
    session_id: Optional[uuid.UUID] = None
    user_id: Optional[uuid.UUID] = None
    expires_at: Optional[datetime] = None

    if current_user:
        # Người dùng đã đăng nhập: không dùng guest_session
        user_id = current_user.id
        session_id = None
        expires_at = None
    else:
        # Khách vãng lai
        if x_guest_session_token is not None:
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
            raw_token = generate_guest_token()
            token_hash = hash_guest_token(raw_token)
            session_expires = now + timedelta(hours=24)
            session = GuestSession(
                token_hash=token_hash,
                created_at=now,
                expires_at=session_expires,
            )
            db.add(session)
            db.flush()
            issued_token = raw_token

        session_id = session.id
        expires_at = session.expires_at

    rule_settings = {rule.code: rule for rule in db.query(RiskIndicator).all()}
    rule_snapshot = [(code, rule.enabled, rule.weight, rule.explanation_vi) for code, rule in sorted(rule_settings.items())]
    rules_version = "2026.10-" + hashlib.sha256(json.dumps(rule_snapshot, ensure_ascii=False).encode()).hexdigest()[:12]
    # Thực hiện phân tích văn bản (Layer 1 Rule-based và Layer 2 AI tùy chọn)
    job, indicators, risk_label_vi, verification_label_vi, finding_vi, evidence, actions_vi, ai_insights = (
        perform_analysis_with_ai(
            payload.text,
            employer_records=load_for_job(db, extract_job_fields(payload.text)),
            rule_settings=rule_settings,
            is_demo=False,
            use_ai=bool(payload.use_ai),
            ai_consent=bool(payload.ai_consent),
        )
    )

    analysis = Analysis(
        id=uuid.uuid4(),
        session_id=session_id,
        user_id=user_id,
        raw_text=payload.text,
        risk_label_vi=risk_label_vi,
        verification_label_vi=verification_label_vi,
        finding_vi=finding_vi,
        job=job.model_dump(),
        indicators=[ind.model_dump() for ind in indicators],
        evidence=evidence.model_dump(),
        actions_vi=actions_vi,
        ai_insights=ai_insights.model_dump() if ai_insights else None,
        engine_version="1.3.0",
        rules_version=rules_version,
        created_at=now,
        expires_at=expires_at,
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    response.headers["Cache-Control"] = "no-store"
    return _to_analysis_response(analysis, guest_session_token=issued_token, is_saved=False)


@router.get(
    "",
    response_model=AnalysisListResponse,
    status_code=status.HTTP_200_OK,
    summary="Xem lịch sử phân tích của người dùng hiện tại",
)
def list_analyses(
    response: Response,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    is_saved: Optional[bool] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AnalysisListResponse:
    """Lấy danh sách các bài phân tích thuộc sở hữu của người dùng hiện tại."""
    q = db.query(Analysis).filter(Analysis.user_id == current_user.id)

    if is_saved is True:
        saved_subq = (
            db.query(SavedAnalysis.analysis_id)
            .filter(SavedAnalysis.user_id == current_user.id)
            .scalar_subquery()
        )
        q = q.filter(Analysis.id.in_(saved_subq))

    total = q.count()
    analyses = (
        q.order_by(Analysis.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    saved_ids = (
        set(
            row[0]
            for row in db.query(SavedAnalysis.analysis_id)
            .filter(
                SavedAnalysis.user_id == current_user.id,
                SavedAnalysis.analysis_id.in_([a.id for a in analyses]),
            )
            .all()
        )
        if analyses
        else set()
    )

    response.headers["Cache-Control"] = "no-store"
    return AnalysisListResponse(
        items=[_to_analysis_response(a, is_saved=(a.id in saved_ids)) for a in analyses],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{analysis_id}",
    response_model=AnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Đọc lại kết quả phân tích theo phiên khách hoặc tài khoản",
)
def get_analysis(
    analysis_id: uuid.UUID,
    response: Response,
    x_guest_session_token: Optional[str] = Header(None, alias="X-Guest-Session-Token"),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
) -> AnalysisResponse:
    """Đọc lại kết quả phân tích. Phải khớp chủ sở hữu (user_id hoặc session_id)."""
    now = datetime.now(timezone.utc)
    is_saved = False

    if current_user:
        analysis = (
            db.query(Analysis)
            .filter(
                Analysis.id == analysis_id,
                Analysis.user_id == current_user.id,
            )
            .first()
        )
        if not analysis:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")

        is_saved = (
            db.query(SavedAnalysis)
            .filter_by(user_id=current_user.id, analysis_id=analysis_id)
            .first()
            is not None
        )
    elif x_guest_session_token:
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
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")

    response.headers["Cache-Control"] = "no-store"
    return _to_analysis_response(analysis, guest_session_token=None, is_saved=is_saved)


@router.delete(
    "/{analysis_id}",
    status_code=status.HTTP_200_OK,
    summary="Xóa kết quả phân tích của người dùng",
)
def delete_analysis(
    analysis_id: uuid.UUID,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Chủ sở hữu xóa kết quả phân tích khỏi tài khoản."""
    analysis = (
        db.query(Analysis)
        .filter(
            Analysis.id == analysis_id,
            Analysis.user_id == current_user.id,
        )
        .first()
    )
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")

    db.delete(analysis)
    db.commit()

    response.headers["Cache-Control"] = "no-store"
    return {"status": "ok", "message": "Đã xóa kết quả phân tích"}

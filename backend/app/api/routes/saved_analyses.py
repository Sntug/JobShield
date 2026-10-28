"""Saved analyses endpoints: save, unsave, list saved analyses."""

import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.analyses import Analysis
from app.models.saved_analyses import SavedAnalysis
from app.models.users import User
from app.schemas.analyses import AnalysisResponse, EvidenceData, IndicatorItem, JobExtracted
from app.schemas.saved_analyses import SavedAnalysisItemResponse, SavedAnalysisListResponse

router = APIRouter(prefix="/saved-analyses", tags=["saved-analyses"])


def _to_analysis_response(analysis: Analysis) -> AnalysisResponse:
    """Helper chuyển đổi ORM Analysis sang AnalysisResponse."""
    return AnalysisResponse(
        id=analysis.id,
        guest_session_token=None,
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
        is_saved=True,
    )


@router.post(
    "/{analysis_id}",
    status_code=status.HTTP_200_OK,
    summary="Đánh dấu lưu kết quả phân tích",
)
def save_analysis(
    analysis_id: uuid.UUID,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Lưu phân tích của chính người dùng vào danh sách bookmark."""
    analysis = (
        db.query(Analysis)
        .filter(
            Analysis.id == analysis_id,
            Analysis.user_id == current_user.id,
        )
        .first()
    )
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy kết quả phân tích.",
        )

    saved = (
        db.query(SavedAnalysis)
        .filter_by(user_id=current_user.id, analysis_id=analysis_id)
        .first()
    )
    if not saved:
        now = datetime.now(timezone.utc)
        saved = SavedAnalysis(
            user_id=current_user.id,
            analysis_id=analysis_id,
            saved_at=now,
        )
        db.add(saved)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            if not db.query(SavedAnalysis).filter_by(
                user_id=current_user.id, analysis_id=analysis_id,
            ).first():
                raise

    response.headers["Cache-Control"] = "no-store"
    return {
        "status": "ok",
        "message": "Đã lưu kết quả phân tích",
        "analysis_id": str(analysis_id),
    }


@router.delete(
    "/{analysis_id}",
    status_code=status.HTTP_200_OK,
    summary="Bỏ đánh dấu lưu kết quả phân tích",
)
def unsave_analysis(
    analysis_id: uuid.UUID,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Xóa phân tích khỏi danh sách lưu của người dùng."""
    saved = (
        db.query(SavedAnalysis)
        .filter_by(user_id=current_user.id, analysis_id=analysis_id)
        .first()
    )
    if not saved:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bản ghi chưa được lưu hoặc không tồn tại.",
        )

    db.delete(saved)
    db.commit()

    response.headers["Cache-Control"] = "no-store"
    return {"status": "ok", "message": "Đã bỏ lưu kết quả phân tích"}


@router.get(
    "",
    response_model=SavedAnalysisListResponse,
    status_code=status.HTTP_200_OK,
    summary="Lấy danh sách các bài phân tích đã lưu",
)
def list_saved_analyses(
    response: Response,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SavedAnalysisListResponse:
    """Lấy danh sách bài phân tích đã lưu của người dùng hiện tại."""
    q = (
        db.query(SavedAnalysis)
        .filter(SavedAnalysis.user_id == current_user.id)
    )
    total = q.count()
    records = (
        q.order_by(SavedAnalysis.saved_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = []
    for r in records:
        if r.analysis:
            items.append(
                SavedAnalysisItemResponse(
                    analysis_id=r.analysis_id,
                    saved_at=r.saved_at,
                    analysis=_to_analysis_response(r.analysis),
                )
            )

    response.headers["Cache-Control"] = "no-store"
    return SavedAnalysisListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )

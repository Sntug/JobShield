"""API endpoints for batch recruitment analysis."""

from datetime import datetime, timedelta, timezone
from typing import List, Optional
import uuid

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    Header,
    HTTPException,
    Request,
    Response,
    status,
)
from sqlalchemy.orm import Session

from app.api.dependencies import get_optional_current_user
from app.api.routes.analyses import _to_analysis_response
from app.core.rate_limit import check_rate_limit, get_client_ip
from app.core.security import generate_guest_token, hash_guest_token
from app.db.session import get_db
from app.models.analyses import Analysis
from app.models.batch_analyses import BatchAnalysis
from app.models.guest_sessions import GuestSession
from app.models.users import User
from app.schemas.batch_analyses import (
    BatchAnalysisCreate,
    BatchAnalysisCreatedResponse,
    BatchAnalysisResponse,
    BatchItemResponse,
)
from app.services.batch_analysis import (
    cancel_batch,
    create_batch,
    fail_stale_batch,
    get_batch_by_id,
    process_batch_in_background,
)

router = APIRouter(prefix="/batches/analyses", tags=["batch-analyses"])


def _to_batch_response(
    batch: BatchAnalysis,
    db: Session,
) -> BatchAnalysisResponse:
    """Helper chuyển đổi ORM BatchAnalysis sang BatchAnalysisResponse."""
    items_resp: List[BatchItemResponse] = []
    sorted_items = sorted(batch.items, key=lambda x: x.item_order)

    for item in sorted_items:
        analysis_resp = None
        if item.analysis_id is not None:
            analysis = db.query(Analysis).filter(Analysis.id == item.analysis_id).first()
            if analysis:
                analysis_resp = _to_analysis_response(analysis)

        items_resp.append(
            BatchItemResponse(
                id=item.id,
                item_order=item.item_order,
                input_type=item.input_type,
                input_value=item.input_value,
                status=item.status,
                analysis_id=item.analysis_id,
                analysis=analysis_resp,
                error_message=item.error_message,
                error_code=item.error_code,
                created_at=item.created_at,
                updated_at=item.updated_at,
            )
        )

    return BatchAnalysisResponse(
        id=batch.id,
        status=batch.status,
        total_items=batch.total_items,
        processed_items=batch.processed_items,
        items=items_resp,
        created_at=batch.created_at,
        updated_at=batch.updated_at,
        expires_at=batch.expires_at,
    )


def _authorize_batch_access(
    batch_id: uuid.UUID,
    current_user: Optional[User],
    x_guest_session_token: Optional[str],
    db: Session,
) -> BatchAnalysis:
    """Kiểm tra quyền truy cập đợt phân tích hàng loạt."""
    batch = get_batch_by_id(db, batch_id)
    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy lượt phân tích",
        )

    now = datetime.now(timezone.utc)
    if batch.user_id is not None:
        if not current_user or current_user.id != batch.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Không có quyền truy cập lượt phân tích này",
            )
    elif batch.session_id is not None:
        if not x_guest_session_token or not x_guest_session_token.strip():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Không có quyền truy cập lượt phân tích này",
            )
        token_hash = hash_guest_token(x_guest_session_token)
        session = (
            db.query(GuestSession)
            .filter(GuestSession.token_hash == token_hash, GuestSession.expires_at > now)
            .first()
        )
        if not session or session.id != batch.session_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Không có quyền truy cập lượt phân tích này",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Không có quyền truy cập lượt phân tích này",
        )

    return batch


@router.post(
    "",
    response_model=BatchAnalysisCreatedResponse,
    response_model_exclude_unset=True,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo đợt phân tích tuyển dụng hàng loạt",
)
def create_batch_analysis(
    request: Request,
    response: Response,
    payload: BatchAnalysisCreate,
    background_tasks: BackgroundTasks,
    x_guest_session_token: Optional[str] = Header(None, alias="X-Guest-Session-Token"),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
) -> BatchAnalysisCreatedResponse:
    """Tạo đợt phân tích hàng loạt mới và đưa vào hàng đợi xử lý nền."""
    identity = f"user:{current_user.id}" if current_user else f"ip:{get_client_ip(request)}"
    check_rate_limit(request, bucket="batch-analyses", identity=identity, max_requests=2)

    now = datetime.now(timezone.utc)
    guest_session_token: Optional[str] = None
    session_id: Optional[uuid.UUID] = None
    user_id: Optional[uuid.UUID] = None
    expires_at: Optional[datetime] = None

    if current_user:
        user_id = current_user.id
        session_id = None
        expires_at = None
    else:
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
                .with_for_update()
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
            guest_session_token = raw_token
            response.headers["X-Guest-Session-Token"] = guest_session_token

        session_id = session.id
        expires_at = session.expires_at

    batch = create_batch(
        db=db,
        payload=payload,
        session_id=session_id,
        user_id=user_id,
        expires_at=expires_at,
    )

    background_tasks.add_task(
        process_batch_in_background,
        batch.id,
        payload.use_ai,
        payload.ai_consent,
    )

    response.headers["Cache-Control"] = "no-store"
    batch_response = _to_batch_response(batch, db)
    response_body = BatchAnalysisCreatedResponse(
        **batch_response.model_dump(),
        **({"guest_session_token": guest_session_token} if guest_session_token else {}),
    )
    db.rollback()
    return response_body


@router.get(
    "/{batch_id}",
    response_model=BatchAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Lấy chi tiết và tiến độ đợt phân tích hàng loạt",
)
def get_batch(
    batch_id: uuid.UUID,
    response: Response,
    x_guest_session_token: Optional[str] = Header(None, alias="X-Guest-Session-Token"),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
) -> BatchAnalysisResponse:
    """Lấy thông tin và trạng thái đợt phân tích hàng loạt."""
    _authorize_batch_access(batch_id, current_user, x_guest_session_token, db)
    fail_stale_batch(db, batch_id)
    batch = get_batch_by_id(db, batch_id)
    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy lượt phân tích",
        )
    response.headers["Cache-Control"] = "no-store"
    return _to_batch_response(batch, db)


@router.post(
    "/{batch_id}/cancel",
    response_model=BatchAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Hủy đợt phân tích hàng loạt",
)
def cancel_batch_endpoint(
    batch_id: uuid.UUID,
    response: Response,
    x_guest_session_token: Optional[str] = Header(None, alias="X-Guest-Session-Token"),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
) -> BatchAnalysisResponse:
    """Hủy đợt phân tích hàng loạt và dừng các mục đang chờ."""
    _authorize_batch_access(batch_id, current_user, x_guest_session_token, db)
    updated_batch = cancel_batch(db, batch_id)
    if not updated_batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy lượt phân tích",
        )
    updated_batch = get_batch_by_id(db, batch_id)
    if not updated_batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy lượt phân tích",
        )
    response.headers["Cache-Control"] = "no-store"
    return _to_batch_response(updated_batch, db)

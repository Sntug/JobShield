"""Batch recruitment analysis service."""

from datetime import datetime, timedelta, timezone
import hashlib
import json
import logging
import math
from functools import lru_cache
from types import SimpleNamespace
from typing import Optional
import uuid

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.session import get_session_local
from app.models.analyses import Analysis
from app.models.batch_analyses import BatchAnalysis, BatchAnalysisItem
from app.models.guest_sessions import GuestSession
from app.models.indicators import RiskIndicator
from app.schemas.batch_analyses import BatchAnalysisCreate
from app.services.analysis import perform_analysis_with_ai, perform_text_analysis
from app.services.extraction import extract_job_fields
from app.services.url_extraction import extract_text_from_url
from app.services.verification_store import load_for_job

logger = logging.getLogger("uvicorn.error")
WORKER_INTERRUPTED = "Tác vụ bị gián đoạn trước khi hoàn tất. Vui lòng gửi lại lượt phân tích."
WORKER_ERROR = "Tác vụ phân tích bị gián đoạn do lỗi nội bộ. Vui lòng gửi lại lượt phân tích."


@lru_cache(maxsize=1)
def _worker_stale_after() -> timedelta:
    try:
        ai_timeout = float(Settings().ai_timeout_seconds)
    except Exception as exc:
        ai_timeout = 10.0
    if not math.isfinite(ai_timeout):
        ai_timeout = 10.0
    return timedelta(seconds=max(300.0, ai_timeout + 60.0))


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _locked_batch(db: Session, batch_id: uuid.UUID) -> Optional[BatchAnalysis]:
    return (
        db.query(BatchAnalysis)
        .filter(BatchAnalysis.id == batch_id)
        .with_for_update()
        .populate_existing()
        .first()
    )


def _lock_batch_owner_then_batch(db: Session, batch_id: uuid.UUID) -> Optional[BatchAnalysis]:
    # Claiming a guest session uses the same GuestSession -> BatchAnalysis lock order.
    batch = db.query(BatchAnalysis).filter(BatchAnalysis.id == batch_id).first()
    if not batch:
        return None
    guest_id = batch.session_id
    guest = None
    if guest_id is not None:
        guest = (
            db.query(GuestSession)
            .filter(GuestSession.id == guest_id)
            .with_for_update()
            .first()
        )
    batch = _locked_batch(db, batch_id)
    if batch and batch.session_id is not None and guest is None:
        return None
    return batch


def _mark_unfinished_failed(db: Session, batch: BatchAnalysis, message: str) -> int:
    unfinished = (
        db.query(BatchAnalysisItem)
        .filter(
            BatchAnalysisItem.batch_id == batch.id,
            BatchAnalysisItem.status.in_(("pending", "processing")),
        )
        .all()
    )
    now = datetime.now(timezone.utc)
    for item in unfinished:
        item.status = "error"
        item.error_message = message
        item.error_code = "WORKER_INTERRUPTED"
        item.updated_at = now
    batch.processed_items += len(unfinished)
    batch.updated_at = now
    return len(unfinished)


def create_batch(
    db: Session,
    payload: BatchAnalysisCreate,
    session_id: Optional[uuid.UUID] = None,
    user_id: Optional[uuid.UUID] = None,
    expires_at: Optional[datetime] = None,
) -> BatchAnalysis:
    """Khởi tạo đợt phân tích hàng loạt và các mục con ở trạng thái pending."""
    now = datetime.now(timezone.utc)
    batch = BatchAnalysis(
        id=uuid.uuid4(),
        session_id=session_id,
        user_id=user_id,
        status="pending",
        total_items=len(payload.items),
        processed_items=0,
        created_at=now,
        updated_at=now,
        expires_at=expires_at,
    )

    for i, item in enumerate(payload.items):
        batch.items.append(
            BatchAnalysisItem(
                id=uuid.uuid4(),
                batch_id=batch.id,
                item_order=i,
                input_type=item.type,
                input_value=item.value,
                status="pending",
                created_at=now,
                updated_at=now,
            )
        )

    db.add(batch)
    db.commit()
    db.refresh(batch)
    return batch


def get_batch_by_id(db: Session, batch_id: uuid.UUID) -> Optional[BatchAnalysis]:
    """Tìm đợt phân tích theo ID."""
    return db.query(BatchAnalysis).filter(BatchAnalysis.id == batch_id).first()


def cancel_batch(db: Session, batch_id: uuid.UUID) -> Optional[BatchAnalysis]:
    """Hủy lượt đang chạy, giữ nguyên mục đã bắt đầu để worker hoàn tất."""
    batch = _locked_batch(db, batch_id)
    if not batch:
        return None
    if batch.status in ("completed", "failed", "cancelled"):
        db.rollback()
        return batch

    now = datetime.now(timezone.utc)
    batch.status = "cancelled"
    batch.updated_at = now
    for item in batch.items:
        if item.status == "pending":
            item.status = "cancelled"
            item.updated_at = now

    db.commit()
    db.refresh(batch)
    return batch


def fail_stale_batch(db: Session, batch_id: uuid.UUID) -> bool:
    """Settle work abandoned beyond the longest configured URL/AI timeout."""
    now = datetime.now(timezone.utc)
    cutoff = now - _worker_stale_after()
    state = (
        db.query(BatchAnalysis.status, BatchAnalysis.updated_at)
        .filter(BatchAnalysis.id == batch_id)
        .first()
    )
    if not state:
        return False
    status, updated_at = state
    if status in ("pending", "processing"):
        if _utc(updated_at) > cutoff:
            return False
    elif status == "cancelled":
        if not db.query(BatchAnalysisItem.id).filter(
            BatchAnalysisItem.batch_id == batch_id,
            BatchAnalysisItem.status == "processing",
            BatchAnalysisItem.updated_at <= cutoff,
        ).first():
            return False
    else:
        return False

    batch = _locked_batch(db, batch_id)
    if not batch:
        db.rollback()
        return False

    if batch.status == "cancelled":
        stale_items = (
            db.query(BatchAnalysisItem)
            .filter(
                BatchAnalysisItem.batch_id == batch.id,
                BatchAnalysisItem.status == "processing",
            )
            .all()
        )
        stale_items = [item for item in stale_items if _utc(item.updated_at) <= cutoff]
        for item in stale_items:
            item.status = "error"
            item.error_message = WORKER_INTERRUPTED
            item.error_code = "WORKER_INTERRUPTED"
            item.updated_at = now
        if stale_items:
            batch.processed_items += len(stale_items)
            batch.updated_at = now
            db.commit()
            return True
        db.rollback()
        return False

    if batch.status not in ("pending", "processing") or _utc(batch.updated_at) > cutoff:
        db.rollback()
        return False

    _mark_unfinished_failed(db, batch, WORKER_INTERRUPTED)
    batch.status = "failed"
    db.commit()
    return True


def _claim_item(db: Session, batch_id: uuid.UUID, item_id: uuid.UUID) -> Optional[tuple[str, str]]:
    batch = _locked_batch(db, batch_id)
    if not batch or batch.status != "processing":
        db.rollback()
        return None
    item = (
        db.query(BatchAnalysisItem)
        .filter(BatchAnalysisItem.id == item_id, BatchAnalysisItem.batch_id == batch_id)
        .with_for_update()
        .populate_existing()
        .first()
    )
    if not item or item.status != "pending":
        db.rollback()
        return None

    input_type, input_value = item.input_type, item.input_value
    now = datetime.now(timezone.utc)
    item.status = "processing"
    item.updated_at = now
    batch.updated_at = now
    db.commit()
    return input_type, input_value


def _finish_item(
    db: Session,
    batch_id: uuid.UUID,
    item_id: uuid.UUID,
    *,
    analysis: Optional[Analysis] = None,
    error_message: Optional[str] = None,
    error_code: Optional[str] = None,
) -> bool:
    batch = _lock_batch_owner_then_batch(db, batch_id)
    if not batch or batch.status not in ("processing", "cancelled"):
        db.rollback()
        return False
    item = (
        db.query(BatchAnalysisItem)
        .filter(BatchAnalysisItem.id == item_id, BatchAnalysisItem.batch_id == batch_id)
        .with_for_update()
        .populate_existing()
        .first()
    )
    if not item or item.status != "processing":
        db.rollback()
        return False

    now = datetime.now(timezone.utc)
    if analysis is not None:
        analysis.session_id = batch.session_id
        analysis.user_id = batch.user_id
        analysis.expires_at = batch.expires_at
        db.add(analysis)
        item.analysis = analysis
        item.status = "success"
    else:
        item.status = "error"
        item.error_message = error_message
        item.error_code = error_code
    item.updated_at = now
    batch.processed_items += 1
    batch.updated_at = now
    db.commit()
    return True


def _finalize_batch(db: Session, batch_id: uuid.UUID) -> None:
    batch = _locked_batch(db, batch_id)
    if not batch or batch.status != "processing":
        db.rollback()
        return

    statuses = [
        status
        for (status,) in db.query(BatchAnalysisItem.status)
        .filter(BatchAnalysisItem.batch_id == batch_id)
        .all()
    ]
    if any(status in ("pending", "processing") for status in statuses):
        _mark_unfinished_failed(db, batch, WORKER_INTERRUPTED)
        batch.status = "failed"
    elif any(status == "error" for status in statuses) and not any(
        status == "success" for status in statuses
    ):
        batch.status = "failed"
    else:
        batch.status = "completed"
    batch.updated_at = datetime.now(timezone.utc)
    db.commit()


def process_batch_in_background(
    batch_id: uuid.UUID,
    use_ai: bool = False,
    ai_consent: bool = False,
    db: Optional[Session] = None,
) -> None:
    """Xử lý tuần tự các mục trong đợt phân tích hàng loạt trong tác vụ nền."""
    should_close = False
    if db is None:
        db = get_session_local()()
        should_close = True

    try:
        batch = _locked_batch(db, batch_id)
        if not batch or batch.status != "pending":
            db.rollback()
            return
        batch.status = "processing"
        batch.updated_at = datetime.now(timezone.utc)
        db.commit()

        rules = db.query(RiskIndicator).all()
        rule_settings = {
            rule.code: SimpleNamespace(
                enabled=rule.enabled,
                weight=rule.weight,
                explanation_vi=rule.explanation_vi,
            )
            for rule in rules
        }
        rule_snapshot = [
            (code, rule.enabled, rule.weight, rule.explanation_vi)
            for code, rule in sorted(rule_settings.items())
        ]
        rules_version = (
            "2026.10-" + hashlib.sha256(json.dumps(rule_snapshot, ensure_ascii=False).encode()).hexdigest()[:12]
            if rule_snapshot
            else "2026.10"
        )
        item_ids = [
            item_id
            for (item_id,) in db.query(BatchAnalysisItem.id)
            .filter(BatchAnalysisItem.batch_id == batch_id)
            .order_by(BatchAnalysisItem.item_order)
            .all()
        ]
        db.commit()

        for item_id in item_ids:
            claimed = _claim_item(db, batch_id, item_id)
            if claimed is None:
                break
            input_type, input_value = claimed
            if input_type == "url":
                try:
                    result = extract_text_from_url(input_value)
                except Exception as exc:
                    logger.warning("Batch item %s URL extraction failed (%s)", item_id, type(exc).__name__)
                    _finish_item(
                        db,
                        batch_id,
                        item_id,
                        error_message="Không thể trích xuất nội dung từ liên kết này.",
                        error_code="EXTRACTION_FAILED",
                    )
                    continue
                if not result.success or not result.text:
                    _finish_item(
                        db,
                        batch_id,
                        item_id,
                        error_message=result.failure_vi or "Không thể trích xuất nội dung từ liên kết này.",
                        error_code="EXTRACTION_FAILED",
                    )
                    continue
                text_to_analyze = result.text
            else:
                text_to_analyze = input_value

            try:
                employer_records = load_for_job(db, extract_job_fields(text_to_analyze))
                # Release the read transaction before rule/AI work and any result commit.
                db.commit()
                if use_ai and ai_consent:
                    (
                        job,
                        indicators,
                        risk_label_vi,
                        verification_label_vi,
                        finding_vi,
                        evidence,
                        actions_vi,
                        ai_insights,
                    ) = perform_analysis_with_ai(
                        text=text_to_analyze,
                        employer_records=employer_records,
                        rule_settings=rule_settings,
                        is_demo=False,
                        use_ai=True,
                        ai_consent=True,
                    )
                else:
                    (
                        job,
                        indicators,
                        risk_label_vi,
                        verification_label_vi,
                        finding_vi,
                        evidence,
                        actions_vi,
                    ) = perform_text_analysis(
                        text=text_to_analyze,
                        employer_records=employer_records,
                        rule_settings=rule_settings,
                        is_demo=False,
                    )
                    ai_insights = None

                analysis_now = datetime.now(timezone.utc)
                analysis = Analysis(
                    id=uuid.uuid4(),
                    raw_text=text_to_analyze,
                    risk_label_vi=risk_label_vi,
                    verification_label_vi=verification_label_vi,
                    finding_vi=finding_vi,
                    job=job.model_dump(),
                    indicators=[indicator.model_dump() for indicator in indicators],
                    evidence=evidence.model_dump(),
                    actions_vi=actions_vi,
                    ai_insights=ai_insights.model_dump() if ai_insights else None,
                    engine_version="0.1.0",
                    rules_version=rules_version,
                    created_at=analysis_now,
                )
                _finish_item(db, batch_id, item_id, analysis=analysis)
            except Exception as exc:
                logger.warning("Batch item %s analysis failed (%s)", item_id, type(exc).__name__)
                db.rollback()
                _finish_item(
                    db,
                    batch_id,
                    item_id,
                    error_message="Không thể phân tích nội dung này do lỗi nội bộ.",
                    error_code="ANALYSIS_FAILED",
                )

        _finalize_batch(db, batch_id)
    except Exception as exc:
        db.rollback()
        try:
            batch = _locked_batch(db, batch_id)
            if batch and batch.status in ("pending", "processing", "cancelled"):
                count = _mark_unfinished_failed(db, batch, WORKER_ERROR)
                if batch.status != "cancelled":
                    batch.status = "failed"
                if count or batch.status == "failed":
                    db.commit()
                else:
                    db.rollback()
        except Exception:
            db.rollback()
            logger.error("Could not persist batch worker failure for %s", batch_id)
        logger.error("Batch worker failed for %s (%s)", batch_id, type(exc).__name__)
    finally:
        if should_close:
            db.close()

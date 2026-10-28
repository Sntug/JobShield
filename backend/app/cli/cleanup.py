"""Cleanup command for purging expired guest sessions and analyses.

Chạy độc lập ngoài process web (cron job, worker, hoặc scheduled GitHub Action / Supabase task).
"""

import logging
import sys
from datetime import datetime, timezone
from typing import Optional, Tuple
from sqlalchemy.orm import Session

from app.db.session import get_session_local
from app.models.analyses import Analysis
from app.models.guest_sessions import GuestSession

logger = logging.getLogger("cleanup")


def purge_expired_sessions(
    db: Session,
    reference_time: Optional[datetime] = None,
) -> Tuple[int, int]:
    """Xóa các guest_sessions đã quá hạn (expires_at <= reference_time) và các analyses liên quan.

    Tuyệt đối không xóa các bài phân tích đã được user nhận quyền (user_id IS NOT NULL).
    Thực hiện xóa analyses trước rồi đến guest_sessions trong cùng một transaction để bảo đảm
    tương thích hoàn toàn trên cả SQLite (test) và PostgreSQL (staging/production).
    Trả về: (số session đã xóa, số analysis đã xóa).
    """
    now = reference_time or datetime.now(timezone.utc)

    # 1. Xóa các bản ghi analyses thuộc các phiên khách đã hết hạn (chỉ xóa khi chưa được chuyển quyền)
    expired_session_ids = (
        db.query(GuestSession.id)
        .filter(GuestSession.expires_at <= now)
        .scalar_subquery()
    )
    deleted_analyses = (
        db.query(Analysis)
        .filter(
            Analysis.session_id.isnot(None),
            Analysis.session_id.in_(expired_session_ids),
            Analysis.user_id.is_(None),
        )
        .delete(synchronize_session=False)
    )

    # 2. Xóa các guest_sessions đã hết hạn
    deleted_sessions = (
        db.query(GuestSession)
        .filter(GuestSession.expires_at <= now)
        .delete(synchronize_session=False)
    )
    db.commit()

    return deleted_sessions, deleted_analyses


def main() -> int:
    """Entry point cho CLI lệnh: python -m app.cli.cleanup."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    logger.info("Bắt đầu tiến trình dọn dẹp các phiên khách đã hết hạn...")

    session_factory = get_session_local()
    db = session_factory()
    try:
        deleted_sessions, deleted_analyses = purge_expired_sessions(db)
        logger.info(
            "Hoàn tất dọn dẹp: Đã xóa %d phiên khách và %d kết quả phân tích hết hạn.",
            deleted_sessions,
            deleted_analyses,
        )
        return 0
    except Exception as exc:
        logger.error("Lỗi trong quá trình dọn dẹp: %s", exc)
        db.rollback()
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())

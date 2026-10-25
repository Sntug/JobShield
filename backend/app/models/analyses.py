"""Analysis model for recruitment job post evaluations."""

import uuid
from datetime import datetime
from typing import Any, Dict, List
from sqlalchemy import String, Text, DateTime, JSON, ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Analysis(Base):
    """Kết quả phân tích tin tuyển dụng lưu trữ dưới dạng immutable snapshot."""

    __tablename__ = "analyses"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("guest_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)

    risk_label_vi: Mapped[str] = mapped_column(String(50), nullable=False)
    verification_label_vi: Mapped[str] = mapped_column(String(50), nullable=False)
    finding_vi: Mapped[str] = mapped_column(Text, nullable=False)

    # 11 trường trích xuất job
    job: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)

    # Danh sách indicators có matched_quote nguyên văn
    indicators: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, nullable=False)

    # Dữ liệu đối chiếu và giới hạn
    evidence: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)

    # Hành động khuyến nghị
    actions_vi: Mapped[List[str]] = mapped_column(JSON, nullable=False)

    # Snapshot metadata
    engine_version: Mapped[str] = mapped_column(String(20), nullable=False, default="0.1.0")
    rules_version: Mapped[str] = mapped_column(String(20), nullable=False, default="2026.10")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )

    session = relationship("GuestSession", back_populates="analyses")

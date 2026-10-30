"""Analysis model for recruitment job post evaluations."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, JSON, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Analysis(Base):
    """Kết quả phân tích tin tuyển dụng lưu trữ dưới dạng immutable snapshot.

    Mỗi bản ghi thuộc về đúng một chủ sở hữu: hoặc là khách (session_id), hoặc là user (user_id).
    Khi thuộc user: expires_at là NULL (lưu vĩnh viễn đến khi user xóa).
    Khi thuộc guest: expires_at có giá trị (hết hạn sau 24h).
    """

    __tablename__ = "analyses"
    __table_args__ = (
        CheckConstraint(
            "(session_id IS NOT NULL AND user_id IS NULL) OR (session_id IS NULL AND user_id IS NOT NULL)",
            name="ck_analysis_owner",
        ),
        CheckConstraint(
            "(user_id IS NOT NULL AND expires_at IS NULL) OR (session_id IS NOT NULL AND expires_at IS NOT NULL)",
            name="ck_analysis_expiry",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("guest_sessions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
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

    # Lớp phân tích ngữ nghĩa AI tùy chọn (nullable khi không dùng AI hoặc fallback)
    ai_insights: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Snapshot metadata
    engine_version: Mapped[str] = mapped_column(String(20), nullable=False, default="0.1.0")
    rules_version: Mapped[str] = mapped_column(String(20), nullable=False, default="2026.10")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), index=True, nullable=True
    )

    session = relationship("GuestSession", back_populates="analyses")
    user = relationship("User", back_populates="analyses")
    saved_by_users = relationship(
        "SavedAnalysis",
        back_populates="analysis",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

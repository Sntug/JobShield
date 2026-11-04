"""Batch recruitment analysis models."""

import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, backref, mapped_column, relationship

from app.db.base import Base


class BatchAnalysis(Base):
    """Đợt phân tích hàng loạt nhiều tin tuyển dụng.

    Mỗi bản ghi thuộc về đúng một chủ sở hữu: khách (session_id) hoặc user (user_id).
    Khi thuộc user: expires_at là NULL (lưu vĩnh viễn đến khi user xóa).
    Khi thuộc guest: expires_at có giá trị (hết hạn sau 24h).
    """

    __tablename__ = "batch_analyses"
    __table_args__ = (
        CheckConstraint(
            "(session_id IS NOT NULL AND user_id IS NULL) OR (session_id IS NULL AND user_id IS NOT NULL)",
            name="ck_batch_owner",
        ),
        CheckConstraint(
            "(user_id IS NOT NULL AND expires_at IS NULL) OR (session_id IS NOT NULL AND expires_at IS NOT NULL)",
            name="ck_batch_expiry",
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
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # pending, processing, completed, failed, cancelled
    total_items: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    processed_items: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), index=True, nullable=True
    )

    session = relationship(
        "GuestSession", backref=backref("batch_analyses", passive_deletes=True)
    )
    user = relationship("User", backref=backref("batch_analyses", passive_deletes=True))
    items = relationship(
        "BatchAnalysisItem",
        back_populates="batch",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="BatchAnalysisItem.item_order",
    )


class BatchAnalysisItem(Base):
    """Mục phân tích đơn lẻ thuộc một đợt phân tích hàng loạt."""

    __tablename__ = "batch_analysis_items"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    batch_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("batch_analyses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    item_order: Mapped[int] = mapped_column(Integer, nullable=False)
    input_type: Mapped[str] = mapped_column(
        String(10), nullable=False
    )  # 'url' | 'text'
    input_value: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # pending, processing, success, error, cancelled
    analysis_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("analyses.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    batch = relationship("BatchAnalysis", back_populates="items")
    analysis = relationship("Analysis")

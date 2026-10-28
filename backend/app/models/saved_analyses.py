"""Saved analysis bookmark model for authenticated users."""

import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class SavedAnalysis(Base):
    """Bảng đánh dấu tin tuyển dụng đã lưu của người dùng."""

    __tablename__ = "saved_analyses"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("analyses.id", ondelete="CASCADE"),
        primary_key=True,
    )
    saved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    user = relationship("User", back_populates="saved_analyses")
    analysis = relationship("Analysis", back_populates="saved_by_users")

"""Guest session model for anonymous text analysis."""

import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class GuestSession(Base):
    """Phiên làm việc tạm thời cho khách chưa đăng nhập."""

    __tablename__ = "guest_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    token_hash: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )

    analyses = relationship(
        "Analysis",
        back_populates="session",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

"""Models for community reports, moderation actions, and public warnings."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Report(Base):
    """Báo cáo tuyển dụng đáng ngờ do người dùng đăng nhập gửi."""

    __tablename__ = "recruitment_reports"
    __table_args__ = (
        CheckConstraint("length(trim(reason)) > 0", name="ck_report_reason"),
        CheckConstraint("length(trim(description)) > 0", name="ck_report_description"),
        CheckConstraint(
            "status IN ('pending', 'under_review', 'verified', 'rejected')",
            name="ck_report_status",
        ),
        CheckConstraint("version >= 1", name="ck_report_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    analysis_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("analyses.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reporter_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reason: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(30), default="pending", server_default="pending", nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(
        Integer, default=1, server_default="1", nullable=False
    )
    is_demo: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        server_default=func.now(),
        nullable=False,
    )
    private_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    anonymized_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    reporter = relationship("User", foreign_keys=[reporter_id], back_populates="reports")
    analysis = relationship("Analysis")
    evidences = relationship(
        "ReportEvidence",
        back_populates="report",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    moderation_actions = relationship(
        "ModerationAction",
        back_populates="report",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="desc(ModerationAction.created_at)",
    )
    public_warnings = relationship("PublicWarning", back_populates="report")


class ReportEvidence(Base):
    """Bằng chứng đính kèm trong báo cáo (văn bản, URL, hình ảnh)."""

    __tablename__ = "report_evidence"
    __table_args__ = (
        CheckConstraint(
            "evidence_type IN ('text', 'url', 'image')",
            name="ck_evidence_type",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    report_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("recruitment_reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    evidence_type: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    storage_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    file_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    mime_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_demo: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
        nullable=False,
    )

    report = relationship("Report", back_populates="evidences")


class ModerationAction(Base):
    """Nhật ký hành động kiểm duyệt báo cáo của quản trị viên."""

    __tablename__ = "moderation_actions"
    __table_args__ = (
        CheckConstraint(
            "action_type IN ('review', 'request_evidence', 'verify', 'reject')",
            name="ck_moderation_action_type",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    report_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("recruitment_reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    moderator_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    action_type: Mapped[str] = mapped_column(String(30), nullable=False)
    from_status: Mapped[str] = mapped_column(String(30), nullable=False)
    to_status: Mapped[str] = mapped_column(String(30), nullable=False)
    report_version_after: Mapped[int] = mapped_column(Integer, nullable=False)
    reviewed_evidence_ids: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    decision_summary: Mapped[str] = mapped_column(Text, nullable=False)
    private_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
        nullable=False,
    )

    report = relationship("Report", back_populates="moderation_actions")
    moderator = relationship("User")


class PublicWarning(Base):
    """Bản cảnh báo cộng đồng được quản trị viên xuất bản có kiểm chứng."""

    __tablename__ = "public_warnings"
    __table_args__ = (
        CheckConstraint(
            "status IN ('published', 'superseded', 'withdrawn')",
            name="ck_warning_status",
        ),
        CheckConstraint("revision >= 1", name="ck_warning_revision"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    report_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("recruitment_reports.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    decision_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("moderation_actions.id", ondelete="SET NULL"),
        nullable=True,
    )
    previous_warning_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("public_warnings.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
    )
    revision: Mapped[int] = mapped_column(
        Integer, default=1, server_default="1", nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="published",
        server_default="published",
        nullable=False,
        index=True,
    )
    title_vi: Mapped[str] = mapped_column(String(255), nullable=False)
    public_summary_vi: Mapped[str] = mapped_column(Text, nullable=False)
    public_sources_snapshot: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSON, default=list, nullable=False
    )
    is_demo: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
        nullable=False,
    )
    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    withdrawn_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    withdrawal_actor_type: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True
    )
    withdrawn_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    withdrawal_reason_vi: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    report = relationship("Report", back_populates="public_warnings")
    decision = relationship("ModerationAction")
    creator = relationship("User", foreign_keys=[created_by])
    withdrawer = relationship("User", foreign_keys=[withdrawn_by])
    previous_warning = relationship("PublicWarning", remote_side=[id])

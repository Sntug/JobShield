"""Curated identity, provenance and field assertions; no public lookup payloads."""

from datetime import datetime, timezone
import uuid

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Index, Integer, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utc_now():
    return datetime.now(timezone.utc)


class VerifiedEmployer(Base):
    __tablename__ = "verified_employers"
    __table_args__ = (
        CheckConstraint("length(trim(legal_name)) > 0", name="ck_employer_name"),
        CheckConstraint("tax_id IS NULL OR length(tax_id) IN (10, 13)", name="ck_employer_tax_length"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    legal_name: Mapped[str] = mapped_column(String(255), nullable=False)
    tax_id: Mapped[str | None] = mapped_column(String(13), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, server_default=func.now(), nullable=False)


class EmployerSource(Base):
    __tablename__ = "verification_sources"
    __table_args__ = (
        UniqueConstraint("id", "employer_id", name="uq_source_id_employer"),
        CheckConstraint("source_revision >= 1", name="ck_source_revision"),
        CheckConstraint("valid_until IS NULL OR valid_until > verified_at", name="ck_source_lifetime"),
        Index("ix_verification_sources_employer_id", "employer_id"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    employer_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("verified_employers.id", ondelete="CASCADE"), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    label_vi: Mapped[str] = mapped_column(String(255), nullable=False)
    evidence_excerpt_vi: Mapped[str] = mapped_column(Text, nullable=False)
    reviewed_by: Mapped[str] = mapped_column(String(255), nullable=False)
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)


class EmployerClaim(Base):
    __tablename__ = "employer_claims"
    __table_args__ = (
        ForeignKeyConstraint(["source_id", "employer_id"], ["verification_sources.id", "verification_sources.employer_id"], ondelete="CASCADE", name="fk_claim_source_employer"),
        UniqueConstraint("source_id", "field", "value_key", "assertion", name="uq_source_claim"),
        CheckConstraint("field IN ('company_name','tax_id','contact_email','recruitment_website','social_channel_url','bank_account','domain')", name="ck_claim_field"),
        CheckConstraint("assertion IN ('supports','refutes')", name="ck_claim_assertion"),
        CheckConstraint("length(value_key) = 64", name="ck_claim_key_length"),
        Index("ix_employer_claims_lookup", "field", "value_key"),
        Index("ix_employer_claims_source_employer", "source_id", "employer_id"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    employer_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("verified_employers.id", ondelete="CASCADE"), nullable=False)
    source_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    field: Mapped[str] = mapped_column(String(30), nullable=False)
    value_key: Mapped[str] = mapped_column(String(64), nullable=False)
    assertion: Mapped[str] = mapped_column(String(10), nullable=False, default="supports", server_default="supports")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)

"""Curated employer identities, provenance and field assertions.

Revision ID: 71b91d2c6a40
Revises: f0c67067b2b0
"""
from alembic import op
import sqlalchemy as sa

revision = "71b91d2c6a40"
down_revision = "f0c67067b2b0"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "verified_employers",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("legal_name", sa.String(255), nullable=False),
        sa.Column("tax_id", sa.String(13), unique=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("length(trim(legal_name)) > 0", name="ck_employer_name"),
        sa.CheckConstraint("tax_id IS NULL OR length(tax_id) IN (10, 13)", name="ck_employer_tax_length"),
    )
    op.create_table(
        "verification_sources",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("employer_id", sa.Uuid(), sa.ForeignKey("verified_employers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("label_vi", sa.String(255), nullable=False),
        sa.Column("evidence_excerpt_vi", sa.Text(), nullable=False),
        sa.Column("reviewed_by", sa.String(255), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True)),
        sa.Column("source_revision", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.UniqueConstraint("id", "employer_id", name="uq_source_id_employer"),
        sa.CheckConstraint("source_revision >= 1", name="ck_source_revision"),
        sa.CheckConstraint("valid_until IS NULL OR valid_until > verified_at", name="ck_source_lifetime"),
    )
    op.create_index("ix_verification_sources_employer_id", "verification_sources", ["employer_id"])
    op.create_table(
        "employer_claims",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("employer_id", sa.Uuid(), sa.ForeignKey("verified_employers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("field", sa.String(30), nullable=False),
        sa.Column("value_key", sa.String(64), nullable=False),
        sa.Column("assertion", sa.String(10), nullable=False, server_default="supports"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["source_id", "employer_id"], ["verification_sources.id", "verification_sources.employer_id"], ondelete="CASCADE", name="fk_claim_source_employer"),
        sa.UniqueConstraint("source_id", "field", "value_key", "assertion", name="uq_source_claim"),
        sa.CheckConstraint("field IN ('company_name','tax_id','contact_email','recruitment_website','social_channel_url','bank_account','domain')", name="ck_claim_field"),
        sa.CheckConstraint("assertion IN ('supports','refutes')", name="ck_claim_assertion"),
        sa.CheckConstraint("length(value_key) = 64", name="ck_claim_key_length"),
    )
    op.create_index("ix_employer_claims_lookup", "employer_claims", ["field", "value_key"])
    op.create_index("ix_employer_claims_source_employer", "employer_claims", ["source_id", "employer_id"])


def downgrade():
    op.drop_index("ix_employer_claims_source_employer", table_name="employer_claims")
    op.drop_index("ix_employer_claims_lookup", table_name="employer_claims")
    op.drop_table("employer_claims")
    op.drop_index("ix_verification_sources_employer_id", table_name="verification_sources")
    op.drop_table("verification_sources")
    op.drop_table("verified_employers")

"""Persistence constraints and source lifetime using an isolated in-memory store."""

from datetime import datetime, timedelta, timezone
import uuid

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.verifications import VerifiedEmployer, EmployerSource, EmployerClaim
from app.schemas.verifications import VerificationCreate
from app.services.verification_values import claim_key
from app.services.verification_store import load_employers


@pytest.fixture
def verification_db():
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        yield db
    engine.dispose()


def add_employer(db, *, name="Công ty Mẫu", tax_id="0000000001", fields=None, is_demo=False, is_active=True):
    now = datetime.now(timezone.utc)
    company = VerifiedEmployer(legal_name=name, tax_id=tax_id, is_demo=is_demo, is_active=is_active)
    db.add(company)
    db.flush()
    source = EmployerSource(employer_id=company.id, url="https://mau.example/about", label_vi="Nguồn tổng hợp test", evidence_excerpt_vi="Thông tin công khai được dùng trong kiểm thử.", verified_at=now - timedelta(days=1), source_revision=1, reviewed_by="test-reviewer")
    db.add(source)
    db.flush()
    for field, value in (fields or {"company_name": name, "tax_id": tax_id, "contact_email": "HR@mau.example"}).items():
        db.add(EmployerClaim(employer_id=company.id, source_id=source.id, field=field, value_key=claim_key(field, value), assertion="supports"))
    db.commit()
    return company, source


def test_lookup_without_company_name_uses_curated_claims(verification_db):
    company, source = add_employer(verification_db)
    records = load_employers(verification_db, VerificationCreate(contact_email="HR@mau.example"))
    assert [record["id"] for record in records] == [str(company.id)]
    assert records[0]["claims"][0]["source"]["source_revision"] == 1


def test_claim_cannot_point_to_other_employers_source(verification_db):
    company, source = add_employer(verification_db)
    other = VerifiedEmployer(legal_name="Khác", tax_id="0000000002")
    verification_db.add(other)
    verification_db.flush()
    verification_db.add(EmployerClaim(employer_id=other.id, source_id=source.id, field="tax_id", value_key=claim_key("tax_id", "0000000002"), assertion="supports"))
    with pytest.raises(IntegrityError):
        verification_db.flush()


@pytest.mark.parametrize("flag", ["is_demo", "is_active", "expired"])
def test_unusable_source_not_loaded(verification_db, flag):
    _, source = add_employer(verification_db)
    if flag == "expired":
        source.valid_until = datetime.now(timezone.utc) - timedelta(hours=1)
    else:
        setattr(source, flag, flag == "is_demo")
    verification_db.commit()
    assert load_employers(verification_db, VerificationCreate(tax_id="0000000001")) == []


def test_demo_employer_never_loaded(verification_db):
    add_employer(verification_db, is_demo=True)
    assert load_employers(verification_db, VerificationCreate(tax_id="0000000001")) == []


def test_name_not_unique_and_tax_id_is_unique(verification_db):
    add_employer(verification_db)
    add_employer(verification_db, tax_id="0000000002")
    verification_db.add(VerifiedEmployer(legal_name="Trùng mã", tax_id="0000000001"))
    with pytest.raises(IntegrityError):
        verification_db.flush()


def test_unknown_lookup_does_not_create_records(verification_db):
    assert load_employers(verification_db, VerificationCreate(tax_id="0000000001")) == []
    assert verification_db.scalars(select(VerifiedEmployer)).all() == []


def test_refuted_channel_is_loaded_for_scoped_evidence(verification_db):
    company, source = add_employer(verification_db)
    verification_db.add(EmployerClaim(employer_id=company.id, source_id=source.id, field="social_channel_url", value_key=claim_key("social_channel_url", "https://t.me/refuted_test_12345"), assertion="refutes"))
    verification_db.commit()
    assert len(load_employers(verification_db, VerificationCreate(social_channel_url="https://t.me/refuted_test_12345"))) == 1

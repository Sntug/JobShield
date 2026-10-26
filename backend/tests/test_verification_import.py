from copy import deepcopy
from datetime import datetime, timedelta, timezone
import uuid

import pytest
from pydantic import ValidationError
from sqlalchemy import select

from app.cli.import_sources import SourceManifest, import_sources
from app.models.verifications import EmployerClaim, EmployerSource
from tests.test_verification_store import verification_db


def manifest():
    return {"employers": [{"id": str(uuid.uuid4()), "legal_name": "Công ty test", "tax_id": "0000000001", "sources": [{
        "id": str(uuid.uuid4()), "url": "https://mau.example/about", "label_vi": "Nguồn test", "evidence_excerpt_vi": "Thông tin tổng hợp kiểm thử.", "reviewed_by": "reviewer-test", "source_revision": 1,
        "verified_at": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
        "claims": [{"field": "tax_id", "value": "0000000001"}, {"field": "company_name", "value": "Công ty test"}],
    }]}]}


def test_manifest_import_is_atomic_and_keeps_only_bank_hash(verification_db):
    data = manifest()
    data["employers"][0]["sources"][0]["claims"].append({"field": "bank_account", "value": {"account_number": "00001234567", "bank_name": "Bank test", "account_holder": "NGUOI MAU"}})
    parsed = SourceManifest.model_validate(data)
    assert import_sources(verification_db, parsed) == (1, 1)
    claims = verification_db.scalars(select(EmployerClaim)).all()
    assert len(claims) == 3
    assert all("00001234567" not in claim.value_key for claim in claims)
    assert verification_db.scalars(select(EmployerSource)).one().reviewed_by == "reviewer-test"


def test_import_requires_new_revision_for_source_update(verification_db):
    data = manifest()
    import_sources(verification_db, SourceManifest.model_validate(data))
    with pytest.raises(ValueError):
        import_sources(verification_db, SourceManifest.model_validate(data))
    data["employers"][0]["sources"][0]["source_revision"] = 2
    data["employers"][0]["sources"][0]["is_active"] = False
    import_sources(verification_db, SourceManifest.model_validate(data))
    source = verification_db.scalars(select(EmployerSource)).one()
    assert source.source_revision == 2
    assert source.is_active is False


@pytest.mark.parametrize("mutation", ["shared_domain", "future_date", "bank_in_excerpt", "bad_url", "unknown_field"])
def test_untrusted_manifest_rejected_before_write(mutation):
    data = manifest()
    source = data["employers"][0]["sources"][0]
    if mutation == "shared_domain":
        source["claims"].append({"field": "domain", "value": "gmail.com"})
    elif mutation == "future_date":
        source["verified_at"] = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    elif mutation == "bank_in_excerpt":
        source["claims"].append({"field": "bank_account", "value": {"account_number": "00001234567", "bank_name": "Bank test", "account_holder": "NGUOI MAU"}})
        source["evidence_excerpt_vi"] = "Tài khoản 00001234567"
    elif mutation == "bad_url":
        source["url"] = "javascript:alert(1)"
    else:
        source["is_trusted"] = True
    with pytest.raises(ValidationError):
        SourceManifest.model_validate(data)

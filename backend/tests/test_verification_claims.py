"""Independent literal expectations for synthetic curated claim records."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone

import pytest

from app.schemas.verifications import VerificationCreate
from app.services.verifications import verify_claims
from app.services.verification_values import claim_key

NOW = datetime(2026, 10, 26, 10, tzinfo=timezone.utc)


def record(identity="a", name="Công ty Mẫu", *, fields=None):
    values = fields or {"company_name": name, "tax_id": "0000000001", "contact_email": "HR@mau.example"}
    source = {"id": f"source-{identity}", "url": f"https://{identity}.example/about", "label_vi": "Nguồn tổng hợp chỉ dùng trong test", "verified_at": NOW - timedelta(days=1), "source_revision": 1, "evidence_excerpt_vi": "Thông tin minh họa đã được quản trị đối chiếu.", "is_active": True, "is_demo": False, "valid_until": None}
    return {"id": identity, "name": name, "is_active": True, "is_demo": False, "claims": [{"field": field, "value_key": claim_key(field, value), "assertion": "supports", "source": deepcopy(source)} for field, value in values.items()]}


def verify(payload, records):
    return verify_claims(VerificationCreate.model_validate(payload), records, request_id="test-request", now=NOW)


def test_tax_only_lookup_can_match():
    result = verify({"tax_id": "0000000001"}, [record()])
    assert result.verification_label_vi == "Khớp nguồn đã xác minh"
    assert result.field_checks[0].status == "matched"
    assert result.matched_sources[0].source_revision == 1


@pytest.mark.parametrize("field,value", [("contact_email", "HR@mau.example"), ("recruitment_website", "https://mau.example/Careers"), ("social_channel_url", "https://t.me/test_only_12345"), ("bank_account", {"account_number": "0000123", "bank_name": "Bank mẫu", "account_holder": "CHU THE MAU"})])
def test_each_channel_can_identify_without_name(field, value):
    result = verify({field: value}, [record(fields={field: value})])
    assert result.verification_label_vi == "Khớp nguồn đã xác minh"


def test_name_only_and_ambiguous_identity_cannot_verify():
    assert verify({"company_name": "Công ty Mẫu"}, [record()]).verification_label_vi == "Không đủ dữ liệu"
    second = record("b", fields={"company_name": "Công ty Mẫu", "contact_email": "HR@mau.example"})
    for records in ([record(), second], [second, record()]):
        assert verify({"contact_email": "HR@mau.example"}, records).verification_label_vi == "Không đủ dữ liệu"


def test_partial_bank_match_does_not_become_verified_or_conflicting():
    value = {"account_number": "0000123", "bank_name": "Bank mẫu", "account_holder": "NGUOI MAU"}
    result = verify({"tax_id": "0000000001", "bank_account": value}, [record()])
    assert result.verification_label_vi == "Chưa xác minh"
    assert [item.status for item in result.field_checks] == ["matched", "unverified"]
    assert "0000123" not in result.model_dump_json()
    assert "NGUOI MAU" not in result.model_dump_json()


def test_exact_bank_match_requires_holder_too():
    bank = {"account_number": "0000123", "bank_name": "Bank mẫu", "account_holder": "NGUOI MAU"}
    company = record(fields={"tax_id": "0000000001", "bank_account": bank})
    result = verify({"tax_id": "0000000001", "bank_account": {**bank, "account_holder": "NGUOI KHAC"}}, [company])
    assert result.verification_label_vi == "Chưa xác minh"
    assert "0000123" not in claim_key("bank_account", bank)


def test_absence_of_social_or_free_email_is_not_conflict():
    result = verify({"tax_id": "0000000001", "contact_email": "hr@gmail.com", "social_channel_url": "https://t.me/test_only_12345"}, [record()])
    assert result.verification_label_vi == "Chưa xác minh"
    assert not any(check.status == "conflicting" for check in result.field_checks)


def test_explicit_refutation_has_public_evidence():
    company = record()
    company["claims"].append({"field": "contact_email", "value_key": claim_key("contact_email", "other@mau.example"), "assertion": "refutes", "source": deepcopy(company["claims"][0]["source"])})
    result = verify({"tax_id": "0000000001", "contact_email": "other@mau.example"}, [company])
    assert result.verification_label_vi == "Thông tin xung đột"
    assert result.field_checks[1].source_ids == ["source-a"]


def test_two_unique_strong_ids_for_distinct_companies_conflict():
    other = record("b", fields={"recruitment_website": "https://other.example/jobs"})
    result = verify({"tax_id": "0000000001", "recruitment_website": "https://other.example/jobs"}, [record(), other])
    assert result.verification_label_vi == "Thông tin xung đột"
    assert {source.id for source in result.matched_sources} == {"source-a", "source-b"}


@pytest.mark.parametrize("change", [{"is_active": False}, {"is_demo": True}, {"valid_until": NOW}, {"verified_at": NOW + timedelta(seconds=1)}])
def test_unusable_sources_do_not_match(change):
    company = record()
    for claim in company["claims"]:
        claim["source"].update(change)
    result = verify({"tax_id": "0000000001"}, [company])
    assert result.verification_label_vi == "Chưa xác minh"
    assert result.matched_sources == []


def test_shared_domain_never_confirms_arbitrary_account():
    company = record(fields={"domain": "gmail.com"})
    assert verify({"contact_email": "anyone@gmail.com"}, [company]).verification_label_vi == "Chưa xác minh"


def test_explicit_corporate_domain_matches_only_exact_host():
    company = record(fields={"domain": "mau.example"})
    assert verify({"contact_email": "hr@mau.example"}, [company]).verification_label_vi == "Khớp nguồn đã xác minh"
    assert verify({"recruitment_website": "https://mau.example.other.example/jobs"}, [company]).verification_label_vi == "Chưa xác minh"


def test_private_bank_data_cannot_leak_through_curated_excerpt():
    bank = {"account_number": "0000123", "bank_name": "Bank mẫu", "account_holder": "NGUOI MAU"}
    company = record(fields={"bank_account": bank})
    company["claims"][0]["source"]["evidence_excerpt_vi"] = "Tài khoản 0000123 NGUOI MAU"
    result = verify({"bank_account": bank}, [company])
    assert "0000123" not in result.model_dump_json()
    assert "NGUOI MAU" not in result.model_dump_json()


def test_curated_analysis_with_no_extractable_identity_still_returns_result():
    from app.services.analysis import perform_text_analysis
    result = perform_text_analysis("Chào bạn.", [record()])
    assert result[2] == "Không đủ thông tin"
    assert result[5].matched_sources == []


def test_structured_verifier_handles_missing_identity_without_exception():
    from app.schemas.analyses import JobExtracted
    from app.services.employer_verification import verify_employer
    assert verify_employer(JobExtracted(), [record()]) == ("Không đủ dữ liệu", [])


def test_refutes_only_channel_keeps_scoped_evidence_without_global_allegation():
    company = record()
    company["claims"].append({"field": "social_channel_url", "value_key": claim_key("social_channel_url", "https://t.me/refuted_test_12345"), "assertion": "refutes", "source": deepcopy(company["claims"][0]["source"])})
    result = verify({"social_channel_url": "https://t.me/refuted_test_12345"}, [company])
    assert result.verification_label_vi == "Chưa xác minh"
    assert result.field_checks[0].status == "unverified"
    assert result.field_checks[0].source_ids == ["source-a"]
    assert "phạm vi" in result.field_checks[0].reason_vi


def test_channel_supported_by_a_not_globally_conflicting_because_b_denies_it():
    a = record(fields={"contact_email": "HR@mau.example"})
    b = record("b", fields={"tax_id": "0000000002"})
    b["claims"][0].update({"field": "contact_email", "value_key": claim_key("contact_email", "HR@mau.example"), "assertion": "refutes"})
    result = verify({"contact_email": "HR@mau.example"}, [a, b])
    assert result.verification_label_vi == "Khớp nguồn đã xác minh"
    assert {source.id for source in result.matched_sources} == {"source-a"}


def test_short_bank_values_do_not_corrupt_words_or_dates_in_evidence():
    company = record()
    for claim in company["claims"]:
        claim["source"]["label_vi"] = "Data ngày 15"
        claim["source"]["evidence_excerpt_vi"] = "Data ngày 15. Tên A, số 1."
    result = verify({"tax_id": "0000000001", "bank_account": {"account_number": "1", "bank_name": "Bank", "account_holder": "A"}}, [company])
    assert result.matched_sources[0].label_vi == "Data ngày 15"
    assert "Data ngày 15" in result.matched_sources[0].evidence_excerpt_vi
    assert "Tên A" not in result.matched_sources[0].evidence_excerpt_vi
    assert "số 1" not in result.matched_sources[0].evidence_excerpt_vi


@pytest.mark.parametrize("formatted", ["0000 123", "0000-123"])
def test_numeric_bank_formatting_is_consistent(formatted):
    bank = {"account_number": "0000123", "bank_name": "Bank mẫu", "account_holder": "NGUOI MAU"}
    assert claim_key("bank_account", bank) == claim_key("bank_account", {**bank, "account_number": formatted})
    company = record(fields={"bank_account": bank})
    company["claims"][0]["source"]["evidence_excerpt_vi"] = "Số 0000123 đã công bố."
    result = verify({"bank_account": {**bank, "account_number": formatted}}, [company])
    assert "0000123" not in result.model_dump_json()


def test_alphanumeric_account_identifiers_are_not_silently_merged():
    bank = {"account_number": "AB-12", "bank_name": "Bank mẫu", "account_holder": "NGUOI MAU"}
    assert claim_key("bank_account", bank) != claim_key("bank_account", {**bank, "account_number": "AB12"})

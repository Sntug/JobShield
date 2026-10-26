"""Synthetic records only; these tests do not verify real employers."""

from copy import deepcopy

import pytest

from app.schemas.analyses import JobExtracted
from app.services.analysis import perform_text_analysis
from app.services.employer_verification import verify_employer
from app.services.rule_engine import evaluate_analysis


@pytest.fixture
def employer():
    return {
        "name": "Công ty Mẫu",
        "official_domains": ["mau.example"],
        "official_contacts": ["hr@mau.example"],
        "official_recruitment_pages": ["https://mau.example/Careers"],
        "sources": [{
            "id": "test-source", "url": "https://mau.example/Careers",
            "label_vi": "Nguồn tổng hợp chỉ dùng trong test",
            "verified_at": "2026-10-01T00:00:00Z", "is_demo": False,
        }],
    }


def evaluate(employers, **fields):
    return evaluate_analysis(
        "", JobExtracted(company_name="Công ty Mẫu", job_title="Tester", salary="8 triệu", **fields),
        [], employers,
    )


def test_matching_channel_retains_source_provenance(employer):
    _, status, _, evidence, _ = evaluate([employer], contact_email="hr@mau.example")
    assert status == "Khớp nguồn đã xác minh"
    assert evidence.matched_sources == employer["sources"]


@pytest.mark.parametrize("sources", [[], [{}], [{"url": "https://mau.example"}]])
def test_incomplete_provenance_cannot_verify(employer, sources):
    employer["sources"] = sources
    assert evaluate([employer], contact_email="hr@mau.example")[1] == "Chưa xác minh"


def test_demo_source_cannot_verify_runtime_analysis(employer):
    employer["sources"][0]["is_demo"] = True
    assert evaluate([employer], contact_email="hr@mau.example")[1] == "Chưa xác minh"


def test_two_matching_names_and_channels_remain_ambiguous(employer):
    other = deepcopy(employer)
    other["sources"][0]["id"] = "second-source"
    for records in ([employer, other], [other, employer]):
        _, status, _, evidence, _ = evaluate(records, contact_email="hr@mau.example")
        assert status == "Chưa xác minh"
        assert len(evidence.matched_sources) == 2


def test_channel_disambiguates_same_name(employer):
    other = deepcopy(employer)
    other["official_domains"] = ["other.example"]
    other["official_contacts"] = []
    for records in ([other, employer], [employer, other]):
        _, status, _, evidence, _ = evaluate(records, contact_email="hr@mau.example")
        assert status == "Khớp nguồn đã xác minh"
        assert evidence.matched_sources == employer["sources"]


def test_unknown_candidate_prevents_claiming_conflict(employer):
    other = {"name": "Công ty Mẫu"}
    assert evaluate([employer, other], contact_email="hr@other.example")[1] == "Chưa xác minh"


def test_partial_match_does_not_hide_conflicting_website(employer):
    _, status, finding, _, _ = evaluate(
        [employer], contact_email="hr@mau.example", recruitment_website="https://other.example/jobs",
    )
    assert status == "Thông tin xung đột"
    assert "website" in finding.lower()


def test_at_sign_in_url_path_does_not_match_email_domain(employer):
    assert evaluate([employer], recruitment_website="https://other.example/@mau.example")[1] == "Thông tin xung đột"


def test_recruitment_page_paths_are_case_sensitive(employer):
    employer["official_domains"] = []
    assert evaluate([employer], recruitment_website="https://mau.example/careers")[1] == "Thông tin xung đột"


def test_channel_normalization_preserves_original_source(employer):
    original = deepcopy(employer)
    employer["official_domains"] = [" MAU.EXAMPLE "]
    assert evaluate([employer], contact_email="HR@mau.example")[1] == "Khớp nguồn đã xác minh"
    assert employer["sources"] == original["sources"]


@pytest.mark.parametrize("timestamp", ["not-a-date", "2026-10-01T00:00:00"])
def test_invalid_source_timestamp_cannot_verify(employer, timestamp):
    employer["sources"][0]["verified_at"] = timestamp
    assert evaluate([employer], contact_email="hr@mau.example")[1] == "Chưa xác minh"


def test_unparseable_website_does_not_crash_or_verify(employer):
    assert evaluate([employer], recruitment_website="https://[invalid")[1] == "Chưa xác minh"


def test_conflict_retains_all_candidate_sources(employer):
    other = deepcopy(employer)
    other["sources"][0]["id"] = "second-source"
    _, status, _, evidence, _ = evaluate([employer, other], contact_email="hr@other.example")
    assert status == "Thông tin xung đột"
    assert {source["id"] for source in evidence.matched_sources} == {"test-source", "second-source"}


def test_empty_verification_input_is_insufficient():
    assert verify_employer(JobExtracted(), []) == ("Không đủ dữ liệu", [])


def test_name_alone_returns_candidates_without_verifying(employer):
    assert verify_employer(JobExtracted(company_name="Công ty Mẫu"), [employer]) == ("Chưa xác minh", [employer])


def test_demo_employer_cannot_create_runtime_conflict(employer):
    employer["is_demo"] = True
    assert evaluate([employer], contact_email="hr@other.example")[1] == "Chưa xác minh"


def test_demo_employer_cannot_create_runtime_impersonation_warning(employer):
    employer["is_demo"] = True
    text = (
        "Công ty Mẫu tuyển Tester. Lương: 8 triệu đồng/tháng. "
        "Chúng tôi là phòng tuyển dụng Công ty Mẫu, chỉ nhận hồ sơ tại hr@other.example."
    )
    result = perform_text_analysis(text, [employer])
    assert result[3] == "Chưa xác minh"
    assert not any(item.rule_id == "RULE_IMPERSONATION" for item in result[1])


def test_matching_same_name_candidate_prevents_false_impersonation(employer):
    other = deepcopy(employer)
    other["official_domains"] = ["other.example"]
    other["official_contacts"] = []
    text = (
        "Công ty Mẫu tuyển Tester. Lương: 8 triệu đồng/tháng. "
        "Chúng tôi là phòng tuyển dụng Công ty Mẫu, chỉ nhận hồ sơ tại hr@mau.example."
    )
    for records in ([employer, other], [other, employer]):
        result = perform_text_analysis(text, records)
        assert result[3] == "Khớp nguồn đã xác minh"
        assert not any(item.rule_id == "RULE_IMPERSONATION" for item in result[1])

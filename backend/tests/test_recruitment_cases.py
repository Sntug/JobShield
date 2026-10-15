import json
from pathlib import Path
from urllib.parse import urlparse

import pytest


@pytest.fixture
def cases():
    data = json.loads(
        (Path(__file__).parent / "fixtures/recruitment_cases.json").read_text()
    )
    assert data["is_demo"] is True
    assert data["usage"] == "test_only"
    assert len(data["cases"]) == len({case["id"] for case in data["cases"]})
    return {case["id"]: case for case in data["cases"]}


def test_required_product_scenarios(cases):
    assert set(cases) == {
        "complete", "upfront_fee", "impersonation", "missing_information",
        "suspicious_unverified", "ocr_failure", "url_blocked",
        "same_name", "insufficient_contact",
    }
    for case in cases.values():
        assert case["is_demo"] is True
        assert case["expected"]["fraud_confirmed"] is False
        assert case["expected"]["publish_warning"] is False
        assert case["expected"]["actions_vi"]
        for indicator in case["expected"]["indicators"]:
            assert indicator["matched_quote"] in case["input"]["text"]
        for employer in case["employer_records"]:
            assert employer["is_demo"] is True
            for source in employer["sources"]:
                assert source["is_demo"] is True
                assert urlparse(source["url"]).hostname.endswith(".example")
                assert "demo" in source["label_vi"].lower()
    assert {indicator["category_vi"] for case in cases.values()
            for indicator in case["expected"]["indicators"]} == {
        "Phí tuyển dụng trước", "Đặt cọc trước phỏng vấn", "Yêu cầu chuyển tiền",
        "Chỉ dấu mạo danh", "Kênh liên hệ đáng ngờ", "Hứa thu nhập phi thực tế",
        "Nhiệm vụ có nạp tiền", "Yêu cầu dữ liệu nhạy cảm bất thường",
    }


def test_missing_information_never_means_safe(cases):
    expected = cases["missing_information"]["expected"]
    assert expected["risk_label_vi"] == "Không đủ thông tin"
    assert expected["verification_label_vi"] == "Không đủ dữ liệu"
    assert expected["job"]["company_name"] is None
    assert expected["job"]["salary"] is None
    assert expected["evidence"]["missing_vi"]


def test_company_name_alone_does_not_verify_advertisement(cases):
    for case_id in ("same_name", "insufficient_contact"):
        expected = cases[case_id]["expected"]
        assert expected["verification_label_vi"] == "Chưa xác minh"
        assert expected["job"]["contact_email"] is None
        assert expected["job"]["recruitment_website"] is None
    complete = cases["complete"]["expected"]
    assert complete["verification_label_vi"] == "Khớp nguồn đã xác minh"
    assert "tin" in complete["limitations_vi"].lower()
    assert complete["indicators"] == []


def test_failure_requires_manual_text_instead_of_fabricated_result(cases):
    for case_id in ("ocr_failure", "url_blocked"):
        case = cases[case_id]
        assert case["input"]["text"] is None
        assert case["input"]["failure_vi"]
        assert case["expected"]["job"] is None
        assert case["expected"]["risk_label_vi"] is None
        assert case["expected"]["verification_label_vi"] is None
        assert case["expected"]["indicators"] == []

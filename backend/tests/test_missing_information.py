from app.schemas.analyses import IndicatorItem, JobExtracted
from app.services.rule_engine import evaluate_analysis


def test_fee_warning_keeps_missing_fields():
    indicator = IndicatorItem(category_vi="Phí tuyển dụng trước", rule_id="RULE_UPFRONT_FEE", matched_quote="đóng phí")
    risk, _, _, evidence, _ = evaluate_analysis("đóng phí", JobExtracted(), [indicator])
    assert risk == "Rủi ro cao"
    assert {"Tên công ty", "Vị trí tuyển dụng", "Mức lương"} <= set(evidence.missing_vi)
    assert "Email/domain hoặc kênh tuyển dụng đối chiếu được" in evidence.missing_vi


def test_conflict_keeps_missing_salary():
    job = JobExtracted(company_name="Công ty Mẫu", job_title="Tester", contact_email="hr@other.example")
    _, status, _, evidence, _ = evaluate_analysis("", job, [], [{
        "name": "Công ty Mẫu", "official_domains": ["mau.example"],
    }])
    assert status == "Thông tin xung đột"
    assert "Mức lương" in evidence.missing_vi

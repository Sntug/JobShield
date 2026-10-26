"""Analysis orchestration service."""

from typing import Any, Dict, List, Optional, Tuple
from app.schemas.analyses import EvidenceData, IndicatorItem, JobExtracted
from app.services.extraction import extract_job_fields
from app.services.rule_engine import detect_indicators, evaluate_analysis


def perform_text_analysis(
    text: str,
    employer_records: Optional[List[Dict[str, Any]]] = None,
    is_demo: bool = False,
) -> Tuple[JobExtracted, List[IndicatorItem], str, str, str, EvidenceData, List[str]]:
    """Thực hiện trích xuất và phân tích rủi ro thuần túy từ văn bản.

    Mặc định is_demo=False cho người dùng thật.
    Trả về: (job, indicators, risk_label_vi, verification_label_vi, finding_vi, evidence, actions_vi)
    """
    employer_records = [emp for emp in (employer_records or []) if is_demo or not emp.get("is_demo")]
    job = extract_job_fields(text)
    curated = bool(employer_records) and all("claims" in emp for emp in employer_records)
    if curated:
        from pydantic import ValidationError
        from app.schemas.verifications import VerificationCreate
        try:
            curated_payload = VerificationCreate(company_name=job.company_name, contact_email=job.contact_email, recruitment_website=job.recruitment_website)
        except ValidationError:
            employer_records, curated = [], False
    indicators = detect_indicators(text, employer_records=employer_records, is_demo=is_demo)
    risk_label_vi, verification_label_vi, finding_vi, evidence, actions_vi = evaluate_analysis(
        text=text,
        job=job,
        indicators=indicators,
        employer_records=None if curated else employer_records,
        is_demo=is_demo,
    )
    if curated:
        from app.services.verifications import verify_claims
        verification = verify_claims(curated_payload, employer_records, request_id="internal")
        verification_label_vi = verification.verification_label_vi
        prefix = "Có dấu hiệu cảnh báo trong nội dung tin. " if indicators else ("Không đủ thông tin để đánh giá đầy đủ nội dung tin. " if risk_label_vi == "Không đủ thông tin" else "")
        finding_vi = prefix + verification.summary_vi + " " + verification.limitations_vi[0]
        missing = evidence.missing_vi or []
        if verification_label_vi == "Khớp nguồn đã xác minh":
            missing = [item for item in missing if "nguồn" not in item.lower()]
        evidence = EvidenceData(
            matched_sources=[{**source.model_dump(mode="json"), "is_demo": False} for source in verification.matched_sources],
            missing_vi=list(dict.fromkeys(missing + verification.missing_fields_vi)),
            limitations_vi=list(dict.fromkeys((evidence.limitations_vi or []) + verification.limitations_vi)),
            is_demo=False,
        )
        actions_vi = list(dict.fromkeys(actions_vi + verification.recommended_actions_vi))
    return job, indicators, risk_label_vi, verification_label_vi, finding_vi, evidence, actions_vi

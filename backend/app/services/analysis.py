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
    job = extract_job_fields(text)
    indicators = detect_indicators(text, employer_records=employer_records)
    risk_label_vi, verification_label_vi, finding_vi, evidence, actions_vi = evaluate_analysis(
        text=text,
        job=job,
        indicators=indicators,
        employer_records=employer_records,
        is_demo=is_demo,
    )
    return job, indicators, risk_label_vi, verification_label_vi, finding_vi, evidence, actions_vi

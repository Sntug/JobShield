"""Schemas for text analysis requests and responses."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, field_validator


class AnalysisCreate(BaseModel):
    """Schema request gửi tin tuyển dụng để phân tích."""

    text: str

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("Văn bản phân tích phải là chuỗi ký tự.")
        if len(v.strip()) == 0:
            raise ValueError("Văn bản phân tích không được để trống hoặc chỉ chứa khoảng trắng.")
        if len(v) > 10000:
            raise ValueError("Văn bản phân tích không được vượt quá 10.000 ký tự.")
        return v


class JobExtracted(BaseModel):
    """11 trường trích xuất thực thể tuyển dụng (nullable)."""

    company_name: Optional[str] = None
    job_title: Optional[str] = None
    salary: Optional[str] = None
    location: Optional[str] = None
    employment_type: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    recruitment_website: Optional[str] = None
    application_requirements: Optional[str] = None
    required_payments: Optional[str] = None
    suspicious_instructions: Optional[str] = None


class IndicatorItem(BaseModel):
    """Dấu hiệu cảnh báo với trích đoạn nguyên văn."""

    category_vi: str
    rule_id: str
    matched_quote: str
    weight: Optional[int] = None
    explanation_vi: Optional[str] = None


class EvidenceData(BaseModel):
    """Dữ liệu đối chiếu nguồn, thiếu sót và giới hạn."""

    matched_sources: List[Dict[str, Any]] = []
    missing_vi: Optional[List[str]] = None
    limitations_vi: Optional[List[str]] = None
    is_demo: bool = False


class AnalysisResponse(BaseModel):
    """Schema kết quả phân tích tin tuyển dụng hoàn chỉnh."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    guest_session_token: Optional[str] = None
    risk_label_vi: str
    verification_label_vi: str
    finding_vi: str
    job: JobExtracted
    indicators: List[IndicatorItem]
    evidence: EvidenceData
    actions_vi: List[str]
    engine_version: str
    rules_version: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    is_saved: Optional[bool] = False


class AnalysisListResponse(BaseModel):
    """Danh sách kết quả phân tích có phân trang."""

    items: List[AnalysisResponse]
    total: int
    page: int
    page_size: int

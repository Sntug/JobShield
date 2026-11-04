"""Schemas for batch recruitment analysis requests and responses."""

from datetime import datetime
from typing import List, Literal, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.analyses import AnalysisResponse


class BatchItemInput(BaseModel):
    """Mục dữ liệu đầu vào trong đợt phân tích hàng loạt."""

    type: Literal["url", "text"]
    value: str = Field(..., min_length=1, max_length=10000)

    @field_validator("value")
    @classmethod
    def validate_value(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("Nội dung phân tích phải là chuỗi ký tự.")
        trimmed = v.strip()
        if len(trimmed) == 0:
            raise ValueError("Nội dung phân tích không được để trống hoặc chỉ chứa khoảng trắng.")
        if len(v) > 10000:
            raise ValueError("Nội dung phân tích không được vượt quá 10.000 ký tự.")
        return trimmed


class BatchAnalysisCreate(BaseModel):
    """Schema request tạo đợt phân tích hàng loạt."""

    items: List[BatchItemInput] = Field(..., min_length=1, max_length=10)
    use_ai: bool = False
    ai_consent: bool = False


class BatchItemResponse(BaseModel):
    """Kết quả chi tiết của từng mục trong đợt phân tích."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    item_order: int
    input_type: str
    input_value: str
    status: str  # pending, processing, success, error, cancelled
    analysis_id: Optional[uuid.UUID] = None
    analysis: Optional[AnalysisResponse] = None
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class BatchAnalysisResponse(BaseModel):
    """Schema kết quả đợt phân tích hàng loạt."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: str  # pending, processing, completed, failed, cancelled
    total_items: int
    processed_items: int
    items: List[BatchItemResponse]
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime] = None


class BatchAnalysisCreatedResponse(BatchAnalysisResponse):
    """Create response; a new guest credential is returned only when issued."""

    guest_session_token: Optional[str] = None

    @field_validator("items", mode="after")
    @classmethod
    def sort_items(cls, v: List[BatchItemResponse]) -> List[BatchItemResponse]:
        return sorted(v, key=lambda x: x.item_order)

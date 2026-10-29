"""Pydantic schemas for risk indicator detection rules."""

from datetime import datetime
from typing import List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class RiskIndicatorResponse(BaseModel):
    """Quy tắc chỉ dấu rủi ro."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    description: str
    explanation_vi: str
    weight: int
    enabled: bool
    updated_at: datetime


class RiskIndicatorUpdateRequest(BaseModel):
    """Cập nhật trạng thái hoặc trọng số của quy tắc."""

    enabled: Optional[bool] = None
    weight: Optional[int] = Field(None, ge=1, le=100)
    description: Optional[str] = Field(None, max_length=1000)


class RiskIndicatorListResponse(BaseModel):
    """Danh sách các quy tắc chỉ dấu rủi ro."""

    items: List[RiskIndicatorResponse]

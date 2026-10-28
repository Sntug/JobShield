"""Pydantic schemas for saved analyses."""

import uuid
from datetime import datetime
from typing import List
from pydantic import BaseModel, ConfigDict
from app.schemas.analyses import AnalysisResponse


class SavedAnalysisItemResponse(BaseModel):
    """Thông tin bài phân tích đã lưu."""

    model_config = ConfigDict(from_attributes=True)

    analysis_id: uuid.UUID
    saved_at: datetime
    analysis: AnalysisResponse


class SavedAnalysisListResponse(BaseModel):
    """Danh sách các bài phân tích đã lưu có phân trang."""

    items: List[SavedAnalysisItemResponse]
    total: int
    page: int
    page_size: int

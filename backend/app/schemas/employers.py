"""Pydantic schemas for employer management by admin."""

from datetime import datetime
from typing import List, Literal, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from app.schemas.curation import ManifestClaim, ManifestSource
from app.services.verification_values import normalize_tax_id


class EmployerAdminCreate(BaseModel):
    """Yêu cầu tạo nhà tuyển dụng đã xác minh."""

    legal_name: str = Field(..., min_length=1, max_length=255)
    tax_id: Optional[str] = None

    @field_validator("legal_name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Tên doanh nghiệp không được để trống.")
        return trimmed

    @field_validator("tax_id")
    @classmethod
    def validate_tax_id(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
        return normalize_tax_id(v) if v else None


class EmployerAdminUpdate(BaseModel):
    """Cập nhật thông tin nhà tuyển dụng."""

    legal_name: Optional[str] = Field(None, min_length=1, max_length=255)
    tax_id: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator("tax_id")
    @classmethod
    def validate_tax_id(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
        return normalize_tax_id(v) if v else None


class EmployerSourceAdminCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    url: str = Field(min_length=1, max_length=2048)
    label_vi: str = Field(min_length=1, max_length=255)
    evidence_excerpt_vi: str = Field(min_length=1, max_length=4000)
    valid_until: Optional[datetime] = None

    @field_validator("url")
    @classmethod
    def public_url(cls, value):
        return ManifestSource.valid_public_url(value)

    @field_validator("valid_until")
    @classmethod
    def future_expiry(cls, value):
        from datetime import timezone
        if value is not None and (value.utcoffset() is None or value <= datetime.now(timezone.utc)):
            raise ValueError("Hiệu lực nguồn phải nằm trong tương lai và có múi giờ.")
        return value


class EmployerClaimAdminCreate(ManifestClaim):
    source_id: uuid.UUID


class EmployerSourceAdminResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    url: str
    label_vi: str
    evidence_excerpt_vi: str
    is_active: bool
    verified_at: datetime
    valid_until: Optional[datetime] = None



class EmployerAdminResponse(BaseModel):
    """Thông tin nhà tuyển dụng dành cho quản trị viên."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    legal_name: str
    tax_id: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    sources_count: int = 0


class EmployerAdminListResponse(BaseModel):
    """Danh sách nhà tuyển dụng phân trang."""

    items: List[EmployerAdminResponse]
    total: int
    page: int
    page_size: int

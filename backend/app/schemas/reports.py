"""Pydantic schemas for community reports, evidence, moderation, and public warnings."""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ReportEvidenceCreate(BaseModel):
    """Yêu cầu tạo bằng chứng đính kèm."""

    evidence_type: Literal["text", "url", "image"]
    content: Optional[str] = Field(None, max_length=10000)
    source_url: Optional[str] = Field(None, max_length=2048)
    storage_key: Optional[str] = Field(None, max_length=255)
    file_name: Optional[str] = Field(None, max_length=255)
    mime_type: Optional[str] = Field(None, max_length=100)
    size_bytes: Optional[int] = Field(None, ge=0, le=10 * 1024 * 1024)

    @field_validator("source_url")
    @classmethod
    def validate_source_url(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if v and not (v.startswith("http://") or v.startswith("https://")):
                raise ValueError("source_url phải là URL hợp lệ bắt đầu bằng http:// hoặc https://")
        return v or None


class ReportEvidenceResponse(BaseModel):
    """Thông tin bằng chứng đính kèm."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    evidence_type: str
    content: Optional[str] = None
    source_url: Optional[str] = None
    file_name: Optional[str] = None
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = None
    created_at: datetime


class ReportCreate(BaseModel):
    """Yêu cầu gửi báo cáo tin tuyển dụng đáng ngờ."""

    reason: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=5, max_length=5000)
    analysis_id: Optional[uuid.UUID] = None
    evidences: List[ReportEvidenceCreate] = Field(default_factory=list, max_length=10)

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Lý do báo cáo không được để trống.")
        return trimmed

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Mô tả chi tiết không được để trống.")
        return trimmed


class ModerationActionResponse(BaseModel):
    """Thông tin hành động kiểm duyệt hiển thị cho người báo cáo."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    action_type: str
    from_status: str
    to_status: str
    decision_summary: str
    created_at: datetime


class ModerationActionAdminResponse(ModerationActionResponse):
    """Thông tin hành động kiểm duyệt đầy đủ dành cho quản trị viên."""

    moderator_id: uuid.UUID
    moderator_name: Optional[str] = None
    report_version_after: int
    reviewed_evidence_ids: Optional[List[str]] = None
    private_note: Optional[str] = None


class ReportResponse(BaseModel):
    """Chi tiết báo cáo gửi cho người dùng."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    reason: str
    description: str
    status: str
    version: int
    analysis_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime
    evidences: List[ReportEvidenceResponse] = Field(default_factory=list)
    moderation_actions: List[ModerationActionResponse] = Field(default_factory=list)


class ReportListResponse(BaseModel):
    """Danh sách báo cáo phân trang cho người dùng."""

    items: List[ReportResponse]
    total: int
    page: int
    page_size: int


class ReportAdminResponse(ReportResponse):
    """Chi tiết báo cáo mở rộng dành cho quản trị viên."""

    reporter_id: Optional[uuid.UUID] = None
    reporter_email: Optional[str] = None
    reporter_name: Optional[str] = None
    moderation_actions: List[ModerationActionAdminResponse] = Field(default_factory=list)


class ReportAdminListResponse(BaseModel):
    """Danh sách báo cáo phân trang dành cho quản trị viên."""

    items: List[ReportAdminResponse]
    total: int
    page: int
    page_size: int


class ModerationActionCreate(BaseModel):
    """Yêu cầu thực hiện kiểm duyệt báo cáo của quản trị viên."""

    action_type: Literal["review", "request_evidence", "verify", "reject"]
    to_status: Literal["pending", "under_review", "verified", "rejected"]
    decision_summary: str = Field(..., min_length=1, max_length=1000)
    private_note: Optional[str] = Field(None, max_length=2000)
    expected_version: int = Field(..., ge=1)
    reviewed_evidence_ids: Optional[List[str]] = None

    @field_validator("decision_summary")
    @classmethod
    def validate_decision_summary(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Tóm tắt quyết định không được để trống.")
        return trimmed


class WarningPublicSource(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    label_vi: str = Field(min_length=1, max_length=255)
    url: str = Field(min_length=1, max_length=2048)

    @field_validator("url")
    @classmethod
    def public_url(cls, value):
        from app.schemas.curation import ManifestSource
        return ManifestSource.valid_public_url(value)


class PublicWarningCreate(BaseModel):
    """Yêu cầu tạo và xuất bản cảnh báo cộng đồng."""

    title_vi: str = Field(..., min_length=5, max_length=255)
    public_summary_vi: str = Field(..., min_length=10, max_length=5000)
    report_id: Optional[uuid.UUID] = None
    decision_id: Optional[uuid.UUID] = None
    public_sources_snapshot: List[WarningPublicSource] = Field(min_length=1, max_length=10)


class PublicWarningSupersede(BaseModel):
    """Yêu cầu đính chính / thay thế cảnh báo đã xuất bản."""

    title_vi: str = Field(..., min_length=5, max_length=255)
    public_summary_vi: str = Field(..., min_length=10, max_length=5000)
    public_sources_snapshot: List[WarningPublicSource] = Field(min_length=1, max_length=10)


class PublicWarningWithdraw(BaseModel):
    """Yêu cầu thu hồi cảnh báo cộng đồng."""

    withdrawal_reason_vi: str = Field(..., min_length=5, max_length=1000)


class PublicWarningResponse(BaseModel):
    """Bản cảnh báo cộng đồng hiển thị công khai."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    revision: int
    status: str
    title_vi: str
    public_summary_vi: str
    public_sources_snapshot: List[Dict[str, Any]]
    published_at: Optional[datetime] = None
    created_at: datetime
    previous_warning_id: Optional[uuid.UUID] = None
    next_warning_id: Optional[uuid.UUID] = None
    withdrawn_at: Optional[datetime] = None
    withdrawal_reason_vi: Optional[str] = None


class PublicWarningListResponse(BaseModel):
    """Danh sách cảnh báo cộng đồng phân trang."""

    items: List[PublicWarningResponse]
    total: int
    page: int
    page_size: int

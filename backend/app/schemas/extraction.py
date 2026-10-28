"""Pydantic schemas for recruitment content extraction (OCR & URL)."""

from typing import Optional
from urllib.parse import urlparse
from pydantic import BaseModel, ConfigDict, Field, field_validator


class URLExtractionRequest(BaseModel):
    """Yêu cầu trích xuất nội dung tin tuyển dụng từ URL công khai."""

    url: str
    model_config = ConfigDict(extra="forbid")

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("URL phải là chuỗi ký tự.")
        clean = v.strip()
        if not clean:
            raise ValueError("URL không được để trống.")
        if len(clean) > 2048:
            raise ValueError("Độ dài URL không được vượt quá 2048 ký tự.")
        clean.encode("utf-8")
        try:
            urlparse(clean).port
        except ValueError:
            raise ValueError("URL hoặc cổng không hợp lệ.") from None
        return clean


class ImageExtractionRequest(BaseModel):
    """Yêu cầu trích xuất văn bản từ ảnh qua chuỗi Base64."""

    image_base64: str
    filename: Optional[str] = Field(default=None, max_length=255)
    content_type: Optional[str] = Field(default=None, max_length=100)
    model_config = ConfigDict(extra="forbid")

    @field_validator("filename", "content_type")
    @classmethod
    def validate_unicode(cls, value: Optional[str]) -> Optional[str]:
        if value is not None:
            value.encode("utf-8")
        return value

    @field_validator("image_base64")
    @classmethod
    def validate_base64(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("Dữ liệu ảnh base64 phải là chuỗi ký tự.")
        clean = v.strip()
        if not clean:
            raise ValueError("Dữ liệu ảnh base64 không được để trống.")
        # Cho phép prefix data:image/...;base64,
        if "," in clean:
            clean = clean.split(",", 1)[1].strip()
        return clean


class ExtractionResponse(BaseModel):
    """Kết quả trích xuất văn bản tin tuyển dụng."""

    request_id: str
    success: bool
    source_type: str  # "image" | "url"
    text: Optional[str] = None
    failure_vi: Optional[str] = None
    source_name: Optional[str] = None
    confidence: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)

"""Shared validation for curated claims and public source evidence."""
from datetime import datetime, timezone
from typing import Literal
import uuid
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from app.schemas.verifications import VerificationCreate
from app.services.verification_values import SHARED_DOMAINS, bank_private_values, canonical_value, normalize_url


class ManifestClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")
    field: Literal["company_name", "tax_id", "contact_email", "recruitment_website", "social_channel_url", "bank_account", "domain"]
    value: str | dict
    assertion: Literal["supports", "refutes"] = "supports"

    @model_validator(mode="after")
    def validate_value(self):
        if self.field == "domain":
            from urllib.parse import urlsplit
            if not isinstance(self.value, str):
                raise ValueError("Domain claim không hợp lệ.")
            domain = canonical_value("domain", self.value)
            normalized = normalize_url("https://" + domain)
            if urlsplit(normalized).hostname != domain or "." not in domain or domain in SHARED_DOMAINS:
                raise ValueError("Domain claim không hợp lệ hoặc là nền tảng dùng chung.")
            self.value = domain
        else:
            payload = VerificationCreate.model_validate({self.field: self.value})
            self.value = payload.model_dump(exclude_none=True)[self.field]
        return self


class ManifestSource(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    id: uuid.UUID
    url: str = Field(max_length=2048)
    label_vi: str = Field(min_length=1, max_length=255)
    evidence_excerpt_vi: str = Field(min_length=1, max_length=4000)
    reviewed_by: str = Field(min_length=1, max_length=255)
    source_revision: int = Field(ge=1, strict=True)
    verified_at: datetime
    valid_until: datetime | None = None
    is_active: bool = True
    is_demo: bool = False
    claims: list[ManifestClaim] = Field(min_length=1)

    @field_validator("url")
    @classmethod
    def valid_public_url(cls, value):
        from ipaddress import ip_address
        from urllib.parse import urlsplit
        normalized = normalize_url(value)
        parts = urlsplit(normalized)
        if parts.query or parts.fragment or parts.hostname == "localhost" or "." not in parts.hostname:
            raise ValueError("Nguồn public không được chứa tham số truy cập riêng.")
        try:
            if not ip_address(parts.hostname).is_global:
                raise ValueError("Nguồn public không được là địa chỉ nội bộ.")
        except ValueError as error:
            if str(error) == "Nguồn public không được là địa chỉ nội bộ.":
                raise
        return normalized

    @model_validator(mode="after")
    def valid_evidence(self):
        now = datetime.now(timezone.utc)
        if self.verified_at.utcoffset() is None or self.verified_at > now:
            raise ValueError("Ngày kiểm chứng nguồn không hợp lệ.")
        if self.valid_until is not None and (self.valid_until.utcoffset() is None or self.valid_until <= self.verified_at):
            raise ValueError("Hiệu lực nguồn không hợp lệ.")
        public = " ".join((self.url, self.label_vi, self.evidence_excerpt_vi)).casefold()
        for claim in self.claims:
            if claim.field == "bank_account" and any(value.casefold() in public for value in bank_private_values(claim.value)):
                raise ValueError("Nguồn public chứa dữ liệu ngân hàng chưa lược bỏ.")
        return self


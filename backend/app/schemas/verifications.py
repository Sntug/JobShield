"""Public verification contract, independent of the R1.1 analysis schema."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.services.verification_values import normalize_email, normalize_tax_id, normalize_url

VerificationField = Literal["company_name", "tax_id", "contact_email", "recruitment_website", "social_channel_url", "bank_account"]
VerificationLabel = Literal["Khớp nguồn đã xác minh", "Thông tin xung đột", "Chưa xác minh", "Không đủ dữ liệu"]


class BankAccount(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)
    account_number: Annotated[str, Field(min_length=1, max_length=50)]
    bank_name: Annotated[str, Field(min_length=1, max_length=100)]
    account_holder: Annotated[str, Field(min_length=1, max_length=255)]


class VerificationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)
    company_name: Annotated[str, Field(max_length=255)] | None = None
    tax_id: str | None = None
    contact_email: Annotated[str, Field(max_length=255)] | None = None
    recruitment_website: Annotated[str, Field(max_length=2048)] | None = None
    social_channel_url: Annotated[str, Field(max_length=2048)] | None = None
    bank_account: BankAccount | None = None

    @model_validator(mode="before")
    @classmethod
    def normalize_empty_fields(cls, data):
        if not isinstance(data, dict):
            return data
        values = {key: (None if isinstance(value, str) and not value.strip() else value) for key, value in data.items()}
        bank = values.get("bank_account")
        if isinstance(bank, dict) and set(bank) <= {"account_number", "bank_name", "account_holder"} and all(value is None or isinstance(value, str) and not value.strip() for value in bank.values()):
            values["bank_account"] = None
        return values

    @field_validator("tax_id", "contact_email", "recruitment_website", "social_channel_url")
    @classmethod
    def validate_identifiers(cls, value, info):
        if value is None:
            return None
        if info.field_name == "tax_id":
            return normalize_tax_id(value)
        if info.field_name == "contact_email":
            return normalize_email(value)
        return normalize_url(value, social=info.field_name == "social_channel_url")

    @model_validator(mode="after")
    def require_input(self):
        if not any(getattr(self, field) is not None for field in type(self).model_fields):
            raise ValueError("NO_INPUT_PROVIDED")
        return self


class FieldCheck(BaseModel):
    field: VerificationField
    status: Literal["matched", "conflicting", "unverified"]
    reason_vi: str
    source_ids: list[str]


class VerificationSource(BaseModel):
    id: str
    url: str
    label_vi: str
    verified_at: datetime
    source_revision: Annotated[int, Field(ge=1)]
    evidence_excerpt_vi: str


class VerificationResponse(BaseModel):
    request_id: str
    verification_label_vi: VerificationLabel
    summary_vi: str
    findings_vi: list[str]
    field_checks: list[FieldCheck]
    matched_sources: list[VerificationSource]
    missing_fields_vi: list[str]
    limitations_vi: list[str]
    recommended_actions_vi: list[str]
    verification_version: str
    checked_at: datetime

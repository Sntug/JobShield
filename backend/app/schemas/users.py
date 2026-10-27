"""Pydantic schemas for user profile and stats."""

import uuid
from datetime import datetime
from typing import Dict
from pydantic import BaseModel, ConfigDict, Field, field_validator


class UserResponse(BaseModel):
    """Thông tin công khai của tài khoản (không bao giờ lộ password_hash)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    role: str
    created_at: datetime


class UserUpdateRequest(BaseModel):
    """Cập nhật thông tin tài khoản (chỉ cho phép sửa tên hiển thị)."""

    full_name: str = Field(..., min_length=1, max_length=255)

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Họ và tên không được để trống.")
        return trimmed


class PasswordChangeRequest(BaseModel):
    """Yêu cầu đổi mật khẩu (yêu cầu mật khẩu cũ để xác thực)."""

    old_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=15, max_length=128)


class UserStatsResponse(BaseModel):
    """Thống kê cá nhân của người dùng."""

    total_analyses: int
    saved_analyses: int
    risk_distribution: Dict[str, int]

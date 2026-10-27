"""Pydantic schemas for authentication and guest claims."""

import re
import uuid
from typing import List
from pydantic import BaseModel, Field, field_validator
from app.schemas.users import UserResponse

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class UserRegisterRequest(BaseModel):
    """Yêu cầu đăng ký tài khoản mới."""

    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=15, max_length=128)
    full_name: str = Field(..., min_length=1, max_length=255)

    @field_validator("email")
    @classmethod
    def validate_and_normalize_email(cls, v: str) -> str:
        trimmed = v.strip().lower()
        if not EMAIL_REGEX.match(trimmed):
            raise ValueError("Email không hợp lệ.")
        return trimmed

    @field_validator("full_name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Họ và tên không được để trống.")
        return trimmed


class UserLoginRequest(BaseModel):
    """Yêu cầu đăng nhập."""

    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class TokenResponse(BaseModel):
    """Phản hồi cấp token xác thực bearer."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = 86400  # 24 giờ tính bằng giây
    user: UserResponse


class ClaimGuestRequest(BaseModel):
    """Yêu cầu chuyển quyền sở hữu kết quả phân tích từ phiên khách sang tài khoản."""

    guest_session_token: str = Field(..., min_length=1)


class ClaimGuestResponse(BaseModel):
    """Kết quả chuyển quyền phiên khách."""

    claimed_count: int
    claimed_ids: List[uuid.UUID]

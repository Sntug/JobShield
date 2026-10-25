"""Security utilities for guest session tokens."""

import hashlib
import secrets


def generate_guest_token() -> str:
    """Sinh chuỗi token an toàn chứa 32 byte entropy (URL-safe base64, ~43 ký tự)."""
    return secrets.token_urlsafe(32)


def hash_guest_token(token: str) -> str:
    """Tạo hàm băm SHA-256 của token để lưu trữ an toàn trong DB."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

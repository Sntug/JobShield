"""Security utilities for guest session tokens and user authentication."""

import hashlib
import hmac
import secrets

SCRYPT_N = 32768
SCRYPT_R = 8
SCRYPT_P = 3
SCRYPT_MAXMEM = 64 * 1024 * 1024
MIN_PASSWORD_LENGTH = 15
MAX_PASSWORD_LENGTH = 128


def generate_guest_token() -> str:
    """Sinh chuỗi token an toàn chứa 32 byte entropy (URL-safe base64, ~43 ký tự)."""
    return secrets.token_urlsafe(32)


def hash_guest_token(token: str) -> str:
    """Tạo hàm băm SHA-256 của token để lưu trữ an toàn trong DB."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_bearer_token() -> str:
    """Sinh chuỗi bearer token an toàn 32 byte entropy cho người dùng đăng nhập."""
    return secrets.token_urlsafe(32)


def hash_bearer_token(token: str) -> str:
    """Tạo hàm băm SHA-256 của bearer token để lưu trong access_sessions."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def hash_password(password: str) -> str:
    """Băm mật khẩu bằng scrypt theo chuẩn OWASP (N=32768, r=8, p=3).

    Yêu cầu độ dài mật khẩu từ 15 đến 128 ký tự.
    """
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Mật khẩu phải có tối thiểu {MIN_PASSWORD_LENGTH} ký tự.")
    if len(password) > MAX_PASSWORD_LENGTH:
        raise ValueError(f"Mật khẩu tối đa {MAX_PASSWORD_LENGTH} ký tự.")

    salt = secrets.token_bytes(16)
    key = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        maxmem=SCRYPT_MAXMEM,
    )
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${salt.hex()}${key.hex()}"


def verify_password(password: str, hashed_password: str) -> bool:
    """Xác minh mật khẩu bằng so sánh constant-time, chống timing attack."""
    try:
        parts = hashed_password.split("$")
        if len(parts) != 6 or parts[0] != "scrypt":
            return False
        n = int(parts[1])
        r = int(parts[2])
        p = int(parts[3])
        salt = bytes.fromhex(parts[4])
        expected_key = bytes.fromhex(parts[5])

        computed_key = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=n,
            r=r,
            p=p,
            maxmem=SCRYPT_MAXMEM,
        )
        return hmac.compare_digest(computed_key, expected_key)
    except Exception:
        return False

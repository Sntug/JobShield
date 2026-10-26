"""Canonical comparison values; these helpers never perform network lookups."""

import json
import re
import unicodedata
from email.errors import HeaderParseError
from email.headerregistry import Address
from urllib.parse import urlsplit, urlunsplit

FIELDS = ("company_name", "tax_id", "contact_email", "recruitment_website", "social_channel_url", "bank_account")
SOCIAL_HOSTS = {"t.me", "zalo.me", "facebook.com", "www.facebook.com", "m.facebook.com"}
# Shared hosting never proves ownership of a mailbox or social account.
SHARED_DOMAINS = SOCIAL_HOSTS | {"gmail.com", "googlemail.com", "outlook.com", "hotmail.com", "live.com", "yahoo.com", "icloud.com", "proton.me", "protonmail.com"}


def normalize_tax_id(value: str) -> str:
    if not re.fullmatch(r"[0-9]{10}(?:-?[0-9]{3})?", value):
        raise ValueError("Mã số thuế phải có 10 hoặc 13 chữ số.")
    return value.replace("-", "")


def normalize_email(value: str) -> str:
    try:
        address = Address(addr_spec=value)
    except (ValueError, HeaderParseError):
        raise ValueError("Email không đúng định dạng.") from None
    if not address.username or not address.domain or "." not in address.domain or any(ch.isspace() for ch in address.domain):
        raise ValueError("Email không đúng định dạng.")
    local, _, domain = value.rpartition("@")
    return local + "@" + domain.lower()


def normalize_url(value: str, *, social: bool = False) -> str:
    try:
        parts = urlsplit(value)
        if parts.scheme.lower() not in {"https", "http"} or not parts.hostname or parts.username is not None or parts.password is not None:
            raise ValueError
        if any(ch.isspace() or ord(ch) < 32 for ch in value) or "\\" in value:
            raise ValueError
        _ = parts.port
        host = parts.hostname.lower()
        if social and (host not in SOCIAL_HOSTS or not parts.path.strip("/")):
            raise ValueError
    except ValueError:
        raise ValueError("URL không đúng định dạng hoặc không thuộc kênh được hỗ trợ.") from None
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), parts.query, parts.fragment))


def canonical_value(field: str, value: str | dict) -> str:
    if field == "bank_account":
        return json.dumps(_normalized_bank(value), sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    value = unicodedata.normalize("NFC", value.strip())
    if field == "company_name":
        return " ".join(value.split()).casefold()
    if field == "tax_id":
        return normalize_tax_id(value)
    if field == "contact_email":
        return normalize_email(value)
    if field in {"recruitment_website", "social_channel_url"}:
        return normalize_url(value, social=field == "social_channel_url")
    if field == "domain":
        return value.lower()
    raise ValueError("Trường đối chiếu không được hỗ trợ.")


def claim_key(field: str, value: str | dict) -> str:
    """Bound indexed keys and keep raw identifiers out of the claim store (not encryption)."""
    from hashlib import sha256

    canonical = canonical_value(field, value)
    return sha256(canonical.encode()).hexdigest()


def lookup_keys(payload) -> list[tuple[str, str]]:
    keys = []
    for field, value in payload.model_dump(exclude_none=True).items():
        keys.append((field, claim_key(field, value)))
        domain = None
        if field == "contact_email":
            domain = value.rsplit("@", 1)[1]
        elif field == "recruitment_website":
            domain = urlsplit(value).hostname
        if domain and domain not in SHARED_DOMAINS:
            keys.append(("domain", claim_key("domain", domain)))
    return keys


def _normalized_bank(value: dict) -> dict:
    normalized = {key: " ".join(unicodedata.normalize("NFC", value[key]).split()).casefold() for key in ("account_number", "bank_name", "account_holder")}
    account = normalized["account_number"]
    if re.fullmatch(r"[0-9\s-]+", account) and re.search(r"[0-9]", account):
        normalized["account_number"] = re.sub(r"[\s-]+", "", account)
    return normalized


def bank_private_values(bank: dict) -> list[str]:
    if not bank:
        return []
    normalized = _normalized_bank(bank)
    return sorted({value for key in ("account_number", "account_holder") for value in (bank[key], normalized[key])}, key=len, reverse=True)

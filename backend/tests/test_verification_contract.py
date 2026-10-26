"""Contract validation only: all identifiers and bank values are synthetic."""

import pytest
from pydantic import ValidationError

from app.schemas.verifications import VerificationCreate


@pytest.mark.parametrize("payload", [{}, {"company_name": " \t"}, {"tax_id": None}, {"bank_account": {}}, {"bank_account": {"account_number": "", "bank_name": " ", "account_holder": ""}}])
def test_at_least_one_nonempty_value_required(payload):
    with pytest.raises(ValidationError):
        VerificationCreate.model_validate(payload)


@pytest.mark.parametrize("payload", [
    {"company_name": "Mẫu", "is_demo": True},
    {"company_name": "Mẫu", "sources": []},
    {"company_name": "Mẫu", "trusted": True},
    {"company_name": 123}, {"tax_id": 1234567890},
    {"tax_id": "01234567890"}, {"tax_id": "012345678901"},
    {"tax_id": "٠١٢٣٤٥٦٧٨٩"},
    {"contact_email": "Name <hr@mau.example>"},
    {"contact_email": "hr@mau.example, other@mau.example"},
    {"contact_email": "invalid"},
    {"recruitment_website": "javascript:alert(1)"},
    {"recruitment_website": "https://user:secret@mau.example"},
    {"recruitment_website": "https://[invalid"},
    {"social_channel_url": "https://facebook.com.attacker.example/profile"},
    {"social_channel_url": "https://t.me/"},
    {"bank_account": {"account_number": "0001"}},
    {"bank_account": {"account_number": "0001", "bank_name": "Test", "account_holder": "Test", "trusted": True}},
    {"company_name": "a" * 256},
])
def test_invalid_or_untrusted_payload_rejected(payload):
    with pytest.raises(ValidationError):
        VerificationCreate.model_validate(payload)


def test_tax_id_normalization_keeps_leading_zero():
    assert VerificationCreate(tax_id=" 0123456789-001 ").tax_id == "0123456789001"


def test_mailbox_local_part_and_url_path_are_preserved():
    payload = VerificationCreate(contact_email=" HR+Tag@MAU.EXAMPLE ", recruitment_website="https://MAU.EXAMPLE/Careers?ID=A")
    assert payload.contact_email == "HR+Tag@mau.example"
    assert payload.recruitment_website == "https://mau.example/Careers?ID=A"


def test_social_identity_query_is_preserved():
    value = "https://www.facebook.com/profile.php?id=12345"
    assert VerificationCreate(social_channel_url=value).social_channel_url == value


def test_bank_identifiers_remain_strings():
    payload = VerificationCreate(bank_account={"account_number": "0000001", "bank_name": "Test Bank", "account_holder": "NGUOI MAU"})
    assert payload.bank_account.account_number == "0000001"

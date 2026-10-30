"""Kiểm tra quy ước môi trường G1 bằng dữ liệu minh họa, không gọi DB."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_missing_database_url_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(ValidationError) as error:
        Settings(_env_file=None)

    assert error.value.errors()[0]["loc"] == ("DATABASE_URL",)
    assert error.value.errors()[0]["type"] == "missing"


def test_empty_database_url_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_database_url_is_loaded_without_exposing_password(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    example_url = "postgresql+psycopg://jobshield:example-password@localhost:5432/jobshield"
    monkeypatch.setenv("DATABASE_URL", example_url)

    settings = Settings(_env_file=None)

    assert settings.database_url.get_secret_value() == example_url
    assert "example-password" not in repr(settings)
    assert "example-password" not in settings.model_dump_json()


def test_ai_settings_default_and_secret_masking(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:pass@localhost:5432/db")
    settings = Settings(_env_file=None)
    assert settings.ai_provider == "none"
    assert settings.ai_api_key is None
    assert settings.ai_model == "gemini-2.5-flash"
    assert settings.ai_timeout_seconds == 10.0

    secret_key = "AIzaSySecretTestKey12345"
    monkeypatch.setenv("AI_PROVIDER", "gemini")
    monkeypatch.setenv("AI_API_KEY", secret_key)
    monkeypatch.setenv("AI_MODEL", "gemini-1.5-flash")
    settings_with_ai = Settings(_env_file=None)
    assert settings_with_ai.ai_provider == "gemini"
    assert settings_with_ai.ai_api_key is not None
    assert settings_with_ai.ai_api_key.get_secret_value() == secret_key
    assert secret_key not in repr(settings_with_ai)
    assert secret_key not in settings_with_ai.model_dump_json()

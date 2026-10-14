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

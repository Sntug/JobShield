"""Self-check dependency/import của G1; chưa kết nối API hoặc Database."""

import importlib

import pytest


@pytest.mark.parametrize(
    "module_name",
    [
        "fastapi",
        "pydantic",
        "pydantic_settings",
        "sqlalchemy",
        "alembic",
        "psycopg",
        "uvicorn",
        "httpx",
        "app.main",
    ],
)
def test_backend_dependency_can_be_imported(module_name: str) -> None:
    assert importlib.import_module(module_name).__name__ == module_name

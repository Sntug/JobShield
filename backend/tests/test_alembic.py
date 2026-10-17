"""Kiểm tra cấu hình Alembic trong R0.5."""

from alembic.config import Config
from alembic import command


def test_alembic_config_loads_and_runs_offline(capsys, monkeypatch) -> None:
    """Xác nhận cấu hình Alembic hợp lệ và sinh SQL offline không cần mạng."""
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:dummy@localhost:5432/postgres",
    )
    alembic_cfg = Config("alembic.ini")

    # Chạy upgrade head ở chế độ offline (sql=True)
    command.upgrade(alembic_cfg, "head", sql=True)
    captured = capsys.readouterr()

    assert "BEGIN;" in captured.out
    assert "COMMIT;" in captured.out

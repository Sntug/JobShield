"""Load synthetic sources only into explicitly named loopback E2E databases."""

from pathlib import Path
from sqlalchemy.engine import make_url

from app.core.config import Settings
from app.db.session import get_session_local
from app.cli.import_sources import SourceManifest, import_sources


def main():
    target = make_url(Settings().database_url.get_secret_value())
    if target.host not in {"127.0.0.1", "localhost"} or not (target.database or "").startswith(("jobshield_r12_e2e_", "jobshield_ci_e2e")):
        raise SystemExit("Từ chối seed: chỉ DB E2E local được đặt tên rõ ràng mới nhận fixture.")
    manifest = SourceManifest.model_validate_json((Path(__file__).parent / "fixtures/r12_e2e_sources.json").read_bytes())
    with get_session_local()() as db:
        import_sources(db, manifest)
    print("Đã nạp nguồn tổng hợp vào DB E2E cô lập.")


if __name__ == "__main__":
    main()

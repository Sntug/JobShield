"""Load synthetic sources only into explicitly named loopback E2E databases."""

from pathlib import Path
from datetime import datetime, timezone
from app.models.users import User, Role
from app.core.security import hash_password
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
        role = db.query(Role).filter_by(name="admin").first()
        if role is None:
            role = Role(name="admin")
            db.add(role)
            db.flush()
        if not db.query(User).filter_by(email="admin-r4-e2e@example.com").first():
            now = datetime.now(timezone.utc)
            db.add(User(role_id=role.id, email="admin-r4-e2e@example.com", password_hash=hash_password("synthetic_admin_password_2026"), full_name="DEMO E2E Admin", is_demo=True, created_at=now, updated_at=now))
        db.commit()
    print("Đã nạp nguồn tổng hợp vào DB E2E cô lập.")


if __name__ == "__main__":
    main()

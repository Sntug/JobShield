"""Real PostgreSQL migration, indexed claims, FK isolation and HTTP snapshot checks."""

from pathlib import Path
import uuid

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import IntegrityError

from app.main import app
from app.models.verifications import VerifiedEmployer, EmployerClaim
from app.schemas.verifications import VerificationCreate
from app.services.verification_store import load_employers
from app.services.verification_values import claim_key
from tests.test_postgres_integration import postgres_engine, isolated_schema, run_alembic_migrations, pg_db
from tests.test_verification_store import add_employer


def test_real_store_constraints_api_and_snapshot(pg_db):
    company, source = add_employer(pg_db, tax_id="0000000301")
    records = load_employers(pg_db, VerificationCreate(tax_id="0000000301"))
    assert [record["id"] for record in records] == [str(company.id)]
    other = VerifiedEmployer(legal_name="Công ty khác", tax_id="0000000302")
    pg_db.add(other)
    pg_db.commit()
    with pytest.raises(IntegrityError):
        with pg_db.begin_nested():
            pg_db.add(EmployerClaim(employer_id=other.id, source_id=source.id, field="tax_id", value_key=claim_key("tax_id", "0000000302"), assertion="supports"))
            pg_db.flush()
    inspector = inspect(pg_db.connection())
    assert "ix_employer_claims_lookup" in {item["name"] for item in inspector.get_indexes("employer_claims")}
    with TestClient(app) as client:
        result = client.post("/api/v1/verifications", json={"tax_id": "0000000301"})
        assert result.status_code == 200
        assert result.json()["verification_label_vi"] == "Khớp nguồn đã xác minh"
        snapshot = client.post("/api/v1/analyses", json={"text": "Công ty Mẫu tuyển Tester. Lương: 8 triệu đồng/tháng. Email: HR@mau.example."}).json()
        assert snapshot["verification_label_vi"] == "Khớp nguồn đã xác minh"
        source.is_active = False
        source.source_revision += 1
        pg_db.commit()
        reread = client.get(f"/api/v1/analyses/{snapshot['id']}", headers={"X-Guest-Session-Token": snapshot["guest_session_token"]}).json()
        assert reread["evidence"] == snapshot["evidence"]
        assert client.post("/api/v1/verifications", json={"tax_id": "0000000301"}).json()["verification_label_vi"] == "Chưa xác minh"


def test_migration_round_trip_keeps_r11_tables(postgres_engine, isolated_schema):
    cfg = Config(str(Path(__file__).parent.parent / "alembic.ini"))
    with postgres_engine.connect() as conn:
        conn.execute(text(f'SET search_path TO "{isolated_schema}"'))
        cfg.attributes["connection"] = conn
        cfg.attributes["version_table_schema"] = isolated_schema
        before = conn.execute(text("SELECT count(*) FROM analyses")).scalar_one()
        command.downgrade(cfg, "f0c67067b2b0")
        conn.commit()
        assert "verification_sources" not in inspect(conn).get_table_names(schema=isolated_schema)
        assert conn.execute(text("SELECT count(*) FROM analyses")).scalar_one() == before
        command.upgrade(cfg, "head")
        conn.commit()
        assert {"verified_employers", "verification_sources", "employer_claims"} <= set(inspect(conn).get_table_names(schema=isolated_schema))

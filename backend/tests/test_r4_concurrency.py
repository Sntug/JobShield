"""R4 write conflicts against migrated PostgreSQL; CI must run these."""
from sqlalchemy.orm import sessionmaker
from app.models.users import User, Role
from tests.test_account_concurrency import pg_client, account, simultaneous_requests
from tests.test_postgres_integration import postgres_engine, isolated_schema, run_alembic_migrations


def admin_account(client, engine):
    payload, headers = account(client)
    with sessionmaker(bind=engine)() as db:
        user = db.query(User).filter_by(email=payload["email"]).one()
        role = db.query(Role).filter_by(name="admin").first()
        if role is None:
            role = Role(name="admin")
            db.add(role)
            db.flush()
        user.role_id = role.id
        db.commit()
    return headers


def test_report_concurrent_decisions_have_one_winner(pg_client):
    client, engine = pg_client
    headers = admin_account(client, engine)
    report = client.post("/api/v1/reports", headers=headers, json={"reason": "Fees", "description": "Concurrent report decisions"}).json()
    def decide():
        return client.post(f"/api/v1/admin/reports/{report['id']}/moderation", headers=headers, json={"action_type": "verify", "to_status": "verified", "decision_summary": "Evidence reviewed", "expected_version": 1})
    results = simultaneous_requests(engine, "FROM recruitment_reports", decide)
    assert sorted(r.status_code for r in results) == [200, 409]
    detail = client.get(f"/api/v1/admin/reports/{report['id']}", headers=headers).json()
    assert detail["version"] == 2
    assert len(detail["moderation_actions"]) == 1


def test_warning_withdraw_cannot_race_supersede(pg_client):
    client, engine = pg_client
    headers = admin_account(client, engine)
    payload = {"title_vi": "Concurrent warning", "public_summary_vi": "Reviewed public content for a warning", "public_sources_snapshot": [{"url": "https://example.com/evidence", "label_vi": "Reviewed source"}]}
    warning = client.post("/api/v1/admin/warnings", headers=headers, json=payload).json()
    # Use the same synchronized helper for two competing operations.
    from threading import Lock
    lock = Lock()
    calls = 0
    def transition():
        nonlocal calls
        with lock:
            calls += 1
            supersede = calls == 1
        path = f"/api/v1/admin/warnings/{warning['id']}/"
        return client.post(path + ("supersede" if supersede else "withdraw"), headers=headers, json=payload if supersede else {"withdrawal_reason_vi": "Evidence is incorrect; withdraw immediately"})
    results = simultaneous_requests(engine, "FROM public_warnings", transition)
    assert sorted(r.status_code for r in results) == [200, 409]

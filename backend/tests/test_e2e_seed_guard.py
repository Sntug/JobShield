import pytest
from tests import seed_r12_e2e


@pytest.mark.parametrize("url", ["postgresql+psycopg://u:p@db.remote.example/jobshield_ci_e2e", "postgresql+psycopg://u:p@localhost/production"])
def test_e2e_seed_rejects_remote_or_non_e2e_database(monkeypatch, url):
    monkeypatch.setenv("DATABASE_URL", url)
    with pytest.raises(SystemExit, match="Từ chối seed"):
        seed_r12_e2e.main()

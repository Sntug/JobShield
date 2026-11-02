"""Opt-in PostgreSQL archive restore test using only disposable synthetic databases."""

import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import uuid

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
CONTAINER = "jobshield-test-pg"
RUN_PG_TEST = os.getenv("RUN_RESTORE_DRILL_PG_TEST") == "1"


def docker_psql(database, sql, *, check=True):
    result = subprocess.run(
        [
            "docker", "exec", "--user", "postgres", "-i", CONTAINER,
            "psql", "-U", "r11_review", "-X", "-qAt", "-v", "ON_ERROR_STOP=1", "-d", database, "-c", sql,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if check and result.returncode:
        pytest.fail(result.stderr or result.stdout)
    return result


@pytest.mark.skipif(not RUN_PG_TEST, reason="Set RUN_RESTORE_DRILL_PG_TEST=1 for the disposable PostgreSQL integration test.")
def test_pg_dump_archive_restores_data_foreign_keys_and_rls():
    if not shutil.which("docker"):
        pytest.fail("RUN_RESTORE_DRILL_PG_TEST=1 requires Docker; refusing to skip the configured integration test.")

    suffix = uuid.uuid4().hex[:12]
    source_db = f"jobshield_restore_src_{suffix}"
    probe_role = f"jobshield_rls_probe_{suffix}"
    target_db = None
    created_databases = []
    created_role = False

    try:
        docker_psql("postgres", f'CREATE ROLE "{probe_role}" NOLOGIN;')
        created_role = True
        docker_psql("postgres", f'CREATE DATABASE "{source_db}";')
        created_databases.append(source_db)
        docker_psql(
            source_db,
            f"""
            CREATE TABLE public.analyses (
                id integer PRIMARY KEY,
                details text NOT NULL,
                owner_name text NOT NULL
            );
            ALTER TABLE public.analyses ENABLE ROW LEVEL SECURITY;
            CREATE POLICY analyses_owner_select ON public.analyses
                FOR SELECT USING (owner_name = CURRENT_USER);
            CREATE TABLE public.verified_employers (id text PRIMARY KEY, legal_name text NOT NULL);
            CREATE TABLE public.risk_indicators (id integer PRIMARY KEY, label text NOT NULL);
            CREATE TABLE public.employer_claims (
                id integer PRIMARY KEY,
                employer_id text NOT NULL REFERENCES public.verified_employers(id)
            );
            INSERT INTO public.analyses VALUES
                (1, 'visible synthetic record', '{probe_role}'),
                (2, 'hidden synthetic record', 'another-owner');
            INSERT INTO public.verified_employers VALUES ('synthetic-employer', 'Synthetic Employer');
            INSERT INTO public.risk_indicators VALUES (1, 'synthetic-indicator');
            INSERT INTO public.employer_claims VALUES (1, 'synthetic-employer');
            """,
        )

        with tempfile.TemporaryDirectory(prefix="jobshield_drill_test.") as temp_dir:
            verification_file = Path(temp_dir) / "restore-verification.txt"
            shell_driver = r'''
source "$1"
{
  printf 'analysis_rows='
  psql_db "$TARGET_DRILL_DB" "SELECT string_agg(id || ':' || details, ',' ORDER BY id) FROM public.analyses;"
  printf 'employer_rows='
  psql_db "$TARGET_DRILL_DB" "SELECT string_agg(id || ':' || legal_name, ',' ORDER BY id) FROM public.verified_employers;"
  printf 'indicator_rows='
  psql_db "$TARGET_DRILL_DB" "SELECT string_agg(id || ':' || label, ',' ORDER BY id) FROM public.risk_indicators;"
  printf 'fk_count='
  psql_db "$TARGET_DRILL_DB" "SELECT COUNT(*) FROM pg_constraint WHERE contype = 'f' AND conrelid = 'public.employer_claims'::regclass;"
  printf 'orphan_count='
  psql_db "$TARGET_DRILL_DB" "SELECT COUNT(*) FROM public.employer_claims ec LEFT JOIN public.verified_employers ve ON ve.id = ec.employer_id WHERE ve.id IS NULL;"
  printf 'rls_enabled='
  psql_db "$TARGET_DRILL_DB" "SELECT relrowsecurity::text || ':' || relforcerowsecurity::text FROM pg_class WHERE oid = 'public.analyses'::regclass;"
  printf 'policy='
  psql_db "$TARGET_DRILL_DB" "SELECT policyname || ':' || cmd || ':' || COALESCE(qual, '') FROM pg_policies WHERE schemaname = 'public' AND tablename = 'analyses';"
  printf 'rls_visible='
  psql_db "$TARGET_DRILL_DB" "GRANT USAGE ON SCHEMA public TO \"$RESTORE_DRILL_RLS_ROLE\"; GRANT SELECT ON public.analyses TO \"$RESTORE_DRILL_RLS_ROLE\"; SET ROLE \"$RESTORE_DRILL_RLS_ROLE\"; SELECT string_agg(details, ',' ORDER BY id) FROM public.analyses;"
  if psql_db "$TARGET_DRILL_DB" "INSERT INTO public.employer_claims VALUES (999, 'missing-employer');"; then
    echo 'foreign_key_enforced=false'
    exit 1
  fi
  echo 'foreign_key_enforced=true'
} > "$2"
'''
            env = {
                **os.environ,
                "SOURCE_DB": source_db,
                "RESTORE_DRILL_RLS_ROLE": probe_role,
                "TMPDIR": temp_dir,
            }
            result = subprocess.run(
                ["bash", "-c", shell_driver, "restore-drill-test", str(REPO_ROOT / "scripts/restore-drill.sh"), str(verification_file)],
                cwd=REPO_ROOT,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            match = re.search(r"Target Isolated DB: ([A-Za-z0-9_]+)", result.stdout)
            target_db = match.group(1) if match else None
            assert result.returncode == 0, result.stderr + result.stdout
            assert target_db is not None

            report = dict(line.split("=", 1) for line in verification_file.read_text(encoding="utf-8").splitlines())
            assert report == {
                "analysis_rows": "1:visible synthetic record,2:hidden synthetic record",
                "employer_rows": "synthetic-employer:Synthetic Employer",
                "indicator_rows": "1:synthetic-indicator",
                "fk_count": "1",
                "orphan_count": "0",
                "rls_enabled": "true:false",
                "policy": "analyses_owner_select:SELECT:(owner_name = CURRENT_USER)",
                "rls_visible": "visible synthetic record",
                "foreign_key_enforced": "true",
            }
            assert not list(Path(temp_dir).glob("jobshield_drill.*"))

        assert docker_psql("postgres", f"SELECT COUNT(*) FROM pg_database WHERE datname = '{target_db}';").stdout.strip() == "0"
    finally:
        if target_db:
            exists = docker_psql("postgres", f"SELECT 1 FROM pg_database WHERE datname = '{target_db}';", check=False)
            if exists.returncode == 0 and exists.stdout.strip() == "1":
                docker_psql("postgres", f'DROP DATABASE "{target_db}";', check=False)
        for database in reversed(created_databases):
            docker_psql("postgres", f'DROP DATABASE "{database}";', check=False)
        if created_role:
            docker_psql("postgres", f'DROP ROLE "{probe_role}";', check=False)

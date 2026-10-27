"""Keep backend-managed tables private from Supabase Data API roles.

Revision ID: d7a8b9c0e1f2
Revises: c4d5e6f7a8b9
"""
from alembic import op


revision = 'd7a8b9c0e1f2'
down_revision = 'c4d5e6f7a8b9'
branch_labels = None
depends_on = None

TABLES = (
    'roles', 'users', 'access_sessions', 'saved_analyses', 'guest_sessions',
    'analyses', 'verified_employers', 'verification_sources', 'employer_claims',
    'alembic_version',
)


def upgrade():
    for table in TABLES:
        # FastAPI connects as the table owner; browser API roles must have no direct access.
        op.execute(f'ALTER TABLE {table} ENABLE ROW LEVEL SECURITY')
        op.execute(f"""
            DO $privacy$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                    REVOKE ALL PRIVILEGES ON TABLE {table} FROM anon;
                END IF;
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
                    REVOKE ALL PRIVILEGES ON TABLE {table} FROM authenticated;
                END IF;
            END
            $privacy$;
        """)


def downgrade():
    # Reverting application code must never reopen private tables to the Data API.
    pass

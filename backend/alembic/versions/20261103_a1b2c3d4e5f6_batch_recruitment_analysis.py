"""Batch recruitment analysis tables.

Revision ID: a1b2c3d4e5f6
Revises: f9a0b1c2d3e4
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'f9a0b1c2d3e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES = ('batch_analyses', 'batch_analysis_items')


def upgrade() -> None:
    op.create_table(
        'batch_analyses',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('session_id', sa.Uuid(), nullable=True),
        sa.Column('user_id', sa.Uuid(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('total_items', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('processed_items', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['guest_sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint(
            '(session_id IS NOT NULL AND user_id IS NULL) OR (session_id IS NULL AND user_id IS NOT NULL)',
            name='ck_batch_owner',
        ),
        sa.CheckConstraint(
            '(user_id IS NOT NULL AND expires_at IS NULL) OR (session_id IS NOT NULL AND expires_at IS NOT NULL)',
            name='ck_batch_expiry',
        ),
    )
    op.create_index(op.f('ix_batch_analyses_session_id'), 'batch_analyses', ['session_id'], unique=False)
    op.create_index(op.f('ix_batch_analyses_user_id'), 'batch_analyses', ['user_id'], unique=False)
    op.create_index(op.f('ix_batch_analyses_expires_at'), 'batch_analyses', ['expires_at'], unique=False)

    op.create_table(
        'batch_analysis_items',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('batch_id', sa.Uuid(), nullable=False),
        sa.Column('item_order', sa.Integer(), nullable=False),
        sa.Column('input_type', sa.String(length=10), nullable=False),
        sa.Column('input_value', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('analysis_id', sa.Uuid(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_code', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['batch_id'], ['batch_analyses.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['analysis_id'], ['analyses.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_batch_analysis_items_batch_id'), 'batch_analysis_items', ['batch_id'], unique=False)
    op.create_index(op.f('ix_batch_analysis_items_analysis_id'), 'batch_analysis_items', ['analysis_id'], unique=False)

    for table in TABLES:
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


def downgrade() -> None:
    op.drop_index(op.f('ix_batch_analysis_items_analysis_id'), table_name='batch_analysis_items')
    op.drop_index(op.f('ix_batch_analysis_items_batch_id'), table_name='batch_analysis_items')
    op.drop_table('batch_analysis_items')
    op.drop_index(op.f('ix_batch_analyses_expires_at'), table_name='batch_analyses')
    op.drop_index(op.f('ix_batch_analyses_user_id'), table_name='batch_analyses')
    op.drop_index(op.f('ix_batch_analyses_session_id'), table_name='batch_analyses')
    op.drop_table('batch_analyses')

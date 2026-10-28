"""R2 accounts, access sessions, and saved analyses.

Revision ID: c4d5e6f7a8b9
Revises: 71b91d2c6a40
"""
from typing import Sequence, Union
import uuid
from alembic import op
import sqlalchemy as sa


revision: str = 'c4d5e6f7a8b9'
down_revision: Union[str, None] = '71b91d2c6a40'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. roles
    roles_table = op.create_table(
        'roles',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('name', sa.String(50), nullable=False),
        sa.Column('description', sa.String(255), nullable=True),
    )
    op.create_index(op.f('ix_roles_name'), 'roles', ['name'], unique=True)

    # Seed default roles
    op.bulk_insert(
        roles_table,
        [
            {'id': uuid.uuid4(), 'name': 'user', 'description': 'Người dùng thông thường'},
            {'id': uuid.uuid4(), 'name': 'admin', 'description': 'Quản trị viên'},
        ],
    )

    # 2. users
    op.create_table(
        'users',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('role_id', sa.Uuid(), sa.ForeignKey('roles.id'), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=False),
        sa.Column('is_demo', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('anonymized_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # 3. access_sessions
    op.create_table(
        'access_sessions',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('user_id', sa.Uuid(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('token_hash', sa.String(64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(op.f('ix_access_sessions_token_hash'), 'access_sessions', ['token_hash'], unique=True)
    op.create_index(op.f('ix_access_sessions_user_id'), 'access_sessions', ['user_id'], unique=False)
    op.create_index(op.f('ix_access_sessions_expires_at'), 'access_sessions', ['expires_at'], unique=False)

    # 4. update analyses
    op.alter_column('analyses', 'session_id', existing_type=sa.Uuid(), nullable=True)
    op.alter_column('analyses', 'expires_at', existing_type=sa.DateTime(timezone=True), nullable=True)
    op.add_column(
        'analyses',
        sa.Column('user_id', sa.Uuid(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=True),
    )
    op.create_index(op.f('ix_analyses_user_id'), 'analyses', ['user_id'], unique=False)
    op.create_check_constraint(
        'ck_analysis_owner',
        'analyses',
        '(session_id IS NOT NULL AND user_id IS NULL) OR (session_id IS NULL AND user_id IS NOT NULL)',
    )
    op.create_check_constraint(
        'ck_analysis_expiry',
        'analyses',
        '(user_id IS NOT NULL AND expires_at IS NULL) OR (session_id IS NOT NULL AND expires_at IS NOT NULL)',
    )

    # 5. saved_analyses
    op.create_table(
        'saved_analyses',
        sa.Column('user_id', sa.Uuid(), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('analysis_id', sa.Uuid(), sa.ForeignKey('analyses.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('saved_at', sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('saved_analyses')
    op.drop_constraint('ck_analysis_expiry', 'analyses', type_='check')
    op.drop_constraint('ck_analysis_owner', 'analyses', type_='check')
    op.drop_index(op.f('ix_analyses_user_id'), table_name='analyses')
    op.drop_column('analyses', 'user_id')
    op.alter_column('analyses', 'expires_at', existing_type=sa.DateTime(timezone=True), nullable=False)
    op.alter_column('analyses', 'session_id', existing_type=sa.Uuid(), nullable=False)
    op.drop_index(op.f('ix_access_sessions_expires_at'), table_name='access_sessions')
    op.drop_index(op.f('ix_access_sessions_user_id'), table_name='access_sessions')
    op.drop_index(op.f('ix_access_sessions_token_hash'), table_name='access_sessions')
    op.drop_table('access_sessions')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
    op.drop_index(op.f('ix_roles_name'), table_name='roles')
    op.drop_table('roles')

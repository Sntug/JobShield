"""R5 optional AI semantic analysis insights.

Revision ID: f9a0b1c2d3e4
Revises: e8f9a0b1c2d3
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'f9a0b1c2d3e4'
down_revision: Union[str, None] = 'e8f9a0b1c2d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('analyses', sa.Column('ai_insights', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('analyses', 'ai_insights')

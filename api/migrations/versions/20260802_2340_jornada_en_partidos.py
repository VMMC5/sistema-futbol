"""jornada en partidos

Revision ID: e5f6a7b8c9d0
Revises: d3f4a5b6c7e8
Create Date: 2026-08-02 23:40:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, None] = "d3f4a5b6c7e8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("partidos", sa.Column("jornada", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("partidos", "jornada")

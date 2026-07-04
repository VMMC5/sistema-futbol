"""pagos: concepto y completado_en

Revision ID: 20260703_1000
Revises: 3b5c9804c2e3
Create Date: 2026-07-03
"""
from alembic import op
import sqlalchemy as sa


revision = "20260703_1000"
down_revision = "3b5c9804c2e3"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("pagos", sa.Column("concepto", sa.String(length=160), nullable=True))
    op.add_column("pagos", sa.Column("completado_en", sa.DateTime(timezone=True), nullable=True))


def downgrade():
    op.drop_column("pagos", "completado_en")
    op.drop_column("pagos", "concepto")

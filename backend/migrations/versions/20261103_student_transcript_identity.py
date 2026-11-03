"""Add student identity fields required by academic transcript schemas.

Revision ID: 20261103identity
Revises: 20261103credit
Create Date: 2026-11-03
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261103identity"
down_revision: Union[str, Sequence[str], None] = "20261103credit"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("students", sa.Column("social_name", sa.String(length=160), nullable=True))
    op.add_column("students", sa.Column("sex", sa.String(length=40), nullable=True))
    op.add_column("students", sa.Column("nationality", sa.String(length=100), nullable=True))
    op.add_column("students", sa.Column("birthplace_municipality_code", sa.String(length=10), nullable=True))
    op.add_column("students", sa.Column("birthplace_municipality_name", sa.String(length=120), nullable=True))
    op.add_column("students", sa.Column("birthplace_state", sa.String(length=2), nullable=True))
    op.add_column("students", sa.Column("rg_number", sa.String(length=30), nullable=True))
    op.add_column("students", sa.Column("rg_issuing_authority", sa.String(length=40), nullable=True))
    op.add_column("students", sa.Column("rg_state", sa.String(length=2), nullable=True))


def downgrade() -> None:
    for column in (
        "rg_state",
        "rg_issuing_authority",
        "rg_number",
        "birthplace_state",
        "birthplace_municipality_name",
        "birthplace_municipality_code",
        "nationality",
        "sex",
        "social_name",
    ):
        op.drop_column("students", column)

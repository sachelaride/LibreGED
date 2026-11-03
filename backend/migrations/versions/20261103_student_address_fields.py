"""Add structured address fields to students and guardians.

Revision ID: 20261103address
Revises: 20261102student
Create Date: 2026-11-03
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261103address"
down_revision: Union[str, Sequence[str], None] = "20261102student"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for table in ("students", "guardians"):
        op.add_column(table, sa.Column("address_street", sa.String(length=160), nullable=True))
        op.add_column(table, sa.Column("address_number", sa.String(length=20), nullable=True))
        op.add_column(table, sa.Column("address_complement", sa.String(length=120), nullable=True))
        op.add_column(table, sa.Column("address_neighborhood", sa.String(length=120), nullable=True))
        op.add_column(table, sa.Column("address_city", sa.String(length=120), nullable=True))
        op.add_column(table, sa.Column("address_state", sa.String(length=2), nullable=True))
        op.add_column(table, sa.Column("address_postal_code", sa.String(length=12), nullable=True))


def downgrade() -> None:
    columns = (
        "address_postal_code",
        "address_state",
        "address_city",
        "address_neighborhood",
        "address_complement",
        "address_number",
        "address_street",
    )
    for table in ("guardians", "students"):
        for column in columns:
            op.drop_column(table, column)

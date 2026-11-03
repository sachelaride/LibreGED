"""Add phone contact fields to students and guardians.

Revision ID: 20261102student
Revises: 20261101acad
Create Date: 2026-11-02
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261102student"
down_revision: Union[str, Sequence[str], None] = "20261101acad"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("students", sa.Column("phone", sa.String(length=32), nullable=True))
    op.add_column("guardians", sa.Column("phone", sa.String(length=32), nullable=True))


def downgrade() -> None:
    op.drop_column("guardians", "phone")
    op.drop_column("students", "phone")

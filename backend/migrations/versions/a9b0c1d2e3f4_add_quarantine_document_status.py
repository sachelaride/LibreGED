"""add quarantine document status

Revision ID: a9b0c1d2e3f4
Revises: f7a8b9c0d1e2
Create Date: 2026-09-15 12:35:00
"""
from typing import Sequence, Union

from alembic import op


revision: str = "a9b0c1d2e3f4"
down_revision: Union[str, Sequence[str], None] = "f7a8b9c0d1e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TYPE geddocumentstatus ADD VALUE IF NOT EXISTS 'QUARENTENA'"
    )


def downgrade() -> None:
    # PostgreSQL does not safely remove enum values while dependent columns exist.
    pass

"""Add faculty qualification data for academic transcripts.

Revision ID: 20261103staffhist
Revises: 20261103entry
Create Date: 2026-11-03
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261103staffhist"
down_revision: Union[str, Sequence[str], None] = "20261103entry"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "academic_staff",
        sa.Column("transcript_title", sa.String(length=40), nullable=True),
    )
    op.add_column(
        "academic_staff",
        sa.Column("transcript_cpf", sa.String(length=11), nullable=True),
    )
    op.add_column(
        "academic_staff",
        sa.Column("transcript_lattes", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("academic_staff", "transcript_lattes")
    op.drop_column("academic_staff", "transcript_cpf")
    op.drop_column("academic_staff", "transcript_title")

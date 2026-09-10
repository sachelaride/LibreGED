"""Add optional storage links to document types

Revision ID: 7b3d2b8c1a4f
Revises: 64432ae7387b
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7b3d2b8c1a4f"
down_revision: Union[str, Sequence[str], None] = "64432ae7387b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("ged_document_types", sa.Column("storage_area_id", sa.String(), nullable=True))
    op.add_column("ged_document_types", sa.Column("storage_partition_id", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("ged_document_types", "storage_partition_id")
    op.drop_column("ged_document_types", "storage_area_id")

"""Persist SHA-256 hashes for GED documents.

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d3e4f5a6b7c8"
down_revision: Union[str, Sequence[str], None] = "c2d3e4f5a6b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("ged_documents", sa.Column("file_hash", sa.String(length=64), nullable=True))
    op.create_index("ix_ged_documents_file_hash", "ged_documents", ["file_hash"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_ged_documents_file_hash", table_name="ged_documents")
    op.drop_column("ged_documents", "file_hash")

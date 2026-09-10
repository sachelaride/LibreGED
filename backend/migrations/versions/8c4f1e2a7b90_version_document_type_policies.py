"""Version document type policies

Revision ID: 8c4f1e2a7b90
Revises: 7b3d2b8c1a4f
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "8c4f1e2a7b90"
down_revision: Union[str, Sequence[str], None] = "7b3d2b8c1a4f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("ged_document_types", sa.Column("access_policy", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")))
    op.add_column("ged_document_types", sa.Column("signature_rule", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")))
    op.add_column("ged_document_types", sa.Column("active_version", sa.Integer(), nullable=False, server_default="1"))
    op.create_table(
        "ged_document_type_versions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("document_type_id", sa.String(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("workflow_id", sa.String(), nullable=True),
        sa.Column("group_id", sa.String(), nullable=True),
        sa.Column("retention_years", sa.Integer(), nullable=False),
        sa.Column("legal_hold", sa.Boolean(), nullable=False),
        sa.Column("access_policy", postgresql.JSONB(), nullable=False),
        sa.Column("signature_rule", postgresql.JSONB(), nullable=False),
        sa.Column("effective_from", sa.DateTime(), nullable=True),
        sa.Column("effective_until", sa.DateTime(), nullable=True),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["document_type_id"], ["ged_document_types.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_type_id", "version", name="uq_document_type_version"),
    )
    op.create_index("ix_ged_document_type_versions_document_type_id", "ged_document_type_versions", ["document_type_id"])


def downgrade() -> None:
    op.drop_index("ix_ged_document_type_versions_document_type_id", table_name="ged_document_type_versions")
    op.drop_table("ged_document_type_versions")
    op.drop_column("ged_document_types", "active_version")
    op.drop_column("ged_document_types", "signature_rule")
    op.drop_column("ged_document_types", "access_policy")

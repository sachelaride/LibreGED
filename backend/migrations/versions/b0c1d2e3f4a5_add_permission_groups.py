"""add permission groups and explicit denials

Revision ID: b0c1d2e3f4a5
Revises: a9b0c1d2e3f4
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "b0c1d2e3f4a5"
down_revision: Union[str, Sequence[str], None] = "a9b0c1d2e3f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("ged_user_document_types", sa.Column(
        "denied_permissions", postgresql.JSONB(), nullable=False, server_default="[]"
    ))
    op.create_table(
        "ged_permission_groups",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("institution_id", sa.String(), nullable=False),
        sa.Column("parent_group_id", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"]),
        sa.ForeignKeyConstraint(["parent_group_id"], ["ged_permission_groups.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("institution_id", "name", name="uq_permission_group_institution_name"),
    )
    op.create_index("ix_ged_permission_groups_institution_id", "ged_permission_groups", ["institution_id"])
    op.create_table(
        "ged_permission_group_members",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("group_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["group_id"], ["ged_permission_groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("group_id", "user_id", name="uq_permission_group_member"),
    )
    op.create_index("ix_ged_permission_group_members_group_id", "ged_permission_group_members", ["group_id"])
    op.create_index("ix_ged_permission_group_members_user_id", "ged_permission_group_members", ["user_id"])
    op.create_table(
        "ged_permission_group_document_types",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("group_id", sa.String(), nullable=False),
        sa.Column("document_type_id", sa.String(), nullable=False),
        sa.Column("permissions", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("denied_permissions", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["group_id"], ["ged_permission_groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_type_id"], ["ged_document_types.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("group_id", "document_type_id", name="uq_permission_group_document_type"),
    )
    op.create_index("ix_ged_permission_group_document_types_group_id", "ged_permission_group_document_types", ["group_id"])
    op.create_index("ix_ged_permission_group_document_types_document_type_id", "ged_permission_group_document_types", ["document_type_id"])


def downgrade() -> None:
    op.drop_table("ged_permission_group_document_types")
    op.drop_table("ged_permission_group_members")
    op.drop_table("ged_permission_groups")
    op.drop_column("ged_user_document_types", "denied_permissions")

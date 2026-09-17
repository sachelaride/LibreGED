"""Align workflow and ECM columns with the SQLAlchemy models.

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "c2d3e4f5a6b7"
down_revision: Union[str, Sequence[str], None] = "b1c2d3e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "ecm_node_permissions",
        "permissions",
        existing_type=sa.JSON(),
        type_=postgresql.JSONB(),
        postgresql_using="permissions::jsonb",
    )
    op.create_index(
        "ix_ged_permission_groups_parent_group_id",
        "ged_permission_groups",
        ["parent_group_id"],
        unique=False,
    )
    op.add_column(
        "ged_workflow_tasks",
        sa.Column("assignee_group_id", sa.String(), nullable=True),
    )
    op.add_column(
        "ged_workflow_tasks",
        sa.Column("assignee_role", sa.String(), nullable=True),
    )
    op.alter_column(
        "ged_workflow_tasks",
        "assignee_id",
        existing_type=sa.String(),
        nullable=True,
    )
    op.create_index(
        "ix_ged_workflow_tasks_assignee_group_id",
        "ged_workflow_tasks",
        ["assignee_group_id"],
        unique=False,
    )
    op.create_index(
        "ix_ged_workflow_tasks_assignee_role",
        "ged_workflow_tasks",
        ["assignee_role"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_ged_workflow_tasks_assignee_role",
        table_name="ged_workflow_tasks",
    )
    op.drop_index(
        "ix_ged_workflow_tasks_assignee_group_id",
        table_name="ged_workflow_tasks",
    )
    op.alter_column(
        "ged_workflow_tasks",
        "assignee_id",
        existing_type=sa.String(),
        nullable=False,
    )
    op.drop_column("ged_workflow_tasks", "assignee_role")
    op.drop_column("ged_workflow_tasks", "assignee_group_id")
    op.drop_index(
        "ix_ged_permission_groups_parent_group_id",
        table_name="ged_permission_groups",
    )
    op.alter_column(
        "ecm_node_permissions",
        "permissions",
        existing_type=postgresql.JSONB(),
        type_=sa.JSON(),
        postgresql_using="permissions::json",
    )

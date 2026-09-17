"""Add workflow versions and executable node configuration."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, Sequence[str], None] = "d3e4f5a6b7c8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ged_workflow_states", sa.Column("config_json", sa.Text(), nullable=True))
    op.create_table(
        "ged_workflow_versions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("workflow_id", sa.String(), sa.ForeignKey("ged_workflows.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="DRAFT"),
        sa.Column("snapshot_json", sa.Text(), nullable=False),
        sa.Column("created_by_user_id", sa.String(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("workflow_id", "version_number", name="uq_workflow_version_number"),
    )
    op.create_index("ix_ged_workflow_versions_workflow_id", "ged_workflow_versions", ["workflow_id"])


def downgrade() -> None:
    op.drop_index("ix_ged_workflow_versions_workflow_id", table_name="ged_workflow_versions")
    op.drop_table("ged_workflow_versions")
    op.drop_column("ged_workflow_states", "config_json")

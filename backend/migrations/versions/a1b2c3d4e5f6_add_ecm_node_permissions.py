"""Add granular permissions for ECM nodes."""

from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e5f6"
down_revision = "f0a1b2c3d4e5"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ecm_node_permissions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("node_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=True),
        sa.Column("site_id", sa.String(), nullable=True),
        sa.Column("permissions", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["node_id"], ["ecm_nodes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["site_id"], ["ecm_sites.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_ecm_node_permissions_node_id", "ecm_node_permissions", ["node_id"])
    op.create_index("ix_ecm_node_permissions_user_id", "ecm_node_permissions", ["user_id"])
    op.create_index("ix_ecm_node_permissions_site_id", "ecm_node_permissions", ["site_id"])


def downgrade():
    op.drop_index("ix_ecm_node_permissions_site_id", table_name="ecm_node_permissions")
    op.drop_index("ix_ecm_node_permissions_user_id", table_name="ecm_node_permissions")
    op.drop_index("ix_ecm_node_permissions_node_id", table_name="ecm_node_permissions")
    op.drop_table("ecm_node_permissions")

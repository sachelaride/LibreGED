"""Add declarative workflow gateway conditions."""

from alembic import op
import sqlalchemy as sa


revision = "f7a8b9c0d1e2"
down_revision = "e6f7a8b9c0d1"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("ged_workflow_transitions", sa.Column("condition_key", sa.String(), nullable=True))
    op.add_column("ged_workflow_transitions", sa.Column("condition_value", sa.String(), nullable=True))
    op.add_column("ged_workflow_transitions", sa.Column("priority", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("ged_workflow_transitions", sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade():
    op.drop_column("ged_workflow_transitions", "is_default")
    op.drop_column("ged_workflow_transitions", "priority")
    op.drop_column("ged_workflow_transitions", "condition_value")
    op.drop_column("ged_workflow_transitions", "condition_key")

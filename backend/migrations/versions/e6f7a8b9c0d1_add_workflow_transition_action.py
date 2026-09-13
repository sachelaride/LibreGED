"""Add action code and route uniqueness to workflow transitions."""

from alembic import op
import sqlalchemy as sa


revision = "e6f7a8b9c0d1"
down_revision = "d5e6f7a8b9c0"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("ged_workflow_transitions", sa.Column("action_code", sa.String(), nullable=True))
    op.create_unique_constraint(
        "uq_workflow_transition_route",
        "ged_workflow_transitions",
        ["workflow_id", "origin_state_id", "destination_state_id"],
    )


def downgrade():
    op.drop_constraint(
        "uq_workflow_transition_route",
        "ged_workflow_transitions",
        type_="unique",
    )
    op.drop_column("ged_workflow_transitions", "action_code")

"""Add auditable document suspension state."""

from alembic import op
import sqlalchemy as sa


revision = "a5b6c7d8e9f0"
down_revision = "f4a5b6c7d8e9"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TYPE geddocumentstatus ADD VALUE IF NOT EXISTS 'SUSPENSO'")
    op.add_column("ged_documents", sa.Column("suspended_previous_status", sa.String(), nullable=True))
    op.add_column("ged_documents", sa.Column("suspension_reason", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("ged_documents", "suspension_reason")
    op.drop_column("ged_documents", "suspended_previous_status")

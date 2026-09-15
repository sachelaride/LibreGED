"""Add group identity to academic dossiers."""

from alembic import op
import sqlalchemy as sa


revision = "e3f4a5b6c7d8"
down_revision = "d2e3f4a5b6c7"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("academic_dossiers", sa.Column("group_id", sa.String(), nullable=True))
    op.create_index("ix_academic_dossiers_group_id", "academic_dossiers", ["group_id"])


def downgrade():
    op.drop_index("ix_academic_dossiers_group_id", table_name="academic_dossiers")
    op.drop_column("academic_dossiers", "group_id")

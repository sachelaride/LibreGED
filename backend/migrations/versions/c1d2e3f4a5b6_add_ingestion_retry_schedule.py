"""Add persistent retry scheduling to ingestion jobs."""

from alembic import op
import sqlalchemy as sa


revision = "c1d2e3f4a5b6"
down_revision = "b0c1d2e3f4a5"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("ingestion_jobs", sa.Column("next_attempt_at", sa.DateTime(), nullable=True))
    op.create_index("ix_ingestion_jobs_next_attempt_at", "ingestion_jobs", ["next_attempt_at"])


def downgrade():
    op.drop_index("ix_ingestion_jobs_next_attempt_at", table_name="ingestion_jobs")
    op.drop_column("ingestion_jobs", "next_attempt_at")

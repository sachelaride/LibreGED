"""Add idempotency fields to ingestion jobs."""

from alembic import op
import sqlalchemy as sa


revision = "c4a7b1d2e3f4"
down_revision = "a1f0218f1c70"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("ingestion_jobs", sa.Column("ingestion_id", sa.String(), nullable=True))
    op.add_column("ingestion_jobs", sa.Column("correlation_id", sa.String(), nullable=True))
    op.add_column("ingestion_jobs", sa.Column("document_id", sa.String(), nullable=True))
    op.create_index(
        "ix_ingestion_jobs_ingestion_id", "ingestion_jobs", ["ingestion_id"], unique=True
    )
    op.create_index(
        "ix_ingestion_jobs_correlation_id", "ingestion_jobs", ["correlation_id"], unique=False
    )
    op.create_index(
        "ix_ingestion_jobs_document_id", "ingestion_jobs", ["document_id"], unique=False
    )
    op.create_foreign_key(
        "fk_ingestion_jobs_document_id",
        "ingestion_jobs",
        "ged_documents",
        ["document_id"],
        ["id"],
    )


def downgrade():
    op.drop_constraint("fk_ingestion_jobs_document_id", "ingestion_jobs", type_="foreignkey")
    op.drop_index("ix_ingestion_jobs_document_id", table_name="ingestion_jobs")
    op.drop_index("ix_ingestion_jobs_correlation_id", table_name="ingestion_jobs")
    op.drop_index("ix_ingestion_jobs_ingestion_id", table_name="ingestion_jobs")
    op.drop_column("ingestion_jobs", "document_id")
    op.drop_column("ingestion_jobs", "correlation_id")
    op.drop_column("ingestion_jobs", "ingestion_id")

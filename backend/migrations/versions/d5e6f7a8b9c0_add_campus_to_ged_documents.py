"""Add campus scope to GED documents."""

from alembic import op
import sqlalchemy as sa


revision = "d5e6f7a8b9c0"
down_revision = "c4a7b1d2e3f4"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("ged_documents", sa.Column("campus_id", sa.String(), nullable=True))
    op.create_index(
        "ix_ged_documents_campus_id", "ged_documents", ["campus_id"], unique=False
    )
    op.create_foreign_key(
        "fk_ged_documents_campus_id",
        "ged_documents",
        "campuses",
        ["campus_id"],
        ["id"],
    )


def downgrade():
    op.drop_constraint("fk_ged_documents_campus_id", "ged_documents", type_="foreignkey")
    op.drop_index("ix_ged_documents_campus_id", table_name="ged_documents")
    op.drop_column("ged_documents", "campus_id")

"""Link second-copy documents to their source document."""

from alembic import op
import sqlalchemy as sa

revision = "c7d8e9f0a1b2"
down_revision = "b6c7d8e9f0a1"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "ged_documents",
        sa.Column("second_copy_of_id", sa.String(), nullable=True),
    )
    op.create_index(
        "ix_ged_documents_second_copy_of_id",
        "ged_documents",
        ["second_copy_of_id"],
    )
    op.create_foreign_key(
        "fk_ged_documents_second_copy_of_id",
        "ged_documents",
        "ged_documents",
        ["second_copy_of_id"],
        ["id"],
    )


def downgrade():
    op.drop_constraint(
        "fk_ged_documents_second_copy_of_id", "ged_documents", type_="foreignkey"
    )
    op.drop_index("ix_ged_documents_second_copy_of_id", table_name="ged_documents")
    op.drop_column("ged_documents", "second_copy_of_id")

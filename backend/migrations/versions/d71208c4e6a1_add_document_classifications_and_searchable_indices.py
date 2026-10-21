"""Add document classifications and searchable index defaults."""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d71208c4e6a1"
down_revision: Union[str, Sequence[str], None] = "502057c2d0b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("ged_indices", sa.Column("default_value", sa.String(), nullable=True))
    op.add_column(
        "ged_indices",
        sa.Column("is_searchable", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_table(
        "ged_document_classifications",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("document_type_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["document_type_id"], ["ged_document_types.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "document_type_id", "name", name="uq_document_classification_type_name"
        ),
    )
    op.create_index(
        "ix_ged_document_classifications_document_type_id",
        "ged_document_classifications",
        ["document_type_id"],
    )
    with op.batch_alter_table("ged_documents") as batch_op:
        batch_op.add_column(sa.Column("classification_id", sa.String(), nullable=True))
        batch_op.create_foreign_key(
            "fk_ged_documents_classification_id",
            "ged_document_classifications",
            ["classification_id"],
            ["id"],
            ondelete="SET NULL",
        )
    op.create_index(
        "ix_ged_documents_classification_id", "ged_documents", ["classification_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_ged_documents_classification_id", table_name="ged_documents")
    with op.batch_alter_table("ged_documents") as batch_op:
        batch_op.drop_constraint(
            "fk_ged_documents_classification_id", type_="foreignkey"
        )
        batch_op.drop_column("classification_id")
    op.drop_index(
        "ix_ged_document_classifications_document_type_id",
        table_name="ged_document_classifications",
    )
    op.drop_table("ged_document_classifications")
    op.drop_column("ged_indices", "is_searchable")
    op.drop_column("ged_indices", "default_value")

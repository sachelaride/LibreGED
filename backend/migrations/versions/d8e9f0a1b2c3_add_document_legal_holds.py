"""Add document-level legal hold records."""

from alembic import op
import sqlalchemy as sa

revision = "d8e9f0a1b2c3"
down_revision = "c7d8e9f0a1b2"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ged_document_legal_holds",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("document_id", sa.String(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("authorization_reference", sa.String(), nullable=False),
        sa.Column("placed_by_user_id", sa.String(), nullable=False),
        sa.Column("placed_at", sa.DateTime(), nullable=False),
        sa.Column("released_by_user_id", sa.String(), nullable=True),
        sa.Column("released_at", sa.DateTime(), nullable=True),
        sa.Column("release_reason", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["document_id"], ["ged_documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["placed_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["released_by_user_id"], ["users.id"]),
    )
    op.create_index(
        "ix_ged_document_legal_holds_document_id",
        "ged_document_legal_holds",
        ["document_id"],
    )


def downgrade():
    op.drop_index(
        "ix_ged_document_legal_holds_document_id",
        table_name="ged_document_legal_holds",
    )
    op.drop_table("ged_document_legal_holds")

"""Identify conference documents as non-official."""

from alembic import op
import sqlalchemy as sa


revision = "f4a5b6c7d8e9"
down_revision = "e3f4a5b6c7d8"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("ged_documents", sa.Column(
        "document_purpose", sa.String(), nullable=False, server_default="official"
    ))
    op.add_column("ged_documents", sa.Column(
        "is_official", sa.Boolean(), nullable=False, server_default=sa.true()
    ))


def downgrade():
    op.drop_column("ged_documents", "is_official")
    op.drop_column("ged_documents", "document_purpose")

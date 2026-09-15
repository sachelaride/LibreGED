"""Add revocation and annulment document states."""

from alembic import op
import sqlalchemy as sa

revision = "b6c7d8e9f0a1"
down_revision = "a5b6c7d8e9f0"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TYPE geddocumentstatus ADD VALUE IF NOT EXISTS 'REVOGADO'")
    op.execute("ALTER TYPE geddocumentstatus ADD VALUE IF NOT EXISTS 'ANULADO'")
    op.add_column("ged_documents", sa.Column("revocation_reason", sa.Text(), nullable=True))
    op.add_column("ged_documents", sa.Column("annulment_reason", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("ged_documents", "annulment_reason")
    op.drop_column("ged_documents", "revocation_reason")

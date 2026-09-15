"""Add public verification codes to GED documents."""

from alembic import op
import sqlalchemy as sa

revision = "e9f0a1b2c3d4"
down_revision = "d8e9f0a1b2c3"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("ged_documents", sa.Column("public_code", sa.String(), nullable=True))
    op.execute(
        "UPDATE ged_documents SET public_code = md5(id || random()::text) "
        "WHERE public_code IS NULL"
    )
    op.alter_column("ged_documents", "public_code", nullable=False)
    op.create_index("ix_ged_documents_public_code", "ged_documents", ["public_code"], unique=True)


def downgrade():
    op.drop_index("ix_ged_documents_public_code", table_name="ged_documents")
    op.drop_column("ged_documents", "public_code")

"""Adiciona opções, máscara, autonumeração e vínculo único aos índices."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "b28d02c3e541"
down_revision = "a17c91b2d430"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("ged_indices", sa.Column(
        "options", postgresql.JSONB(), nullable=False, server_default="[]"))
    op.add_column("ged_indices", sa.Column("mask", sa.String(), nullable=True))
    op.add_column("ged_indices", sa.Column(
        "auto_increment", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.execute("""
        DELETE FROM ged_document_type_indices atual
        USING ged_document_type_indices repetido
        WHERE atual.document_type_id = repetido.document_type_id
          AND atual.index_id = repetido.index_id
          AND atual.id > repetido.id
    """)
    op.create_unique_constraint(
        "uq_document_type_index", "ged_document_type_indices",
        ["document_type_id", "index_id"])


def downgrade():
    op.drop_constraint(
        "uq_document_type_index", "ged_document_type_indices", type_="unique")
    op.drop_column("ged_indices", "auto_increment")
    op.drop_column("ged_indices", "mask")
    op.drop_column("ged_indices", "options")

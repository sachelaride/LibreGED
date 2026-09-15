"""Add durable indexing outbox fields."""

from alembic import op
import sqlalchemy as sa


revision = "d2e3f4a5b6c7"
down_revision = "c1d2e3f4a5b6"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("ged_fila_processamento", sa.Column("index_payload", sa.Text(), nullable=True))
    op.add_column("ged_fila_processamento", sa.Column("indexed_at", sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column("ged_fila_processamento", "indexed_at")
    op.drop_column("ged_fila_processamento", "index_payload")

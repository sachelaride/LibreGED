"""Adiciona privilégios explícitos aos vínculos documentais dos usuários."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'a17c91b2d430'
down_revision = '0f25e1d72b31'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('ged_user_document_types', sa.Column(
        'permissions', postgresql.JSONB(), nullable=False, server_default='[]'))
    # Vínculos antigos preservam consulta; operações de escrita exigem concessão.
    op.execute("UPDATE ged_user_document_types SET permissions = '[\"consultar\"]'::jsonb")


def downgrade():
    op.drop_column('ged_user_document_types', 'permissions')

"""Add FTS5 virtual table

Revision ID: 064963f122ad
Revises: a4588b9baf7e
Create Date: 2026-08-31 16:40:25.462849
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '064963f122ad'
down_revision: Union[str, Sequence[str], None] = 'a4588b9baf7e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass


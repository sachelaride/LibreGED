"""Link student accounts to academic records.

Revision ID: 20261109stuuser
Revises: 20261108finguard
Create Date: 2026-11-03
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261109stuuser"
down_revision: Union[str, Sequence[str], None] = "20261108finguard"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("students", sa.Column("user_id", sa.String(), nullable=True))
    op.create_foreign_key(
        "fk_students_user_id_users",
        "students",
        "users",
        ["user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_students_user_id", "students", ["user_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_students_user_id", table_name="students")
    op.drop_constraint("fk_students_user_id_users", "students", type_="foreignkey")
    op.drop_column("students", "user_id")

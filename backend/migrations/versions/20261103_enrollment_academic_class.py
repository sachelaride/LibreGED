"""Link enrollments to the academic catalog class.

Revision ID: 20261103enrollclass
Revises: 20261103address
Create Date: 2026-11-03
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261103enrollclass"
down_revision: Union[str, Sequence[str], None] = "20261103address"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "enrollments",
        sa.Column("academic_class_id", sa.String(), nullable=True),
    )
    op.create_index(
        "ix_enrollments_academic_class_id",
        "enrollments",
        ["academic_class_id"],
    )
    op.create_foreign_key(
        "fk_enrollments_academic_class_id_academic_classes",
        "enrollments",
        "academic_classes",
        ["academic_class_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_enrollments_academic_class_id_academic_classes",
        "enrollments",
        type_="foreignkey",
    )
    op.drop_index("ix_enrollments_academic_class_id", table_name="enrollments")
    op.drop_column("enrollments", "academic_class_id")

"""Add curriculum prerequisites and persisted enrollment results.

Revision ID: 20261103prereq
Revises: 20261103enrollclass
Create Date: 2026-11-03
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261103prereq"
down_revision: Union[str, Sequence[str], None] = "20261103enrollclass"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "enrollments",
        sa.Column(
            "result",
            sa.String(),
            nullable=False,
            server_default="pending",
        ),
    )
    op.create_index("ix_enrollments_result", "enrollments", ["result"])
    op.create_table(
        "academic_curriculum_prerequisites",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("curriculum_discipline_id", sa.String(), nullable=False),
        sa.Column("prerequisite_curriculum_discipline_id", sa.String(), nullable=False),
        sa.CheckConstraint(
            "curriculum_discipline_id != prerequisite_curriculum_discipline_id",
            name="ck_academic_curriculum_prerequisite_not_self",
        ),
        sa.ForeignKeyConstraint(
            ["curriculum_discipline_id"],
            ["academic_curriculum_disciplines.id"],
        ),
        sa.ForeignKeyConstraint(
            ["prerequisite_curriculum_discipline_id"],
            ["academic_curriculum_disciplines.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "curriculum_discipline_id",
            "prerequisite_curriculum_discipline_id",
            name="uq_academic_curriculum_prerequisite",
        ),
    )
    op.create_index(
        "ix_academic_curriculum_prerequisites_id",
        "academic_curriculum_prerequisites",
        ["id"],
    )
    op.create_index(
        "ix_acad_cur_prereq_target",
        "academic_curriculum_prerequisites",
        ["curriculum_discipline_id"],
    )
    op.create_index(
        "ix_acad_cur_prereq_source",
        "academic_curriculum_prerequisites",
        ["prerequisite_curriculum_discipline_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_acad_cur_prereq_source",
        table_name="academic_curriculum_prerequisites",
    )
    op.drop_index(
        "ix_acad_cur_prereq_target",
        table_name="academic_curriculum_prerequisites",
    )
    op.drop_index(
        "ix_academic_curriculum_prerequisites_id",
        table_name="academic_curriculum_prerequisites",
    )
    op.drop_table("academic_curriculum_prerequisites")
    op.drop_index("ix_enrollments_result", table_name="enrollments")
    op.drop_column("enrollments", "result")

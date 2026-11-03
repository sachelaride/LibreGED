"""Add formal academic credit recognition requests.

Revision ID: 20261103credit
Revises: 20261103curreq
Create Date: 2026-11-03
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261103credit"
down_revision: Union[str, Sequence[str], None] = "20261103curreq"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "academic_credit_recognitions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("institution_id", sa.String(), nullable=False),
        sa.Column("student_id", sa.String(), nullable=False),
        sa.Column("course_id", sa.String(), nullable=False),
        sa.Column("curriculum_discipline_id", sa.String(), nullable=False),
        sa.Column("source_institution", sa.String(), nullable=False),
        sa.Column("source_course", sa.String(), nullable=False),
        sa.Column("source_discipline", sa.String(), nullable=False),
        sa.Column("workload_hours", sa.Integer(), nullable=False),
        sa.Column("credits", sa.Integer(), nullable=False),
        sa.Column("request_note", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("decision_note", sa.String(), nullable=True),
        sa.Column("reviewer_id", sa.String(), nullable=True),
        sa.Column("requested_at", sa.DateTime(), nullable=False),
        sa.Column("decided_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint(
            "workload_hours > 0",
            name="ck_academic_credit_recognition_workload",
        ),
        sa.CheckConstraint(
            "credits >= 0",
            name="ck_academic_credit_recognition_credits",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'approved', 'rejected')",
            name="ck_academic_credit_recognition_status",
        ),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"]),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"]),
        sa.ForeignKeyConstraint(["course_id"], ["academic_courses.id"]),
        sa.ForeignKeyConstraint(
            ["curriculum_discipline_id"],
            ["academic_curriculum_disciplines.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_academic_credit_recognitions_id",
        "academic_credit_recognitions",
        ["id"],
    )
    op.create_index(
        "ix_academic_credit_recognitions_institution_id",
        "academic_credit_recognitions",
        ["institution_id"],
    )
    op.create_index(
        "ix_academic_credit_recognitions_student_id",
        "academic_credit_recognitions",
        ["student_id"],
    )
    op.create_index(
        "ix_academic_credit_recognitions_course_id",
        "academic_credit_recognitions",
        ["course_id"],
    )
    op.create_index(
        "ix_academic_credit_recognitions_curriculum_discipline_id",
        "academic_credit_recognitions",
        ["curriculum_discipline_id"],
    )
    op.create_index(
        "ix_academic_credit_recognitions_status",
        "academic_credit_recognitions",
        ["status"],
    )
    op.create_index(
        "ix_acad_credit_recognition_student",
        "academic_credit_recognitions",
        ["student_id", "course_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_acad_credit_recognition_student",
        table_name="academic_credit_recognitions",
    )
    op.drop_index(
        "ix_academic_credit_recognitions_status",
        table_name="academic_credit_recognitions",
    )
    op.drop_index(
        "ix_academic_credit_recognitions_curriculum_discipline_id",
        table_name="academic_credit_recognitions",
    )
    op.drop_index(
        "ix_academic_credit_recognitions_course_id",
        table_name="academic_credit_recognitions",
    )
    op.drop_index(
        "ix_academic_credit_recognitions_student_id",
        table_name="academic_credit_recognitions",
    )
    op.drop_index(
        "ix_academic_credit_recognitions_institution_id",
        table_name="academic_credit_recognitions",
    )
    op.drop_index(
        "ix_academic_credit_recognitions_id",
        table_name="academic_credit_recognitions",
    )
    op.drop_table("academic_credit_recognitions")

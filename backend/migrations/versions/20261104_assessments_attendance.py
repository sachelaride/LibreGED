"""Add persistent academic assessments, grades, attendance, and teacher account links.

Revision ID: 20261104assessments
Revises: 20261103coordassign
Create Date: 2026-11-04
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261104assessments"
down_revision: Union[str, Sequence[str], None] = "20261103coordassign"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "academic_staff",
        sa.Column("user_id", sa.String(), nullable=True),
    )
    op.create_foreign_key(
        "fk_academic_staff_user_id_users",
        "academic_staff",
        "users",
        ["user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_academic_staff_user_id",
        "academic_staff",
        ["user_id"],
        unique=True,
    )

    op.create_table(
        "academic_assessments",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("institution_id", sa.String(), nullable=False),
        sa.Column("class_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=True),
        sa.Column("max_score", sa.Float(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("max_score > 0", name="ck_academic_assessment_max_score"),
        sa.ForeignKeyConstraint(["class_id"], ["academic_classes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_academic_assessments_class_id", "academic_assessments", ["class_id"])
    op.create_index("ix_academic_assessments_id", "academic_assessments", ["id"])
    op.create_index("ix_academic_assessments_institution_id", "academic_assessments", ["institution_id"])

    op.create_table(
        "academic_grades",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("institution_id", sa.String(), nullable=False),
        sa.Column("assessment_id", sa.String(), nullable=False),
        sa.Column("enrollment_id", sa.String(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("comment", sa.String(length=2000), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("score >= 0", name="ck_academic_grade_score"),
        sa.ForeignKeyConstraint(["assessment_id"], ["academic_assessments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["enrollment_id"], ["enrollments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("assessment_id", "enrollment_id", name="uq_academic_grade_assessment_enrollment"),
    )
    op.create_index("ix_academic_grades_assessment_id", "academic_grades", ["assessment_id"])
    op.create_index("ix_academic_grades_enrollment_id", "academic_grades", ["enrollment_id"])
    op.create_index("ix_academic_grades_id", "academic_grades", ["id"])
    op.create_index("ix_academic_grades_institution_id", "academic_grades", ["institution_id"])

    op.create_table(
        "academic_attendance",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("institution_id", sa.String(), nullable=False),
        sa.Column("class_id", sa.String(), nullable=False),
        sa.Column("enrollment_id", sa.String(), nullable=False),
        sa.Column("attendance_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("note", sa.String(length=1000), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "status IN ('present', 'absent', 'justified', 'remote')",
            name="ck_academic_attendance_status",
        ),
        sa.ForeignKeyConstraint(["class_id"], ["academic_classes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["enrollment_id"], ["enrollments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "class_id",
            "enrollment_id",
            "attendance_date",
            name="uq_academic_attendance_class_enrollment_date",
        ),
    )
    op.create_index("ix_academic_attendance_attendance_date", "academic_attendance", ["attendance_date"])
    op.create_index("ix_academic_attendance_class_id", "academic_attendance", ["class_id"])
    op.create_index("ix_academic_attendance_enrollment_id", "academic_attendance", ["enrollment_id"])
    op.create_index("ix_academic_attendance_id", "academic_attendance", ["id"])
    op.create_index("ix_academic_attendance_institution_id", "academic_attendance", ["institution_id"])


def downgrade() -> None:
    op.drop_index("ix_academic_attendance_institution_id", table_name="academic_attendance")
    op.drop_index("ix_academic_attendance_id", table_name="academic_attendance")
    op.drop_index("ix_academic_attendance_enrollment_id", table_name="academic_attendance")
    op.drop_index("ix_academic_attendance_class_id", table_name="academic_attendance")
    op.drop_index("ix_academic_attendance_attendance_date", table_name="academic_attendance")
    op.drop_table("academic_attendance")

    op.drop_index("ix_academic_grades_institution_id", table_name="academic_grades")
    op.drop_index("ix_academic_grades_id", table_name="academic_grades")
    op.drop_index("ix_academic_grades_enrollment_id", table_name="academic_grades")
    op.drop_index("ix_academic_grades_assessment_id", table_name="academic_grades")
    op.drop_table("academic_grades")

    op.drop_index("ix_academic_assessments_institution_id", table_name="academic_assessments")
    op.drop_index("ix_academic_assessments_id", table_name="academic_assessments")
    op.drop_index("ix_academic_assessments_class_id", table_name="academic_assessments")
    op.drop_table("academic_assessments")

    op.drop_index("ix_academic_staff_user_id", table_name="academic_staff")
    op.drop_constraint("fk_academic_staff_user_id_users", "academic_staff", type_="foreignkey")
    op.drop_column("academic_staff", "user_id")

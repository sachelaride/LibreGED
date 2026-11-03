"""Add persistent academic catalog and scheduling records.

Revision ID: 20261101acad
Revises: d71208c4e6a1
Create Date: 2026-11-01
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261101acad"
down_revision: Union[str, Sequence[str], None] = "d71208c4e6a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "academic_courses",
        sa.Column("id", sa.String(), nullable=False, index=True),
        sa.Column("institution_id", sa.String(), nullable=False, index=True),
        sa.Column("campus_id", sa.String(), nullable=True, index=True),
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False, index=True),
        sa.Column("degree", sa.String(), nullable=False),
        sa.Column("modality", sa.String(), nullable=False),
        sa.Column("duration_periods", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"]),
        sa.ForeignKeyConstraint(["campus_id"], ["campuses.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("institution_id", "code", name="uq_academic_course_code"),
    )
    op.create_table(
        "academic_disciplines",
        sa.Column("id", sa.String(), nullable=False, index=True),
        sa.Column("institution_id", sa.String(), nullable=False, index=True),
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False, index=True),
        sa.Column("workload_hours", sa.Integer(), nullable=False),
        sa.Column("credits", sa.Integer(), nullable=False),
        sa.Column("syllabus", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.CheckConstraint("workload_hours > 0", name="ck_academic_discipline_workload"),
        sa.CheckConstraint("credits >= 0", name="ck_academic_discipline_credits"),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("institution_id", "code", name="uq_academic_discipline_code"),
    )
    op.create_table(
        "academic_terms",
        sa.Column("id", sa.String(), nullable=False, index=True),
        sa.Column("institution_id", sa.String(), nullable=False, index=True),
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("starts_on", sa.Date(), nullable=False),
        sa.Column("ends_on", sa.Date(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.CheckConstraint("ends_on >= starts_on", name="ck_academic_term_dates"),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("institution_id", "code", name="uq_academic_term_code"),
    )
    op.create_table(
        "academic_curricula",
        sa.Column("id", sa.String(), nullable=False, index=True),
        sa.Column("institution_id", sa.String(), nullable=False, index=True),
        sa.Column("course_id", sa.String(), nullable=False, index=True),
        sa.Column("version", sa.String(), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"]),
        sa.ForeignKeyConstraint(["course_id"], ["academic_courses.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("course_id", "version", name="uq_academic_curriculum_version"),
    )
    op.create_table(
        "academic_curriculum_disciplines",
        sa.Column("id", sa.String(), nullable=False, index=True),
        sa.Column("curriculum_id", sa.String(), nullable=False, index=True),
        sa.Column("discipline_id", sa.String(), nullable=False, index=True),
        sa.Column("term_number", sa.Integer(), nullable=False),
        sa.Column("is_required", sa.Boolean(), nullable=False),
        sa.CheckConstraint("term_number > 0", name="ck_academic_curriculum_term_number"),
        sa.ForeignKeyConstraint(["curriculum_id"], ["academic_curricula.id"]),
        sa.ForeignKeyConstraint(["discipline_id"], ["academic_disciplines.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("curriculum_id", "discipline_id", name="uq_academic_curriculum_discipline"),
    )
    op.create_table(
        "academic_staff",
        sa.Column("id", sa.String(), nullable=False, index=True),
        sa.Column("institution_id", sa.String(), nullable=False, index=True),
        sa.Column("campus_id", sa.String(), nullable=True, index=True),
        sa.Column("staff_code", sa.String(), nullable=False),
        sa.Column("full_name", sa.String(), nullable=False, index=True),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("staff_type", sa.String(), nullable=False, index=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"]),
        sa.ForeignKeyConstraint(["campus_id"], ["campuses.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("institution_id", "email", name="uq_academic_staff_email"),
        sa.UniqueConstraint("institution_id", "staff_code", name="uq_academic_staff_code"),
    )
    op.create_table(
        "academic_rooms",
        sa.Column("id", sa.String(), nullable=False, index=True),
        sa.Column("institution_id", sa.String(), nullable=False, index=True),
        sa.Column("campus_id", sa.String(), nullable=False, index=True),
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("room_type", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.CheckConstraint("capacity > 0", name="ck_academic_room_capacity"),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"]),
        sa.ForeignKeyConstraint(["campus_id"], ["campuses.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("campus_id", "code", name="uq_academic_room_code"),
    )
    op.create_table(
        "academic_offerings",
        sa.Column("id", sa.String(), nullable=False, index=True),
        sa.Column("institution_id", sa.String(), nullable=False, index=True),
        sa.Column("course_id", sa.String(), nullable=False, index=True),
        sa.Column("discipline_id", sa.String(), nullable=False, index=True),
        sa.Column("term_id", sa.String(), nullable=False, index=True),
        sa.Column("campus_id", sa.String(), nullable=False, index=True),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.CheckConstraint("capacity > 0", name="ck_academic_offering_capacity"),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"]),
        sa.ForeignKeyConstraint(["course_id"], ["academic_courses.id"]),
        sa.ForeignKeyConstraint(["discipline_id"], ["academic_disciplines.id"]),
        sa.ForeignKeyConstraint(["term_id"], ["academic_terms.id"]),
        sa.ForeignKeyConstraint(["campus_id"], ["campuses.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("course_id", "discipline_id", "term_id", "campus_id", name="uq_academic_offering_scope"),
    )
    op.create_table(
        "academic_classes",
        sa.Column("id", sa.String(), nullable=False, index=True),
        sa.Column("institution_id", sa.String(), nullable=False, index=True),
        sa.Column("offering_id", sa.String(), nullable=False, index=True),
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("teacher_id", sa.String(), nullable=True, index=True),
        sa.Column("coordinator_id", sa.String(), nullable=True, index=True),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.CheckConstraint("capacity > 0", name="ck_academic_class_capacity"),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"]),
        sa.ForeignKeyConstraint(["offering_id"], ["academic_offerings.id"]),
        sa.ForeignKeyConstraint(["teacher_id"], ["academic_staff.id"]),
        sa.ForeignKeyConstraint(["coordinator_id"], ["academic_staff.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("offering_id", "code", name="uq_academic_class_code"),
    )
    op.create_table(
        "academic_class_schedules",
        sa.Column("id", sa.String(), nullable=False, index=True),
        sa.Column("institution_id", sa.String(), nullable=False, index=True),
        sa.Column("class_id", sa.String(), nullable=False, index=True),
        sa.Column("room_id", sa.String(), nullable=True, index=True),
        sa.Column("weekday", sa.Integer(), nullable=False),
        sa.Column("starts_at", sa.Time(), nullable=False),
        sa.Column("ends_at", sa.Time(), nullable=False),
        sa.CheckConstraint("ends_at > starts_at", name="ck_academic_schedule_times"),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"]),
        sa.ForeignKeyConstraint(["class_id"], ["academic_classes.id"]),
        sa.ForeignKeyConstraint(["room_id"], ["academic_rooms.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("academic_class_schedules")
    op.drop_table("academic_classes")
    op.drop_table("academic_offerings")
    op.drop_table("academic_rooms")
    op.drop_table("academic_staff")
    op.drop_table("academic_curriculum_disciplines")
    op.drop_table("academic_curricula")
    op.drop_table("academic_terms")
    op.drop_table("academic_disciplines")
    op.drop_table("academic_courses")

"""Store student course admission data required by MEC transcripts.

Revision ID: 20261103entry
Revises: 20261103regidx
Create Date: 2026-11-03
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261103entry"
down_revision: Union[str, Sequence[str], None] = "20261103regidx"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "student_course_transcript_profiles",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("institution_id", sa.String(), nullable=False),
        sa.Column("student_id", sa.String(), nullable=False),
        sa.Column("course_id", sa.String(), nullable=False),
        sa.Column("entry_date", sa.Date(), nullable=False),
        sa.Column("access_form", sa.String(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"]),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"]),
        sa.ForeignKeyConstraint(["course_id"], ["academic_courses.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "student_id",
            "course_id",
            name="uq_student_course_transcript_profile",
        ),
    )
    op.create_index(
        "ix_student_course_transcript_profiles_id",
        "student_course_transcript_profiles",
        ["id"],
    )
    op.create_index(
        "ix_student_course_transcript_profiles_institution_id",
        "student_course_transcript_profiles",
        ["institution_id"],
    )
    op.create_index(
        "ix_student_course_transcript_profiles_student_id",
        "student_course_transcript_profiles",
        ["student_id"],
    )
    op.create_index(
        "ix_student_course_transcript_profiles_course_id",
        "student_course_transcript_profiles",
        ["course_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_student_course_transcript_profiles_course_id",
        table_name="student_course_transcript_profiles",
    )
    op.drop_index(
        "ix_student_course_transcript_profiles_student_id",
        table_name="student_course_transcript_profiles",
    )
    op.drop_index(
        "ix_student_course_transcript_profiles_institution_id",
        table_name="student_course_transcript_profiles",
    )
    op.drop_index(
        "ix_student_course_transcript_profiles_id",
        table_name="student_course_transcript_profiles",
    )
    op.drop_table("student_course_transcript_profiles")

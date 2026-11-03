"""Add institution and course transcript regulatory profiles.

Revision ID: 20261103regprof
Revises: 20261103identity
Create Date: 2026-11-03
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261103regprof"
down_revision: Union[str, Sequence[str], None] = "20261103identity"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "institution_transcript_profiles",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("institution_id", sa.String(), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("institution_id"),
    )
    op.create_index(
        "ix_institution_transcript_profiles_id",
        "institution_transcript_profiles",
        ["id"],
    )
    op.create_index(
        "ix_institution_transcript_profiles_institution_id",
        "institution_transcript_profiles",
        ["institution_id"],
    )

    op.create_table(
        "course_transcript_profiles",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("institution_id", sa.String(), nullable=False),
        sa.Column("course_id", sa.String(), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"]),
        sa.ForeignKeyConstraint(["course_id"], ["academic_courses.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("course_id"),
    )
    op.create_index(
        "ix_course_transcript_profiles_id",
        "course_transcript_profiles",
        ["id"],
    )
    op.create_index(
        "ix_course_transcript_profiles_institution_id",
        "course_transcript_profiles",
        ["institution_id"],
    )
    op.create_index(
        "ix_course_transcript_profiles_course_id",
        "course_transcript_profiles",
        ["course_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_course_transcript_profiles_course_id", table_name="course_transcript_profiles")
    op.drop_index("ix_course_transcript_profiles_institution_id", table_name="course_transcript_profiles")
    op.drop_index("ix_course_transcript_profiles_id", table_name="course_transcript_profiles")
    op.drop_table("course_transcript_profiles")
    op.drop_index(
        "ix_institution_transcript_profiles_institution_id",
        table_name="institution_transcript_profiles",
    )
    op.drop_index("ix_institution_transcript_profiles_id", table_name="institution_transcript_profiles")
    op.drop_table("institution_transcript_profiles")

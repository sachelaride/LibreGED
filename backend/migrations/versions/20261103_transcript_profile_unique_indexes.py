"""Align transcript profile uniqueness with model indexes.

Revision ID: 20261103regidx
Revises: 20261103regprof
Create Date: 2026-11-03
"""

from typing import Sequence, Union

from alembic import op


revision: str = "20261103regidx"
down_revision: Union[str, Sequence[str], None] = "20261103regprof"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        "institution_transcript_profiles_institution_id_key",
        "institution_transcript_profiles",
        type_="unique",
    )
    op.drop_index(
        "ix_institution_transcript_profiles_institution_id",
        table_name="institution_transcript_profiles",
    )
    op.create_index(
        "ix_institution_transcript_profiles_institution_id",
        "institution_transcript_profiles",
        ["institution_id"],
        unique=True,
    )

    op.drop_constraint(
        "course_transcript_profiles_course_id_key",
        "course_transcript_profiles",
        type_="unique",
    )
    op.drop_index(
        "ix_course_transcript_profiles_course_id",
        table_name="course_transcript_profiles",
    )
    op.create_index(
        "ix_course_transcript_profiles_course_id",
        "course_transcript_profiles",
        ["course_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_course_transcript_profiles_course_id",
        table_name="course_transcript_profiles",
    )
    op.create_index(
        "ix_course_transcript_profiles_course_id",
        "course_transcript_profiles",
        ["course_id"],
    )
    op.create_unique_constraint(
        "course_transcript_profiles_course_id_key",
        "course_transcript_profiles",
        ["course_id"],
    )

    op.drop_index(
        "ix_institution_transcript_profiles_institution_id",
        table_name="institution_transcript_profiles",
    )
    op.create_index(
        "ix_institution_transcript_profiles_institution_id",
        "institution_transcript_profiles",
        ["institution_id"],
    )
    op.create_unique_constraint(
        "institution_transcript_profiles_institution_id_key",
        "institution_transcript_profiles",
        ["institution_id"],
    )

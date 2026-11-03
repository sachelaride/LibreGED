"""Add course and campus scoped coordinator responsibility periods.

Revision ID: 20261103coordassign
Revises: 20261103staffhist
Create Date: 2026-11-03
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261103coordassign"
down_revision: Union[str, Sequence[str], None] = "20261103staffhist"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "academic_coordinator_assignments",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("institution_id", sa.String(), nullable=False),
        sa.Column("coordinator_id", sa.String(), nullable=False),
        sa.Column("course_id", sa.String(), nullable=False),
        sa.Column("campus_id", sa.String(), nullable=False),
        sa.Column("starts_on", sa.Date(), nullable=False),
        sa.Column("ends_on", sa.Date(), nullable=False),
        sa.CheckConstraint(
            "ends_on >= starts_on",
            name="ck_academic_coordinator_assignment_dates",
        ),
        sa.ForeignKeyConstraint(["campus_id"], ["campuses.id"]),
        sa.ForeignKeyConstraint(["coordinator_id"], ["academic_staff.id"]),
        sa.ForeignKeyConstraint(["course_id"], ["academic_courses.id"]),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_academic_coordinator_assignments_campus_id",
        "academic_coordinator_assignments",
        ["campus_id"],
    )
    op.create_index(
        "ix_academic_coordinator_assignments_coordinator_id",
        "academic_coordinator_assignments",
        ["coordinator_id"],
    )
    op.create_index(
        "ix_academic_coordinator_assignments_course_id",
        "academic_coordinator_assignments",
        ["course_id"],
    )
    op.create_index(
        "ix_academic_coordinator_assignments_id",
        "academic_coordinator_assignments",
        ["id"],
    )
    op.create_index(
        "ix_academic_coordinator_assignments_institution_id",
        "academic_coordinator_assignments",
        ["institution_id"],
    )
    op.create_index(
        "ix_academic_coord_assignment_scope",
        "academic_coordinator_assignments",
        ["course_id", "campus_id", "starts_on", "ends_on"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_academic_coord_assignment_scope",
        table_name="academic_coordinator_assignments",
    )
    op.drop_index(
        "ix_academic_coordinator_assignments_institution_id",
        table_name="academic_coordinator_assignments",
    )
    op.drop_index(
        "ix_academic_coordinator_assignments_id",
        table_name="academic_coordinator_assignments",
    )
    op.drop_index(
        "ix_academic_coordinator_assignments_course_id",
        table_name="academic_coordinator_assignments",
    )
    op.drop_index(
        "ix_academic_coordinator_assignments_coordinator_id",
        table_name="academic_coordinator_assignments",
    )
    op.drop_index(
        "ix_academic_coordinator_assignments_campus_id",
        table_name="academic_coordinator_assignments",
    )
    op.drop_table("academic_coordinator_assignments")

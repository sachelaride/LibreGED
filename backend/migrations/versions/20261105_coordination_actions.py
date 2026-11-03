"""Persist academic coordination actions.

Revision ID: 20261105coordactions
Revises: 20261104assessments
Create Date: 2026-11-05
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261105coordactions"
down_revision: Union[str, Sequence[str], None] = "20261104assessments"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "academic_coordination_actions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("institution_id", sa.String(), nullable=False),
        sa.Column("student_id", sa.String(), nullable=False),
        sa.Column("course_id", sa.String(), nullable=False),
        sa.Column("campus_id", sa.String(), nullable=False),
        sa.Column("issue", sa.String(length=500), nullable=False),
        sa.Column("priority", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("responsible", sa.String(length=160), nullable=False),
        sa.Column("deadline", sa.Date(), nullable=True),
        sa.Column("category", sa.String(length=120), nullable=False),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column("resolved_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint(
            "priority IN ('alta', 'média', 'baixa')",
            name="ck_academic_coordination_action_priority",
        ),
        sa.CheckConstraint(
            "status IN ('em andamento', 'aguardando', 'concluída')",
            name="ck_academic_coordination_action_status",
        ),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"]),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"]),
        sa.ForeignKeyConstraint(["course_id"], ["academic_courses.id"]),
        sa.ForeignKeyConstraint(["campus_id"], ["campuses.id"]),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["resolved_by"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_academic_coordination_actions_id",
        "academic_coordination_actions",
        ["id"],
    )
    op.create_index(
        "ix_academic_coordination_actions_institution_id",
        "academic_coordination_actions",
        ["institution_id"],
    )
    op.create_index(
        "ix_academic_coordination_actions_student_id",
        "academic_coordination_actions",
        ["student_id"],
    )
    op.create_index(
        "ix_academic_coordination_actions_course_id",
        "academic_coordination_actions",
        ["course_id"],
    )
    op.create_index(
        "ix_academic_coordination_actions_campus_id",
        "academic_coordination_actions",
        ["campus_id"],
    )
    op.create_index(
        "ix_academic_coordination_actions_status",
        "academic_coordination_actions",
        ["status"],
    )
    op.create_index(
        "ix_academic_coordination_action_scope",
        "academic_coordination_actions",
        ["institution_id", "course_id", "campus_id", "status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_academic_coordination_action_scope",
        table_name="academic_coordination_actions",
    )
    op.drop_index(
        "ix_academic_coordination_actions_status",
        table_name="academic_coordination_actions",
    )
    op.drop_index(
        "ix_academic_coordination_actions_campus_id",
        table_name="academic_coordination_actions",
    )
    op.drop_index(
        "ix_academic_coordination_actions_course_id",
        table_name="academic_coordination_actions",
    )
    op.drop_index(
        "ix_academic_coordination_actions_student_id",
        table_name="academic_coordination_actions",
    )
    op.drop_index(
        "ix_academic_coordination_actions_institution_id",
        table_name="academic_coordination_actions",
    )
    op.drop_index(
        "ix_academic_coordination_actions_id",
        table_name="academic_coordination_actions",
    )
    op.drop_table("academic_coordination_actions")

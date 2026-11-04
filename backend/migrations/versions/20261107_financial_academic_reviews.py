"""Track finance review required for academic transfers.

Revision ID: 20261107finreview
Revises: 20261106finance
Create Date: 2026-11-03
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261107finreview"
down_revision: Union[str, Sequence[str], None] = "20261106finance"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "financial_academic_reviews",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("institution_id", sa.String(), nullable=False),
        sa.Column("student_id", sa.String(), nullable=False),
        sa.Column("enrollment_id", sa.String(), nullable=False),
        sa.Column("review_type", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("details", sa.String(length=1000), nullable=False),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column("resolved_by", sa.String(), nullable=True),
        sa.Column("resolution_note", sa.String(length=2000), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint(
            "review_type IN ('transferencia')",
            name="ck_financial_academic_review_type",
        ),
        sa.CheckConstraint(
            "status IN ('pendente', 'resolvida')",
            name="ck_financial_academic_review_status",
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"], ["institutions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["student_id"], ["students.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["enrollment_id"], ["enrollments.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["resolved_by"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "enrollment_id",
            "review_type",
            name="uq_financial_academic_review_enrollment_type",
        ),
    )
    op.create_index(
        "ix_financial_academic_reviews_id",
        "financial_academic_reviews",
        ["id"],
    )
    op.create_index(
        "ix_financial_academic_reviews_institution_id",
        "financial_academic_reviews",
        ["institution_id"],
    )
    op.create_index(
        "ix_financial_academic_reviews_student_id",
        "financial_academic_reviews",
        ["student_id"],
    )
    op.create_index(
        "ix_financial_academic_reviews_enrollment_id",
        "financial_academic_reviews",
        ["enrollment_id"],
    )
    op.create_index(
        "ix_financial_academic_review_scope",
        "financial_academic_reviews",
        ["institution_id", "student_id", "status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_financial_academic_review_scope",
        table_name="financial_academic_reviews",
    )
    op.drop_index(
        "ix_financial_academic_reviews_enrollment_id",
        table_name="financial_academic_reviews",
    )
    op.drop_index(
        "ix_financial_academic_reviews_student_id",
        table_name="financial_academic_reviews",
    )
    op.drop_index(
        "ix_financial_academic_reviews_institution_id",
        table_name="financial_academic_reviews",
    )
    op.drop_index(
        "ix_financial_academic_reviews_id",
        table_name="financial_academic_reviews",
    )
    op.drop_table("financial_academic_reviews")

"""Add institutional departments and sectors to the academic catalog.

Revision ID: 20261103org
Revises: 20261103prereq
Create Date: 2026-11-03
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261103org"
down_revision: Union[str, Sequence[str], None] = "20261103prereq"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "academic_departments",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("institution_id", sa.String(), nullable=False),
        sa.Column("campus_id", sa.String(), nullable=True),
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["campus_id"], ["campuses.id"]),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("institution_id", "code", name="uq_academic_department_code"),
    )
    op.create_index("ix_academic_departments_id", "academic_departments", ["id"])
    op.create_index(
        "ix_academic_departments_institution_id",
        "academic_departments",
        ["institution_id"],
    )
    op.create_index("ix_academic_departments_campus_id", "academic_departments", ["campus_id"])
    op.create_index("ix_academic_departments_name", "academic_departments", ["name"])

    op.create_table(
        "academic_sectors",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("institution_id", sa.String(), nullable=False),
        sa.Column("department_id", sa.String(), nullable=False),
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["department_id"], ["academic_departments.id"]),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("department_id", "code", name="uq_academic_sector_code"),
    )
    op.create_index("ix_academic_sectors_id", "academic_sectors", ["id"])
    op.create_index("ix_academic_sectors_institution_id", "academic_sectors", ["institution_id"])
    op.create_index("ix_academic_sectors_department_id", "academic_sectors", ["department_id"])
    op.create_index("ix_academic_sectors_name", "academic_sectors", ["name"])


def downgrade() -> None:
    op.drop_index("ix_academic_sectors_name", table_name="academic_sectors")
    op.drop_index("ix_academic_sectors_department_id", table_name="academic_sectors")
    op.drop_index("ix_academic_sectors_institution_id", table_name="academic_sectors")
    op.drop_index("ix_academic_sectors_id", table_name="academic_sectors")
    op.drop_table("academic_sectors")
    op.drop_index("ix_academic_departments_name", table_name="academic_departments")
    op.drop_index("ix_academic_departments_campus_id", table_name="academic_departments")
    op.drop_index("ix_academic_departments_institution_id", table_name="academic_departments")
    op.drop_index("ix_academic_departments_id", table_name="academic_departments")
    op.drop_table("academic_departments")

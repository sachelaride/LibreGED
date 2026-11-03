"""Add elective groups and curricular discipline equivalences.

Revision ID: 20261103curreq
Revises: 20261103org
Create Date: 2026-11-03
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261103curreq"
down_revision: Union[str, Sequence[str], None] = "20261103org"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "academic_curriculum_equivalences",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("curriculum_discipline_id", sa.String(), nullable=False),
        sa.Column("equivalent_discipline_id", sa.String(), nullable=False),
        sa.CheckConstraint(
            "curriculum_discipline_id != equivalent_discipline_id",
            name="ck_academic_curriculum_equivalence_not_self",
        ),
        sa.ForeignKeyConstraint(
            ["curriculum_discipline_id"],
            ["academic_curriculum_disciplines.id"],
        ),
        sa.ForeignKeyConstraint(
            ["equivalent_discipline_id"],
            ["academic_disciplines.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "curriculum_discipline_id",
            "equivalent_discipline_id",
            name="uq_academic_curriculum_equivalence",
        ),
    )
    op.create_index("ix_academic_curriculum_equivalences_id", "academic_curriculum_equivalences", ["id"])
    op.create_index("ix_acad_cur_equivalence_target", "academic_curriculum_equivalences", ["curriculum_discipline_id"])
    op.create_index("ix_acad_cur_equivalence_source", "academic_curriculum_equivalences", ["equivalent_discipline_id"])

    op.create_table(
        "academic_curriculum_elective_groups",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("curriculum_id", sa.String(), nullable=False),
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("minimum_credits", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "minimum_credits > 0",
            name="ck_academic_curriculum_elective_min_credits",
        ),
        sa.ForeignKeyConstraint(["curriculum_id"], ["academic_curricula.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "curriculum_id",
            "code",
            name="uq_academic_curriculum_elective_group",
        ),
    )
    op.create_index("ix_academic_curriculum_elective_groups_id", "academic_curriculum_elective_groups", ["id"])
    op.create_index("ix_academic_curriculum_elective_groups_curriculum_id", "academic_curriculum_elective_groups", ["curriculum_id"])

    op.create_table(
        "academic_curriculum_elective_disciplines",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("elective_group_id", sa.String(), nullable=False),
        sa.Column("curriculum_discipline_id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["curriculum_discipline_id"],
            ["academic_curriculum_disciplines.id"],
        ),
        sa.ForeignKeyConstraint(
            ["elective_group_id"],
            ["academic_curriculum_elective_groups.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "curriculum_discipline_id",
            name="uq_academic_curriculum_elective_discipline",
        ),
        sa.UniqueConstraint(
            "elective_group_id",
            "curriculum_discipline_id",
            name="uq_academic_curriculum_elective_group_discipline",
        ),
    )
    op.create_index("ix_academic_curriculum_elective_disciplines_id", "academic_curriculum_elective_disciplines", ["id"])
    op.create_index("ix_acad_cur_elective_group", "academic_curriculum_elective_disciplines", ["elective_group_id"])
    op.create_index("ix_acad_cur_elective_link", "academic_curriculum_elective_disciplines", ["curriculum_discipline_id"])


def downgrade() -> None:
    op.drop_index(
        "ix_acad_cur_elective_link",
        table_name="academic_curriculum_elective_disciplines",
    )
    op.drop_index(
        "ix_acad_cur_elective_group",
        table_name="academic_curriculum_elective_disciplines",
    )
    op.drop_index(
        "ix_academic_curriculum_elective_disciplines_id",
        table_name="academic_curriculum_elective_disciplines",
    )
    op.drop_table("academic_curriculum_elective_disciplines")
    op.drop_index(
        "ix_academic_curriculum_elective_groups_curriculum_id",
        table_name="academic_curriculum_elective_groups",
    )
    op.drop_index(
        "ix_academic_curriculum_elective_groups_id",
        table_name="academic_curriculum_elective_groups",
    )
    op.drop_table("academic_curriculum_elective_groups")
    op.drop_index("ix_acad_cur_equivalence_source", table_name="academic_curriculum_equivalences")
    op.drop_index("ix_acad_cur_equivalence_target", table_name="academic_curriculum_equivalences")
    op.drop_index("ix_academic_curriculum_equivalences_id", table_name="academic_curriculum_equivalences")
    op.drop_table("academic_curriculum_equivalences")

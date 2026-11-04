"""Persist financial contracts and invoices.

Revision ID: 20261106finance
Revises: 20261105coordactions
Create Date: 2026-11-03
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261106finance"
down_revision: Union[str, Sequence[str], None] = "20261105coordactions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "financial_contracts",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("institution_id", sa.String(), nullable=False),
        sa.Column("student_id", sa.String(), nullable=False),
        sa.Column("enrollment_id", sa.String(), nullable=True),
        sa.Column("course_id", sa.String(), nullable=True),
        sa.Column("period", sa.String(length=40), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("plan", sa.String(length=120), nullable=False),
        sa.Column("total_amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("discount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("responsible_financial", sa.String(length=160), nullable=False),
        sa.Column("signed_at", sa.Date(), nullable=True),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "status IN ('em_validacao', 'ativo', 'cancelado')",
            name="ck_financial_contract_status",
        ),
        sa.CheckConstraint(
            "total_amount >= 0 AND discount >= 0 AND discount <= total_amount",
            name="ck_financial_contract_amounts",
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"], ["institutions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["enrollment_id"], ["enrollments.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["course_id"], ["academic_courses.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_financial_contracts_id", "financial_contracts", ["id"])
    op.create_index(
        "ix_financial_contracts_institution_id",
        "financial_contracts",
        ["institution_id"],
    )
    op.create_index(
        "ix_financial_contracts_student_id",
        "financial_contracts",
        ["student_id"],
    )
    op.create_index(
        "ix_financial_contracts_enrollment_id",
        "financial_contracts",
        ["enrollment_id"],
    )
    op.create_index(
        "ix_financial_contracts_course_id",
        "financial_contracts",
        ["course_id"],
    )
    op.create_index(
        "ix_financial_contract_scope",
        "financial_contracts",
        ["institution_id", "student_id", "course_id"],
    )

    op.create_table(
        "financial_invoices",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("institution_id", sa.String(), nullable=False),
        sa.Column("student_id", sa.String(), nullable=False),
        sa.Column("contract_id", sa.String(), nullable=False),
        sa.Column("enrollment_id", sa.String(), nullable=True),
        sa.Column("course_id", sa.String(), nullable=True),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("payment_recorded_at", sa.DateTime(), nullable=True),
        sa.Column("issuer", sa.String(length=120), nullable=False),
        sa.Column("payment_method", sa.String(length=40), nullable=False),
        sa.Column("installment", sa.String(length=40), nullable=False),
        sa.Column("responsible_financial", sa.String(length=160), nullable=False),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "status IN ('pendente', 'atrasado', 'vencido', 'quitado', 'cancelado')",
            name="ck_financial_invoice_status",
        ),
        sa.CheckConstraint("amount > 0", name="ck_financial_invoice_amount"),
        sa.ForeignKeyConstraint(
            ["institution_id"], ["institutions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["contract_id"], ["financial_contracts.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["enrollment_id"], ["enrollments.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["course_id"], ["academic_courses.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_financial_invoices_id", "financial_invoices", ["id"])
    op.create_index(
        "ix_financial_invoices_institution_id",
        "financial_invoices",
        ["institution_id"],
    )
    op.create_index(
        "ix_financial_invoices_student_id",
        "financial_invoices",
        ["student_id"],
    )
    op.create_index(
        "ix_financial_invoices_contract_id",
        "financial_invoices",
        ["contract_id"],
    )
    op.create_index(
        "ix_financial_invoices_enrollment_id",
        "financial_invoices",
        ["enrollment_id"],
    )
    op.create_index(
        "ix_financial_invoices_course_id",
        "financial_invoices",
        ["course_id"],
    )
    op.create_index(
        "ix_financial_invoice_scope",
        "financial_invoices",
        ["institution_id", "student_id", "course_id", "due_date"],
    )


def downgrade() -> None:
    op.drop_index("ix_financial_invoice_scope", table_name="financial_invoices")
    op.drop_index("ix_financial_invoices_course_id", table_name="financial_invoices")
    op.drop_index("ix_financial_invoices_enrollment_id", table_name="financial_invoices")
    op.drop_index("ix_financial_invoices_contract_id", table_name="financial_invoices")
    op.drop_index("ix_financial_invoices_student_id", table_name="financial_invoices")
    op.drop_index(
        "ix_financial_invoices_institution_id", table_name="financial_invoices"
    )
    op.drop_index("ix_financial_invoices_id", table_name="financial_invoices")
    op.drop_table("financial_invoices")

    op.drop_index("ix_financial_contract_scope", table_name="financial_contracts")
    op.drop_index("ix_financial_contracts_course_id", table_name="financial_contracts")
    op.drop_index(
        "ix_financial_contracts_enrollment_id", table_name="financial_contracts"
    )
    op.drop_index("ix_financial_contracts_student_id", table_name="financial_contracts")
    op.drop_index(
        "ix_financial_contracts_institution_id", table_name="financial_contracts"
    )
    op.drop_index("ix_financial_contracts_id", table_name="financial_contracts")
    op.drop_table("financial_contracts")

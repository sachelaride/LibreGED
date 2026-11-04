"""Link financial contracts and invoices to student guardians.

Revision ID: 20261108finguard
Revises: 20261107finreview
Create Date: 2026-11-03
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261108finguard"
down_revision: Union[str, Sequence[str], None] = "20261107finreview"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "financial_contracts",
        sa.Column("responsible_financial_id", sa.String(), nullable=True),
    )
    op.create_foreign_key(
        "fk_financial_contracts_responsible_financial_id_guardians",
        "financial_contracts",
        "guardians",
        ["responsible_financial_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_financial_contracts_responsible_financial_id",
        "financial_contracts",
        ["responsible_financial_id"],
    )

    op.add_column(
        "financial_invoices",
        sa.Column("responsible_financial_id", sa.String(), nullable=True),
    )
    op.create_foreign_key(
        "fk_financial_invoices_responsible_financial_id_guardians",
        "financial_invoices",
        "guardians",
        ["responsible_financial_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_financial_invoices_responsible_financial_id",
        "financial_invoices",
        ["responsible_financial_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_financial_invoices_responsible_financial_id",
        table_name="financial_invoices",
    )
    op.drop_constraint(
        "fk_financial_invoices_responsible_financial_id_guardians",
        "financial_invoices",
        type_="foreignkey",
    )
    op.drop_column("financial_invoices", "responsible_financial_id")

    op.drop_index(
        "ix_financial_contracts_responsible_financial_id",
        table_name="financial_contracts",
    )
    op.drop_constraint(
        "fk_financial_contracts_responsible_financial_id_guardians",
        "financial_contracts",
        type_="foreignkey",
    )
    op.drop_column("financial_contracts", "responsible_financial_id")

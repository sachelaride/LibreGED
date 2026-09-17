"""Add signature requests and link dossiers to GED documents.

Revision ID: b1c2d3e4f5a6
Revises: a1b2c3d4e5f6
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ged_signature_requests",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("document_id", sa.String(), nullable=False),
        sa.Column("signer_id", sa.String(), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(), nullable=False, server_default="PENDING"),
        sa.Column("requested_at", sa.DateTime(), nullable=True),
        sa.Column("signed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["document_id"], ["ged_documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["signer_id"], ["ged_signers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ged_signature_requests_document_id",
        "ged_signature_requests",
        ["document_id"],
        unique=False,
    )
    op.create_index(
        "ix_ged_signature_requests_signer_id",
        "ged_signature_requests",
        ["signer_id"],
        unique=False,
    )

    with op.batch_alter_table("dossier_documents", recreate="always") as batch_op:
        batch_op.drop_constraint("dossier_documents_document_id_fkey", type_="foreignkey")
        batch_op.create_foreign_key(
            "fk_dossier_documents_document_id_ged_documents",
            "ged_documents",
            ["document_id"],
            ["id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("dossier_documents", recreate="always") as batch_op:
        batch_op.drop_constraint(
            "fk_dossier_documents_document_id_ged_documents",
            type_="foreignkey",
        )
        batch_op.create_foreign_key(
            "dossier_documents_document_id_fkey",
            "ecm_nodes",
            ["document_id"],
            ["id"],
        )

    op.drop_index(
        "ix_ged_signature_requests_signer_id",
        table_name="ged_signature_requests",
    )
    op.drop_index(
        "ix_ged_signature_requests_document_id",
        table_name="ged_signature_requests",
    )
    op.drop_table("ged_signature_requests")

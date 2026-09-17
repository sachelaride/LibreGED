"""Add versioned XML visual representation services."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "e1f2a3b4c5d6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "representation_services",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("document_type", sa.String(), nullable=False),
        sa.Column("workflow_id", sa.String(), sa.ForeignKey("ged_workflows.id", ondelete="SET NULL"), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_representation_service_code"),
    )
    op.create_index("ix_representation_services_code", "representation_services", ["code"])
    op.create_index("ix_representation_services_document_type", "representation_services", ["document_type"])
    op.create_table(
        "representation_service_versions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("service_id", sa.String(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("version_label", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="DRAFT"),
        sa.Column("xslt_content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(), nullable=False),
        sa.Column("created_by_user_id", sa.String(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["service_id"], ["representation_services.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("service_id", "revision", name="uq_representation_service_revision"),
        sa.UniqueConstraint("service_id", "version_label", name="uq_representation_service_version_label"),
    )
    op.create_index("ix_representation_service_versions_service_id", "representation_service_versions", ["service_id"])
    op.create_index("ix_representation_service_versions_content_hash", "representation_service_versions", ["content_hash"])
    op.create_table(
        "representation_executions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("service_id", sa.String(), nullable=False),
        sa.Column("service_version_id", sa.String(), nullable=False),
        sa.Column("document_id", sa.String(), nullable=True),
        sa.Column("input_xml_hash", sa.String(), nullable=False),
        sa.Column("output_hash", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="PENDING"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("requested_by_user_id", sa.String(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["service_id"], ["representation_services.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["service_version_id"], ["representation_service_versions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["document_id"], ["ged_documents.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_representation_executions_service_id", "representation_executions", ["service_id"])
    op.create_index("ix_representation_executions_service_version_id", "representation_executions", ["service_version_id"])
    op.create_index("ix_representation_executions_document_id", "representation_executions", ["document_id"])
    op.create_index("ix_representation_executions_status", "representation_executions", ["status"])


def downgrade() -> None:
    op.drop_table("representation_executions")
    op.drop_table("representation_service_versions")
    op.drop_table("representation_services")

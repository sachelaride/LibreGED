"""Persist ECM file version history."""

from alembic import op
import sqlalchemy as sa
import uuid

revision = "f0a1b2c3d4e5"
down_revision = "e9f0a1b2c3d4"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ecm_node_versions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("node_id", sa.String(), nullable=False),
        sa.Column("major_version", sa.Integer(), nullable=False),
        sa.Column("minor_version", sa.Integer(), nullable=False),
        sa.Column("file_name", sa.String(), nullable=False),
        sa.Column("stored_path", sa.String(), nullable=False),
        sa.Column("checksum", sa.String(), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("mime_type", sa.String(), nullable=True),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["node_id"], ["ecm_nodes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_ecm_node_versions_node_id", "ecm_node_versions", ["node_id"])

    bind = op.get_bind()
    rows = bind.execute(sa.text(
        "SELECT id, major_version, minor_version, properties, created_by, created_at "
        "FROM ecm_nodes WHERE properties ? 'cm:content'"
    ))
    for row in rows:
        content = row.properties.get("cm:content", {})
        if not content.get("stored_path") or not content.get("checksum"):
            continue
        bind.execute(sa.text(
            "INSERT INTO ecm_node_versions "
            "(id, node_id, major_version, minor_version, file_name, stored_path, checksum, size, mime_type, created_by, created_at) "
            "VALUES (:id, :node_id, :major, :minor, :file_name, :path, :checksum, :size, :mime, :created_by, :created_at)"
        ), {
            "id": str(uuid.uuid4()), "node_id": row.id,
            "major": row.major_version, "minor": row.minor_version,
            "file_name": content.get("file_name", "arquivo"),
            "path": content["stored_path"], "checksum": content["checksum"],
            "size": content.get("size", 0), "mime": content.get("mime_type"),
            "created_by": row.created_by, "created_at": row.created_at,
        })


def downgrade():
    op.drop_index("ix_ecm_node_versions_node_id", table_name="ecm_node_versions")
    op.drop_table("ecm_node_versions")

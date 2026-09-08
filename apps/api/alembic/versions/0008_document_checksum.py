"""Add document content checksums.

Revision ID: 0008_document_checksum
Revises: 0007_audit_events
Create Date: 2026-09-08
"""

from alembic import op
import sqlalchemy as sa

revision = "0008_document_checksum"
down_revision = "0007_audit_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "patient_documents",
        sa.Column("sha256", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ix_patient_documents_sha256",
        "patient_documents",
        ["sha256"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_patient_documents_sha256", table_name="patient_documents")
    op.drop_column("patient_documents", "sha256")

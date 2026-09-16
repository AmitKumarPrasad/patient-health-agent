"""Add durable document-ingestion retry metadata.

Revision ID: 0011_document_ingestion_retry
Revises: 0010_document_ingestion_status
Create Date: 2026-09-16
"""

from alembic import op
import sqlalchemy as sa

revision = "0011_document_ingestion_retry"
down_revision = "0010_document_ingestion_status"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "patient_documents",
        sa.Column("ingestion_attempts", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "patient_documents",
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "patient_documents",
        sa.Column("processing_started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_patient_documents_next_attempt_at",
        "patient_documents",
        ["next_attempt_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_patient_documents_next_attempt_at", table_name="patient_documents")
    op.drop_column("patient_documents", "processing_started_at")
    op.drop_column("patient_documents", "next_attempt_at")
    op.drop_column("patient_documents", "ingestion_attempts")

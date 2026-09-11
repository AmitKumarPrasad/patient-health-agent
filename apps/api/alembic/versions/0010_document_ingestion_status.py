"""Track document RAG ingestion status.

Revision ID: 0010_document_ingestion_status
Revises: 0009_pgvector_embeddings
Create Date: 2026-09-11
"""

from alembic import op
import sqlalchemy as sa

revision = "0010_document_ingestion_status"
down_revision = "0009_pgvector_embeddings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "patient_documents",
        sa.Column("ingestion_status", sa.String(length=20), nullable=False, server_default="ready"),
    )
    op.add_column(
        "patient_documents",
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "patient_documents",
        sa.Column("indexed_chunks", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "patient_documents",
        sa.Column("ingestion_error", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_patient_documents_ingestion_status",
        "patient_documents",
        ["ingestion_status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_patient_documents_ingestion_status", table_name="patient_documents")
    op.drop_column("patient_documents", "ingestion_error")
    op.drop_column("patient_documents", "indexed_chunks")
    op.drop_column("patient_documents", "indexed_at")
    op.drop_column("patient_documents", "ingestion_status")

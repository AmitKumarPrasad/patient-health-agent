"""Add patient-scoped document chunks for RAG.

Revision ID: 0006_document_chunks
Revises: 0005_patient_documents
Create Date: 2026-09-08
"""

from alembic import op
import sqlalchemy as sa

revision = "0006_document_chunks"
down_revision = "0005_patient_documents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "patient_document_chunks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("patient_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["patient_documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id", "chunk_index", name="uq_document_chunk_index"),
    )
    op.create_index("ix_patient_document_chunks_document_id", "patient_document_chunks", ["document_id"], unique=False)
    op.create_index("ix_patient_document_chunks_patient_id", "patient_document_chunks", ["patient_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_patient_document_chunks_patient_id", table_name="patient_document_chunks")
    op.drop_index("ix_patient_document_chunks_document_id", table_name="patient_document_chunks")
    op.drop_table("patient_document_chunks")

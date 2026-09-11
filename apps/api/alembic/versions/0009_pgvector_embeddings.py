"""Store document embeddings in PostgreSQL pgvector.

Revision ID: 0009_pgvector_embeddings
Revises: 0008_document_checksum
Create Date: 2026-09-11
"""

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import VECTOR

revision = "0009_pgvector_embeddings"
down_revision = "0008_document_checksum"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.drop_column("patient_document_chunks", "embedding")
    op.add_column(
        "patient_document_chunks",
        sa.Column("embedding", VECTOR(1536), nullable=True),
    )
    op.create_index(
        "ix_patient_document_chunks_embedding_hnsw",
        "patient_document_chunks",
        ["embedding"],
        unique=False,
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
        postgresql_with={"m": 16, "ef_construction": 64},
    )


def downgrade() -> None:
    op.drop_index(
        "ix_patient_document_chunks_embedding_hnsw",
        table_name="patient_document_chunks",
    )
    op.drop_column("patient_document_chunks", "embedding")
    op.add_column(
        "patient_document_chunks",
        sa.Column("embedding", sa.JSON(), nullable=True),
    )

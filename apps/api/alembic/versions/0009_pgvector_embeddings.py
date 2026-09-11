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
    op.add_column(
        "patient_document_chunks",
        sa.Column("embedding_vector", VECTOR(1536), nullable=True),
    )
    op.execute(
        """
        UPDATE patient_document_chunks
        SET embedding_vector = embedding::text::vector
        WHERE embedding IS NOT NULL
          AND jsonb_typeof(embedding::jsonb) = 'array'
          AND jsonb_array_length(embedding::jsonb) = 1536
        """
    )
    op.drop_column("patient_document_chunks", "embedding")
    op.alter_column(
        "patient_document_chunks",
        "embedding_vector",
        new_column_name="embedding",
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
    op.add_column(
        "patient_document_chunks",
        sa.Column("embedding_json", sa.JSON(), nullable=True),
    )
    op.execute(
        """
        UPDATE patient_document_chunks
        SET embedding_json = embedding::text::json
        WHERE embedding IS NOT NULL
        """
    )
    op.drop_column("patient_document_chunks", "embedding")
    op.alter_column(
        "patient_document_chunks",
        "embedding_json",
        new_column_name="embedding",
    )

"""Add patient document metadata table.

Revision ID: 0005_patient_documents
Revises: 0004_notifications
Create Date: 2026-09-08
"""

from alembic import op
import sqlalchemy as sa

revision = "0005_patient_documents"
down_revision = "0004_notifications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "patient_documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("patient_id", sa.Uuid(), nullable=False),
        sa.Column("object_key", sa.String(length=500), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=150), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("object_key"),
    )
    op.create_index("ix_patient_documents_patient_id", "patient_documents", ["patient_id"], unique=False)
    op.create_index("ix_patient_documents_object_key", "patient_documents", ["object_key"], unique=True)
    op.create_index("ix_patient_documents_category", "patient_documents", ["category"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_patient_documents_category", table_name="patient_documents")
    op.drop_index("ix_patient_documents_object_key", table_name="patient_documents")
    op.drop_index("ix_patient_documents_patient_id", table_name="patient_documents")
    op.drop_table("patient_documents")

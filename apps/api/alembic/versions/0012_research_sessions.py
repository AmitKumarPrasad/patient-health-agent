"""Add persistent public research sessions.

Revision ID: 0012_research_sessions
Revises: 0011_document_ingestion_retry
"""
from alembic import op
import sqlalchemy as sa

revision = "0012_research_sessions"
down_revision = "0011_document_ingestion_retry"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "research_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_subject", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_research_sessions_owner_subject", "research_sessions", ["owner_subject"])
    op.create_index("ix_research_sessions_owner_updated_at", "research_sessions", ["owner_subject", "updated_at"])

    op.create_table(
        "research_messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("sources", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["research_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_research_messages_session_id", "research_messages", ["session_id"])
    op.create_index("ix_research_messages_session_created_at", "research_messages", ["session_id", "created_at"])
    op.create_index("ix_research_messages_created_at", "research_messages", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_research_messages_created_at", table_name="research_messages")
    op.drop_index("ix_research_messages_session_created_at", table_name="research_messages")
    op.drop_index("ix_research_messages_session_id", table_name="research_messages")
    op.drop_table("research_messages")
    op.drop_index("ix_research_sessions_owner_updated_at", table_name="research_sessions")
    op.drop_index("ix_research_sessions_owner_subject", table_name="research_sessions")
    op.drop_table("research_sessions")

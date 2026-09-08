"""Add Keycloak identity mapping for providers.

Revision ID: 0002_provider_external_id
Revises: 0001_initial_schema
Create Date: 2026-09-08
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_provider_external_id"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("providers", sa.Column("external_id", sa.String(100), nullable=True))
    op.create_index("ix_providers_external_id", "providers", ["external_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_providers_external_id", table_name="providers")
    op.drop_column("providers", "external_id")

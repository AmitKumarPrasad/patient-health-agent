"""Add idempotent appointment notifications.

Revision ID: 0004_notifications
Revises: 0003_demo_identity_seed
Create Date: 2026-09-08
"""

from alembic import op
import sqlalchemy as sa

revision = "0004_notifications"
down_revision = "0003_demo_identity_seed"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("appointment_id", sa.Uuid(), nullable=False),
        sa.Column("notification_type", sa.String(length=50), nullable=False),
        sa.Column("channel", sa.String(length=20), nullable=False),
        sa.Column("recipient", sa.String(length=320), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["appointment_id"], ["appointments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "appointment_id",
            "notification_type",
            "channel",
            name="uq_notification_appointment_type_channel",
        ),
    )
    op.create_index("ix_notifications_appointment_id", "notifications", ["appointment_id"], unique=False)
    op.create_index("ix_notifications_notification_type", "notifications", ["notification_type"], unique=False)
    op.create_index("ix_notifications_scheduled_for", "notifications", ["scheduled_for"], unique=False)
    op.create_index("ix_notifications_status", "notifications", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_notifications_status", table_name="notifications")
    op.drop_index("ix_notifications_scheduled_for", table_name="notifications")
    op.drop_index("ix_notifications_notification_type", table_name="notifications")
    op.drop_index("ix_notifications_appointment_id", table_name="notifications")
    op.drop_table("notifications")

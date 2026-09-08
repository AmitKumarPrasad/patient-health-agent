"""Create initial healthcare scheduling schema.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-09-08
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "patients",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("external_id", sa.String(100), nullable=True),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("email", sa.String(320), nullable=True),
        sa.Column("phone", sa.String(30), nullable=True),
        sa.Column("date_of_birth", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_id"),
    )
    op.create_index("ix_patients_external_id", "patients", ["external_id"], unique=True)
    op.create_index("ix_patients_email", "patients", ["email"], unique=False)
    op.create_index("ix_patients_phone", "patients", ["phone"], unique=False)

    op.create_table(
        "providers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("specialty", sa.String(150), nullable=False),
        sa.Column("email", sa.String(320), nullable=True),
        sa.Column("phone", sa.String(30), nullable=True),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_providers_specialty", "providers", ["specialty"], unique=False)
    op.create_index("ix_providers_email", "providers", ["email"], unique=True)

    op.create_table(
        "provider_availability",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("provider_id", sa.Uuid(), nullable=False),
        sa.Column("available_date", sa.Date(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("is_available", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["provider_id"], ["providers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider_id", "available_date", "start_time", name="uq_provider_availability_slot"),
    )
    op.create_index("ix_provider_availability_provider_id", "provider_availability", ["provider_id"], unique=False)
    op.create_index("ix_provider_availability_available_date", "provider_availability", ["available_date"], unique=False)

    op.create_table(
        "appointments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("patient_id", sa.Uuid(), nullable=False),
        sa.Column("provider_id", sa.Uuid(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("appointment_type", sa.String(50), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["provider_id"], ["providers.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_appointments_patient_id", "appointments", ["patient_id"], unique=False)
    op.create_index("ix_appointments_provider_id", "appointments", ["provider_id"], unique=False)
    op.create_index("ix_appointments_starts_at", "appointments", ["starts_at"], unique=False)
    op.create_index("ix_appointments_status", "appointments", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_appointments_status", table_name="appointments")
    op.drop_index("ix_appointments_starts_at", table_name="appointments")
    op.drop_index("ix_appointments_provider_id", table_name="appointments")
    op.drop_index("ix_appointments_patient_id", table_name="appointments")
    op.drop_table("appointments")

    op.drop_index("ix_provider_availability_available_date", table_name="provider_availability")
    op.drop_index("ix_provider_availability_provider_id", table_name="provider_availability")
    op.drop_table("provider_availability")

    op.drop_index("ix_providers_email", table_name="providers")
    op.drop_index("ix_providers_specialty", table_name="providers")
    op.drop_table("providers")

    op.drop_index("ix_patients_phone", table_name="patients")
    op.drop_index("ix_patients_email", table_name="patients")
    op.drop_index("ix_patients_external_id", table_name="patients")
    op.drop_table("patients")

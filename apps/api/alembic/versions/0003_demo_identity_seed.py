"""Seed local demo identities and provider availability.

Revision ID: 0003_demo_identity_seed
Revises: 0002_provider_external_id
Create Date: 2026-09-08
"""

from datetime import datetime, time, timezone
from uuid import UUID

from alembic import op
import sqlalchemy as sa

revision = "0003_demo_identity_seed"
down_revision = "0002_provider_external_id"
branch_labels = None
depends_on = None

PATIENT_ID = UUID("7f7d4cc2-8c35-4e7c-a1e2-5b5d1c01a101")
PROVIDER_ID = UUID("7f7d4cc2-8c35-4e7c-a1e2-5b5d1c01a102")
AVAILABILITY_IDS = [
    UUID("7f7d4cc2-8c35-4e7c-a1e2-5b5d1c01a201"),
    UUID("7f7d4cc2-8c35-4e7c-a1e2-5b5d1c01a202"),
    UUID("7f7d4cc2-8c35-4e7c-a1e2-5b5d1c01a203"),
]


def upgrade() -> None:
    patients = sa.table(
        "patients",
        sa.column("id", sa.Uuid()),
        sa.column("external_id", sa.String()),
        sa.column("first_name", sa.String()),
        sa.column("last_name", sa.String()),
        sa.column("email", sa.String()),
        sa.column("phone", sa.String()),
    )
    providers = sa.table(
        "providers",
        sa.column("id", sa.Uuid()),
        sa.column("external_id", sa.String()),
        sa.column("first_name", sa.String()),
        sa.column("last_name", sa.String()),
        sa.column("specialty", sa.String()),
        sa.column("email", sa.String()),
        sa.column("phone", sa.String()),
        sa.column("bio", sa.Text()),
    )
    availability = sa.table(
        "provider_availability",
        sa.column("id", sa.Uuid()),
        sa.column("provider_id", sa.Uuid()),
        sa.column("available_date", sa.Date()),
        sa.column("start_time", sa.Time()),
        sa.column("end_time", sa.Time()),
        sa.column("is_available", sa.Boolean()),
    )

    op.execute(
        sa.insert(patients).values(
            id=PATIENT_ID,
            external_id=str(PATIENT_ID),
            first_name="Demo",
            last_name="Patient",
            email="demo.patient@example.local",
            phone="+91-9000000001",
        )
    )
    op.execute(
        sa.insert(providers).values(
            id=PROVIDER_ID,
            external_id=str(PROVIDER_ID),
            first_name="Demo",
            last_name="Provider",
            specialty="General Medicine",
            email="demo.provider@example.local",
            phone="+91-9000000002",
            bio="Demo provider for local development and client walkthroughs.",
        )
    )

    demo_dates = [datetime(2026, 9, day, tzinfo=timezone.utc).date() for day in (9, 10, 11)]
    rows = [
        {
            "id": slot_id,
            "provider_id": PROVIDER_ID,
            "available_date": demo_date,
            "start_time": time(10, 0),
            "end_time": time(10, 30),
            "is_available": True,
        }
        for slot_id, demo_date in zip(AVAILABILITY_IDS, demo_dates, strict=True)
    ]
    op.execute(sa.insert(availability), rows)


def downgrade() -> None:
    op.execute(
        sa.text("DELETE FROM provider_availability WHERE id IN (:a, :b, :c)").bindparams(
            a=AVAILABILITY_IDS[0], b=AVAILABILITY_IDS[1], c=AVAILABILITY_IDS[2]
        )
    )
    op.execute(sa.text("DELETE FROM providers WHERE id = :id").bindparams(id=PROVIDER_ID))
    op.execute(sa.text("DELETE FROM patients WHERE id = :id").bindparams(id=PATIENT_ID))

from __future__ import annotations

import os
import sys
from datetime import date, datetime
from uuid import UUID

from mcp.server.dependencies import get_http_headers
from mcp.server.fastmcp import FastMCP

sys.path.append(os.path.abspath("../api"))

from app.db.session import SessionLocal
from app.services.appointment_tools import book_appointment, get_available_slots, search_providers
from app.services.audit import record_event
from app.services.patient_identity import require_patient_by_external_id
from app.services.record_tools import search_patient_documents


mcp = FastMCP("patient-health-agent", stateless_http=True, json_response=True)


def _authenticated_subject() -> str:
    """Read the patient identity injected by the authenticated API gateway."""
    subject = get_http_headers().get("x-patient-subject", "").strip()
    if not subject:
        raise PermissionError("Authenticated patient context is required")
    return subject


def _audit_record_search(db, patient_subject, patient_id, result_count: int) -> None:
    try:
        record_event(
            db,
            actor_subject=patient_subject,
            actor_role="patient",
            action="record.search",
            resource_type="patient_document",
            patient_id=patient_id,
            metadata={"result_count": result_count},
        )
    except Exception:
        db.rollback()


def _audit_appointment_booking(db, patient_subject, patient_id, result: dict) -> None:
    try:
        record_event(
            db,
            actor_subject=patient_subject,
            actor_role="patient",
            action="appointment.booked",
            resource_type="appointment",
            resource_id=result["id"],
            patient_id=patient_id,
            metadata={
                "provider_id": result["provider_id"],
                "starts_at": result["starts_at"],
                "ends_at": result["ends_at"],
                "source": "mcp",
            },
        )
    except Exception:
        db.rollback()


@mcp.tool()
def find_providers(specialty: str) -> list[dict]:
    """Find providers using the application's validated provider search service."""
    with SessionLocal() as db:
        return search_providers(db, specialty)


@mcp.tool()
def available_slots(provider_id: str, requested_date: str) -> list[dict]:
    """Return currently available slots for a provider on an ISO date."""
    with SessionLocal() as db:
        return get_available_slots(db, UUID(provider_id), date.fromisoformat(requested_date))


@mcp.tool()
def patient_records(query: str = "") -> list[dict]:
    """Search record metadata for the authenticated patient."""
    subject = _authenticated_subject()
    with SessionLocal() as db:
        patient = require_patient_by_external_id(db, subject)
        try:
            results = search_patient_documents(query, subject)
        except Exception:
            _audit_record_search(db, subject, patient.id, 0)
            raise
        _audit_record_search(db, subject, patient.id, len(results))
        return results


@mcp.tool()
def book_slot(
    provider_id: str,
    starts_at: str,
    ends_at: str,
    reason: str = "",
) -> dict:
    """Book an appointment for the authenticated patient through the validated service layer."""
    subject = _authenticated_subject()
    with SessionLocal() as db:
        patient = require_patient_by_external_id(db, subject)
        result = book_appointment(
            db,
            patient_id=patient.id,
            provider_id=UUID(provider_id),
            starts_at=datetime.fromisoformat(starts_at),
            ends_at=datetime.fromisoformat(ends_at),
            reason=reason or None,
        )
        _audit_appointment_booking(db, subject, patient.id, result)
        return result


if __name__ == "__main__":
    transport = os.getenv("MCP_TRANSPORT", "stdio").strip().lower()
    if transport == "streamable-http":
        mcp.run(
            transport="streamable-http",
            host=os.getenv("MCP_HOST", "0.0.0.0"),
            port=int(os.getenv("MCP_PORT", "8000")),
        )
    elif transport == "stdio":
        mcp.run(transport="stdio")
    else:
        raise ValueError("MCP_TRANSPORT must be 'stdio' or 'streamable-http'")

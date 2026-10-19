from types import SimpleNamespace

import pytest

import server


class _FakeSession:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False


def _context(headers):
    return SimpleNamespace(
        request_context=SimpleNamespace(
            request=SimpleNamespace(headers=headers),
        ),
    )


def test_patient_records_uses_only_authenticated_gateway_subject(monkeypatch) -> None:
    calls = {}
    session = _FakeSession()

    monkeypatch.setattr(server, "SessionLocal", lambda: session)
    monkeypatch.setattr(
        server,
        "require_patient_by_external_id",
        lambda db, subject: calls.update(patient_lookup=(db, subject))
        or SimpleNamespace(id="synthetic-patient-id"),
    )
    monkeypatch.setattr(
        server,
        "search_patient_documents",
        lambda query, subject: calls.update(search=(query, subject)) or [{"document_id": "synthetic-doc"}],
    )
    monkeypatch.setattr(server, "_audit_record_search", lambda *args: None)

    result = server.patient_records(
        "synthetic records query",
        _context({"x-patient-subject": " patient-a "}),
    )

    assert result == [{"document_id": "synthetic-doc"}]
    assert calls["patient_lookup"] == (session, "patient-a")
    assert calls["search"] == ("synthetic records query", "patient-a")


@pytest.mark.parametrize(
    "context",
    [
        None,
        _context({}),
        _context({"x-patient-subject": "   "}),
    ],
)
def test_patient_records_rejects_missing_gateway_identity_before_database_access(
    monkeypatch,
    context,
) -> None:
    monkeypatch.setattr(
        server,
        "SessionLocal",
        lambda: pytest.fail("database must not be opened without authenticated patient context"),
    )

    with pytest.raises(PermissionError, match="Authenticated patient context is required"):
        server.patient_records("synthetic records query", context)

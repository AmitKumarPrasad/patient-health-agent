import logging

from app.observability.safe_logging import PHISafeLogFilter, safe_log_exception


def test_phi_safe_filter_redacts_sensitive_values_and_exception_info() -> None:
    record = logging.LogRecord(
        name="test",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg="Authorization: Bearer secret-token email=patient@example.com password=hunter2",
        args=(),
        exc_info=(ValueError, ValueError("patient diagnosis"), None),
    )

    assert PHISafeLogFilter().filter(record) is True
    message = record.getMessage()
    assert "secret-token" not in message
    assert "patient@example.com" not in message
    assert "hunter2" not in message
    assert "patient diagnosis" not in message
    assert "[REDACTED]" in message
    assert record.exc_info is None


def test_safe_log_exception_contains_only_allowlisted_context(caplog) -> None:
    logger = logging.getLogger("test.safe")
    logger.addFilter(PHISafeLogFilter())

    with caplog.at_level(logging.ERROR, logger="test.safe"):
        safe_log_exception(
            logger,
            "document_ingestion_failed",
            ValueError("patient@example.com diagnosis=confidential"),
            document_id="document-123",
            patient_name="Sensitive Patient",
        )

    message = caplog.records[-1].getMessage()
    assert "document_ingestion_failed" in message
    assert "exception_type=ValueError" in message
    assert "document_id=document-123" in message
    assert "patient@example.com" not in message
    assert "Sensitive Patient" not in message
    assert "confidential" not in message

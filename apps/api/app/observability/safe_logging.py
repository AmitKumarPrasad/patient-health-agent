from __future__ import annotations

import logging
import re
from collections.abc import Mapping, Sequence
from typing import Any


_SENSITIVE_PATTERNS = (
    re.compile(r"(?i)(authorization\s*[:=]\s*bearer\s+)[^\s,;]+"),
    re.compile(r"(?i)(authorization\s*[:=]\s*)[^\s,;]+"),
    re.compile(r"(?i)(x-api-key\s*[:=]\s*)[^\s,;]+"),
    re.compile(r"(?i)(token\s*[:=]\s*)[^\s,;]+"),
    re.compile(r"(?i)(password\s*[:=]\s*)[^\s,;]+"),
    re.compile(r"(?i)(secret\s*[:=]\s*)[^\s,;]+"),
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
)


class PHISafeLogFilter(logging.Filter):
    """Defense-in-depth filter that removes common secrets/identifiers from logs."""

    def filter(self, record: logging.LogRecord) -> bool:
        if record.exc_info is not None:
            record.exc_info = None
            record.exc_text = None

        message = record.getMessage()
        for pattern in _SENSITIVE_PATTERNS:
            message = pattern.sub(r"\1[REDACTED]" if pattern.groups else "[REDACTED]", message)
        record.msg = message
        record.args = ()
        return True


def safe_log_exception(logger: logging.Logger, event: str, exc: BaseException, **context: Any) -> None:
    """Log an error event without exception text, traceback, request data, or PHI."""
    fields = {"event": event, "exception_type": type(exc).__name__}
    fields.update({key: value for key, value in context.items() if key in {"request_id", "document_id"}})
    logger.error("safe_error %s", " ".join(f"{key}={value}" for key, value in fields.items()))

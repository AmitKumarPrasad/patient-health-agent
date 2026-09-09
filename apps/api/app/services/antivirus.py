from __future__ import annotations

import socket

from app.config import settings


class AntivirusError(RuntimeError):
    """Raised when the configured antivirus scanner cannot be used."""


class AntivirusInfectedError(ValueError):
    """Raised when the antivirus scanner identifies malicious content."""


def scan_content(content: bytes) -> None:
    """Scan content with ClamAV when enabled; fail closed if scanning is unavailable."""
    if not settings.antivirus_enabled:
        return

    try:
        with socket.create_connection(
            (settings.antivirus_host, settings.antivirus_port),
            timeout=settings.antivirus_timeout_seconds,
        ) as client:
            client.sendall(b"zINSTREAM" + bytes([0]))
            for offset in range(0, len(content), 1024 * 1024):
                chunk = content[offset : offset + 1024 * 1024]
                client.sendall(len(chunk).to_bytes(4, "big"))
                client.sendall(chunk)
            client.sendall((0).to_bytes(4, "big"))
            response = client.recv(4096).decode("utf-8", errors="replace").strip().rstrip(chr(0))
    except (OSError, TimeoutError) as exc:
        raise AntivirusError("Antivirus scanner is unavailable") from exc

    if response.endswith("FOUND"):
        raise AntivirusInfectedError("Document failed antivirus scanning")
    if not response.endswith("OK"):
        raise AntivirusError("Antivirus scanner returned an invalid response")

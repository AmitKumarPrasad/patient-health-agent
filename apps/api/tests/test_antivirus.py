from __future__ import annotations

import socket

import pytest

from app.services import antivirus


def test_scan_content_is_noop_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(antivirus.settings, "antivirus_enabled", False)

    def fail_connect(*args: object, **kwargs: object) -> socket.socket:
        raise AssertionError("scanner should not be contacted when disabled")

    monkeypatch.setattr(socket, "create_connection", fail_connect)
    antivirus.scan_content(b"hello")


def test_scan_content_accepts_clean_result(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(antivirus.settings, "antivirus_enabled", True)
    calls: list[bytes] = []

    class FakeSocket:
        def __enter__(self) -> "FakeSocket":
            return self

        def __exit__(self, *_args: object) -> None:
            pass

        def sendall(self, data: bytes) -> None:
            calls.append(data)

        def recv(self, _size: int) -> bytes:
            return b"stream: OK\x00"

    monkeypatch.setattr(socket, "create_connection", lambda *args, **kwargs: FakeSocket())

    antivirus.scan_content(b"hello")

    assert calls[0] == b"zINSTREAM\0"
    assert calls[1] == b"\x00\x00\x00\x05"
    assert calls[2] == b"hello"
    assert calls[3] == b"\x00\x00\x00\x00"


def test_scan_content_rejects_infected_result(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(antivirus.settings, "antivirus_enabled", True)

    class FakeSocket:
        def __enter__(self) -> "FakeSocket":
            return self

        def __exit__(self, *_args: object) -> None:
            pass

        def sendall(self, _data: bytes) -> None:
            pass

        def recv(self, _size: int) -> bytes:
            return b"stream: Eicar-Test-Signature FOUND\x00"

    monkeypatch.setattr(socket, "create_connection", lambda *args, **kwargs: FakeSocket())

    with pytest.raises(antivirus.AntivirusInfectedError, match="failed antivirus scanning"):
        antivirus.scan_content(b"malware")


def test_scan_content_fails_closed_when_scanner_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(antivirus.settings, "antivirus_enabled", True)

    def fail_connect(*args: object, **kwargs: object) -> socket.socket:
        raise ConnectionRefusedError("scanner unavailable")

    monkeypatch.setattr(socket, "create_connection", fail_connect)

    with pytest.raises(antivirus.AntivirusError, match="scanner is unavailable"):
        antivirus.scan_content(b"hello")


def test_scan_content_rejects_invalid_scanner_response(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(antivirus.settings, "antivirus_enabled", True)

    class FakeSocket:
        def __enter__(self) -> "FakeSocket":
            return self

        def __exit__(self, *_args: object) -> None:
            pass

        def sendall(self, _data: bytes) -> None:
            pass

        def recv(self, _size: int) -> bytes:
            return b"unexpected response\x00"

    monkeypatch.setattr(socket, "create_connection", lambda *args, **kwargs: FakeSocket())

    with pytest.raises(antivirus.AntivirusError, match="invalid response"):
        antivirus.scan_content(b"hello")

"""Tests for the standalone deployment smoke check."""
import importlib.util
import json
from pathlib import Path
from unittest.mock import patch

import pytest

MODULE_PATH = Path(__file__).resolve().parents[3] / "ops" / "smoke" / "check_deployment.py"
spec = importlib.util.spec_from_file_location("deployment_smoke", MODULE_PATH)
assert spec is not None and spec.loader is not None
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)


@pytest.mark.parametrize("url", [
    "http://api.example.com",
    "https://user:password@api.example.com",
    "https://api.example.com/private",
    "https://api.example.com?secret=1",
])
def test_reject_unsafe_api_origins(url):
    with pytest.raises(ValueError):
        smoke.validate_url(url, False)


def test_allow_local_http_only_with_flag():
    with pytest.raises(ValueError):
        smoke.validate_url("http://localhost:8000", False)
    assert smoke.validate_url("http://localhost:8000", True) == "http://localhost:8000"


def test_endpoint_checks_status_and_payload():
    class Response:
        status = 200
        headers = {"Content-Type": "application/json", "Cache-Control": "no-store", "X-Frame-Options": "DENY", "X-Content-Type-Options": "nosniff"}
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def read(self, maximum):
            return json.dumps({"status": "ready"}).encode()

    with patch.object(smoke, "urlopen", return_value=Response()) as opener:
        smoke.check_endpoint("https://api.example.com", "/ready", "ready")
    assert opener.call_args.kwargs["timeout"] == 10


def test_endpoint_rejects_not_ready_response():
    class Response:
        status = 200
        headers = {"Content-Type": "application/json"}
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def read(self, maximum):
            return b'{"status":"not_ready"}'

    with patch.object(smoke, "urlopen", return_value=Response()):
        with pytest.raises(RuntimeError, match="unexpected health status"):
            smoke.check_endpoint("https://api.example.com", "/ready", "ready")


def test_endpoint_rejects_missing_security_headers():
    class Response:
        status = 200
        headers = {"Content-Type": "application/json"}
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def read(self, maximum):
            return b'{"status":"ok"}'

    with patch.object(smoke, "urlopen", return_value=Response()):
        with pytest.raises(RuntimeError, match="missing no-store cache protection"):
            smoke.check_endpoint("https://api.example.com", "/health", "ok")

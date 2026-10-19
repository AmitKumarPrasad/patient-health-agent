#!/usr/bin/env python3
"""Synthetic, unauthenticated deployment smoke check; no patient data."""
import argparse
import json
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


def check_endpoint(base_url: str, path: str, expected: str, timeout: float = 10) -> None:
    request = Request(base_url.rstrip("/") + path, headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=timeout) as response:
            status = response.status
            content_type = response.headers.get("Content-Type", "")
            cache_control = response.headers.get("Cache-Control", "")
            frame_options = response.headers.get("X-Frame-Options", "")
            content_type_options = response.headers.get("X-Content-Type-Options", "")
            body = response.read(4096)
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(f"{path}: request failed ({type(exc).__name__})") from None
    if status != 200:
        raise RuntimeError(f"{path}: expected HTTP 200, got {status}")
    if "no-store" not in [part.strip().lower() for part in cache_control.split(",")]:
        raise RuntimeError(f"{path}: missing no-store cache protection")
    if frame_options.upper() != "DENY":
        raise RuntimeError(f"{path}: missing DENY clickjacking protection")
    if content_type_options.lower() != "nosniff":
        raise RuntimeError(f"{path}: missing nosniff MIME protection")
    if "application/json" not in content_type.lower():
        raise RuntimeError(f"{path}: expected JSON response")
    try:
        payload = json.loads(body)
    except (ValueError, UnicodeDecodeError):
        raise RuntimeError(f"{path}: invalid JSON response") from None
    if not isinstance(payload, dict) or payload.get("status") != expected:
        raise RuntimeError(f"{path}: unexpected health status") from None
    print(f"PASS {path}: {expected}")


def validate_url(url: str, allow_local_http: bool) -> str:
    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower()
    if parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ("", "/"):
        raise ValueError("Supply only the API origin, without credentials, paths or queries")
    if parsed.scheme == "https" and host:
        return url.rstrip("/")
    if allow_local_http and parsed.scheme == "http" and host in ("localhost", "127.0.0.1", "::1"):
        return url.rstrip("/")
    raise ValueError("HTTPS is required; --allow-local-http permits loopback development only")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate an API deployment using synthetic health checks")
    parser.add_argument("api_origin", help="e.g. https://api.example.com")
    parser.add_argument("--allow-local-http", action="store_true", help="allow HTTP only for localhost/loopback")
    parser.add_argument("--timeout", type=float, default=10)
    args = parser.parse_args()
    try:
        if args.timeout <= 0:
            raise ValueError("timeout must be positive")
        origin = validate_url(args.api_origin, args.allow_local_http)
        check_endpoint(origin, "/health", "ok", args.timeout)
        check_endpoint(origin, "/ready", "ready", args.timeout)
    except ValueError as exc:
        print(f"Invalid configuration: {exc}", file=sys.stderr)
        return 2
    except RuntimeError as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1
    print("API deployment smoke check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())

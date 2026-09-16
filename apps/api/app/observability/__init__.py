from __future__ import annotations

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest


HTTP_REQUESTS_TOTAL = Counter(
    "patient_health_http_requests_total",
    "Total HTTP requests handled by the API.",
    ("method", "route", "status_code"),
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "patient_health_http_request_duration_seconds",
    "HTTP request duration in seconds.",
    ("method", "route"),
)


def observe_http_request(*, method: str, route: str, status_code: int, duration_seconds: float) -> None:
    HTTP_REQUESTS_TOTAL.labels(method, route, str(status_code)).inc()
    HTTP_REQUEST_DURATION_SECONDS.labels(method, route).observe(duration_seconds)


def prometheus_response() -> tuple[bytes, str]:
    return generate_latest(), CONTENT_TYPE_LATEST

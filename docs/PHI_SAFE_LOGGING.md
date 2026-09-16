# PHI-safe application logging

The API and background workers follow a **data-minimizing logging policy**. Logs are operational telemetry, not a copy of patient, document, or request data.

## Never log

- `Authorization` headers, bearer tokens, API keys, passwords, secrets, cookies, or session credentials
- HTTP request or response bodies
- Patient names, email addresses, phone numbers, addresses, dates of birth, or other direct identifiers
- Clinical notes, diagnoses, document text, extracted document content, embeddings, or uploaded file contents
- Full exception messages or tracebacks when they can contain request, document, or provider data

## Safe operational fields

Prefer:

- event name / operation name
- HTTP method and route template
- status code and latency
- request correlation ID
- exception class name
- non-sensitive internal document identifier when operationally necessary
- aggregate counts

## Defense in depth

`app.observability.safe_logging.PHISafeLogFilter` redacts common credential/identifier patterns and removes exception information from records where the filter is installed. Application code must still avoid passing PHI to logging calls; the filter is not a substitute for that rule.

Background workers use `safe_log_exception()` so failures record the event and exception class without exception text or traceback.

## Operational guidance

Production log destinations should use access controls, encryption in transit/at rest, retention limits approved by the data owner, and monitoring for accidental sensitive-data exposure. Do not treat application logs as an authorized clinical-data store.

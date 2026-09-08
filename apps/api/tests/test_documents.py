from app.services.documents import ALLOWED_CONTENT_TYPES, MAX_DOCUMENT_BYTES, _safe_filename


def test_safe_filename_strips_path_and_unsafe_characters() -> None:
    assert _safe_filename("../../report<>.pdf") == "report__.pdf"


def test_document_policy_allows_demo_types_and_caps_size() -> None:
    assert "application/pdf" in ALLOWED_CONTENT_TYPES
    assert "image/png" in ALLOWED_CONTENT_TYPES
    assert MAX_DOCUMENT_BYTES == 10 * 1024 * 1024

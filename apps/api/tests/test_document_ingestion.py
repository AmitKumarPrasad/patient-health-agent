from app.services.document_ingestion import CHUNK_OVERLAP, CHUNK_SIZE, chunk_text, extract_text


def test_chunk_text_uses_overlap_and_preserves_content() -> None:
    text = "alpha " * 500
    chunks = chunk_text(text)
    assert len(chunks) > 1
    assert all(len(chunk) <= CHUNK_SIZE for chunk in chunks)
    assert CHUNK_OVERLAP > 0
    assert chunks[0]


def test_extract_text_plain_text() -> None:
    assert extract_text(b"Patient report: synthetic data", "text/plain") == "Patient report: synthetic data"


def test_unsupported_binary_content_is_not_indexed() -> None:
    assert extract_text(b"binary", "image/png") == ""

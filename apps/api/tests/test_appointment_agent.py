from langchain_core.messages import ToolMessage

from app.agents.appointment_agent import _document_citations


def test_document_citations_deduplicate_same_document_chunk() -> None:
    messages = [
        ToolMessage(
            content=[
                {
                    "document_id": "doc-1",
                    "document_name": "blood-report.pdf",
                    "chunk_index": 2,
                },
                {
                    "document_id": "doc-1",
                    "document_name": "blood-report.pdf",
                    "chunk_index": 2,
                },
            ],
            tool_call_id="call-1",
            name="search_patient_documents",
        )
    ]

    assert _document_citations(messages) == ["blood-report.pdf (chunk 2)"]


def test_document_citations_keep_same_filename_for_distinct_documents() -> None:
    messages = [
        ToolMessage(
            content=[
                {
                    "document_id": "doc-1",
                    "document_name": "report.pdf",
                    "chunk_index": 0,
                },
                {
                    "document_id": "doc-2",
                    "document_name": "report.pdf",
                    "chunk_index": 0,
                },
            ],
            tool_call_id="call-1",
            name="search_patient_documents",
        )
    ]

    assert _document_citations(messages) == [
        "report.pdf (chunk 0)",
        "report.pdf (chunk 0)",
    ]


def test_document_citations_ignore_non_document_tool_messages() -> None:
    messages = [
        ToolMessage(
            content=[{"document_name": "report.pdf", "chunk_index": 0}],
            tool_call_id="call-1",
            name="search_providers",
        )
    ]

    assert _document_citations(messages) == []

from langchain_core.messages import ToolMessage

from app.agents.appointment_agent import _document_citations


def test_document_citations_include_filename_and_chunk() -> None:
    messages = [
        ToolMessage(
            name="search_patient_documents",
            tool_call_id="call-1",
            content=[
                {
                    "document_id": "doc-1",
                    "document_name": "blood-report.pdf",
                    "document_category": "lab",
                    "chunk_index": 2,
                    "content": "hemoglobin 13.2",
                    "score": 0.9,
                }
            ],
        )
    ]

    assert _document_citations(messages) == ["blood-report.pdf (chunk 2)"]


def test_document_citations_deduplicate_sources_and_ignore_other_tools() -> None:
    messages = [
        ToolMessage(
            name="search_patient_documents",
            tool_call_id="call-1",
            content=[
                {"document_name": "report.pdf", "chunk_index": 1},
                {"document_name": "report.pdf", "chunk_index": 1},
                {"document_name": "report.pdf", "chunk_index": 2},
                {"document_name": None, "chunk_index": 3},
            ],
        ),
        ToolMessage(
            name="search_providers",
            tool_call_id="call-2",
            content=[{"document_name": "not-a-source.pdf", "chunk_index": 9}],
        ),
    ]

    assert _document_citations(messages) == [
        "report.pdf (chunk 1)",
        "report.pdf (chunk 2)",
    ]

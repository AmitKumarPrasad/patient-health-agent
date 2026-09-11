from __future__ import annotations

import ast
from pathlib import Path


SERVER_PATH = Path(__file__).with_name("server.py")
EXPECTED_TOOLS = {
    "find_providers",
    "available_slots",
    "patient_records",
    "book_slot",
}


def _tool_functions() -> set[str]:
    tree = ast.parse(SERVER_PATH.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        for decorator in node.decorator_list:
            if (
                isinstance(decorator, ast.Call)
                and isinstance(decorator.func, ast.Attribute)
                and isinstance(decorator.func.value, ast.Name)
                and decorator.func.value.id == "mcp"
                and decorator.func.attr == "tool"
            ):
                names.add(node.name)
    return names


def test_mcp_exposes_expected_application_tools() -> None:
    assert _tool_functions() == EXPECTED_TOOLS


def test_mcp_server_supports_configurable_transports() -> None:
    source = SERVER_PATH.read_text(encoding="utf-8")
    assert 'os.getenv("MCP_TRANSPORT", "stdio")' in source
    assert 'mcp.run(\n            transport="streamable-http"' in source
    assert 'mcp.run(transport="stdio")' in source
    assert 'os.getenv("MCP_PORT", "8000")' in source


def test_mcp_patient_tools_require_gateway_identity() -> None:
    source = SERVER_PATH.read_text(encoding="utf-8")
    assert 'get_http_headers().get("x-patient-subject", "").strip()' in source
    assert "Authenticated patient context is required" in source
    assert "def patient_records(query: str = \"\")" in source
    assert "def book_slot(" in source
    assert "subject: str" not in source


def test_mcp_tools_delegate_to_application_services() -> None:
    tree = ast.parse(SERVER_PATH.read_text(encoding="utf-8"))
    source = ast.unparse(tree)
    assert "search_providers(db, specialty)" in source
    assert (
        "get_available_slots(db, UUID(provider_id), date.fromisoformat(requested_date))"
        in source
    )
    assert "search_patient_documents(query, subject)" in source
    assert "book_appointment(" in source
    assert 'action="record.search"' in source
    assert 'action="appointment.booked"' in source

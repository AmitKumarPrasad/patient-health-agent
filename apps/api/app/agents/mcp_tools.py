from __future__ import annotations

import os

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient


async def load_authenticated_mcp_tools(
    authenticated_subject: str, request_id: str | None = None
) -> list[BaseTool]:
    """Load MCP tools with authenticated patient and request correlation headers."""
    url = os.getenv("MCP_SERVER_URL", "http://mcp-server:8000/mcp").rstrip("/")
    headers = {"X-Patient-Subject": authenticated_subject}
    if request_id:
        headers["X-Request-ID"] = request_id
    client = MultiServerMCPClient(
        {
            "patient_health": {
                "transport": "http",
                "url": url,
                "headers": headers,
            }
        },
        handle_tool_errors=True,
    )
    return await client.get_tools()

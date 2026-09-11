from __future__ import annotations

import os

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient


async def load_authenticated_mcp_tools(authenticated_subject: str) -> list[BaseTool]:
    """Load MCP tools while binding the authenticated patient context to HTTP headers."""
    url = os.getenv("MCP_SERVER_URL", "http://mcp-server:8000/mcp").rstrip("/")
    client = MultiServerMCPClient(
        {
            "patient_health": {
                "transport": "http",
                "url": url,
                "headers": {"X-Patient-Subject": authenticated_subject},
            }
        },
        handle_tool_errors=True,
    )
    return await client.get_tools()

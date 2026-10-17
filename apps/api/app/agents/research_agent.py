from __future__ import annotations

from ipaddress import ip_address
from typing import Any
from urllib.parse import urlsplit

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.services.llm import get_llm
from app.services.web_search import get_web_search


SYSTEM_PROMPT = """You are a general healthcare-information research assistant.
Use web search for public, non-patient-specific information such as healthcare workflows,
standards, terminology, and general educational material. Do not request, infer, or process
personal health information. Do not diagnose, prescribe, or give individualized medical advice.
Clearly distinguish retrieved public information from uncertainty and encourage a qualified
clinician to address patient-specific clinical questions.
Answer only from the supplied public search context. Do not invent sources or URLs.
"""


def is_safe_source_url(url: str) -> bool:
    if not url or len(url) > 1000 or any(char.isspace() or ord(char) < 32 or char == chr(92) for char in url):
        return False
    try:
        parsed = urlsplit(url)
        hostname = (parsed.hostname or "").lower().rstrip(".")
        if not hostname or hostname == "localhost" or hostname.endswith(
            (".localhost", ".local", ".internal")
        ):
            return False
        try:
            if not ip_address(hostname).is_global:
                return False
        except ValueError:
            # Normal DNS names are allowed; do not resolve arbitrary hosts here.
            if "." not in hostname or hostname.replace(".", "").isdigit():
                return False
        return (
            parsed.scheme.lower() in {"https", "http"}
            and parsed.username is None
            and parsed.password is None
            and parsed.port != 0
        )
    except ValueError:
        return False


def _source_metadata(results: Any) -> list[dict[str, str]]:
    items = results if isinstance(results, list) else results.get("results", []) if isinstance(results, dict) else []
    sources: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url", "")).strip()
        title = str(item.get("title", "")).strip() or url
        if not is_safe_source_url(url) or url in seen:
            continue
        seen.add(url)
        sources.append({"title": title[:200], "url": url})
        if len(sources) >= 5:
            break
    return sources


def invoke_research_agent(request: str, history: list[dict[str, str]] | None = None) -> dict[str, Any]:
    search = get_web_search()
    results = search.invoke({"query": request})
    context = str(results)
    messages = [SystemMessage(content=SYSTEM_PROMPT)]
    for item in (history or [])[-10:]:
        role = item.get("role")
        content = item.get("content", "")
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))
    messages.append(
        HumanMessage(
            content=(
                f"Public research request: {request}\n\n"
                f"Search results:\n{context}"
            )
        )
    )
    result = get_llm().invoke(messages)
    return {"response": str(result.content), "sources": _source_metadata(results)}


__all__ = ["invoke_research_agent", "SYSTEM_PROMPT"]

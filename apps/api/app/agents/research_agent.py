from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

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


def _source_metadata(results: Any) -> list[dict[str, str]]:
    """Extract a small, safe provenance list from Tavily results."""
    items = results if isinstance(results, list) else results.get("results", []) if isinstance(results, dict) else []
    sources: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url", "")).strip()
        title = str(item.get("title", "")).strip() or url
        if not url or url in seen:
            continue
        seen.add(url)
        sources.append({"title": title[:200], "url": url[:1000]})
        if len(sources) >= 5:
            break
    return sources


def invoke_research_agent(request: str) -> dict[str, Any]:
    search = get_web_search()
    results = search.invoke({"query": request})
    context = str(results)
    llm = get_llm()
    result = llm.invoke(
        [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(
                content=(
                    f"Public research request: {request}\n\n"
                    f"Search results:\n{context}"
                )
            ),
        ]
    )
    return {"response": str(result.content), "sources": _source_metadata(results)}


__all__ = ["invoke_research_agent", "SYSTEM_PROMPT"]

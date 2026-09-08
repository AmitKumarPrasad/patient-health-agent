from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from app.services.llm import get_llm
from app.services.web_search import get_web_search


class ResearchState(TypedDict, total=False):
    request: str
    context: str
    response: str


SYSTEM_PROMPT = """You are a general healthcare-information research assistant.
Use web search for public, non-patient-specific information such as healthcare workflows,
standards, terminology, and general educational material. Do not request, infer, or process
personal health information. Do not diagnose, prescribe, or give individualized medical advice.
Clearly distinguish retrieved public information from uncertainty and encourage a qualified
clinician to address patient-specific clinical questions.
"""


def invoke_research_agent(request: str) -> str:
    search = get_web_search()
    results = search.invoke({"query": request})
    context = str(results)
    llm = get_llm()
    result = llm.invoke(
        [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=f"Public research request: {request}\n\nSearch results:\n{context}"),
        ]
    )
    return str(result.content)


__all__ = ["invoke_research_agent", "SYSTEM_PROMPT"]

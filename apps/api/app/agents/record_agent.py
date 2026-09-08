from __future__ import annotations

from typing import TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from app.services.llm import get_llm
from app.services.record_tools import search_patient_documents, search_patient_record_content


class RecordAgentState(TypedDict):
    subject: str
    request: str
    context: str
    response: str


SYSTEM_PROMPT = """You are a patient-record navigation assistant.
Your job is to help the authenticated patient find and organize their own health-record documents.
Use only content returned by authorized patient-scoped retrieval tools.
Do not diagnose conditions, recommend treatment, interpret test results as medical advice, or invent facts.
When records are unavailable, say so clearly. Encourage the patient to discuss clinical questions with a qualified clinician.
"""


def _retrieve(state: RecordAgentState) -> RecordAgentState:
    metadata = search_patient_documents(state["request"], state["subject"])
    chunks = search_patient_record_content(state["request"], state["subject"])
    lines = ["Document metadata:"]
    lines.extend(
        f"- {item['filename']} | category={item.get('category') or 'uncategorized'} | "
        f"content_type={item['content_type']} | uploaded={item['created_at']}"
        for item in metadata
    )
    lines.append("\nRelevant extracted record content:")
    lines.extend(
        f"- document_id={item['document_id']} | relevance={item['score']:.3f}\n  {item['content']}"
        for item in chunks
    )
    if not metadata and not chunks:
        lines.append("No matching records were found.")
    return {**state, "context": "\n".join(lines)}


def _respond(state: RecordAgentState) -> RecordAgentState:
    llm = get_llm()
    result = llm.invoke(
        [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(
                content=(
                    f"Patient request: {state['request']}\n\n"
                    f"Authorized record context:\n{state['context']}\n\n"
                    "Answer using only this context. Mention the source filename when useful."
                )
            ),
        ]
    )
    return {**state, "response": str(result.content)}


def _build_graph():
    graph = StateGraph(RecordAgentState)
    graph.add_node("retrieve", _retrieve)
    graph.add_node("respond", _respond)
    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", "respond")
    graph.add_edge("respond", END)
    return graph.compile()


def invoke_record_agent(request: str, subject: str) -> str:
    request = request.strip()
    if not request:
        raise ValueError("Record assistant request cannot be empty")
    result = _build_graph().invoke(
        {
            "subject": subject,
            "request": request,
            "context": "",
            "response": "",
        }
    )
    return result["response"]

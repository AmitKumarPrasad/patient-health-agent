from __future__ import annotations

from typing import TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from app.services.record_tools import search_patient_documents
from app.services.llm import get_llm


class RecordAgentState(TypedDict):
    subject: str
    request: str
    context: str
    response: str


SYSTEM_PROMPT = """You are a patient-record navigation assistant.
Your job is to help the authenticated patient find and organize their own health-record documents.
You may summarize document metadata or text explicitly provided by an authorized retrieval tool.
Do not diagnose conditions, recommend treatment, interpret test results as medical advice, or invent facts.
When records are unavailable, say so clearly. Encourage the patient to discuss clinical questions with a qualified clinician.
"""


def _retrieve(state: RecordAgentState) -> RecordAgentState:
    documents = search_patient_documents(state["request"], state["subject"])
    lines = []
    for item in documents:
        lines.append(
            f"- {item['filename']} | category={item.get('category') or 'uncategorized'} | "
            f"content_type={item['content_type']} | uploaded={item['created_at']}"
        )
    return {**state, "context": "\n".join(lines) if lines else "No matching documents were found."}


def _respond(state: RecordAgentState) -> RecordAgentState:
    llm = get_llm()
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(
            content=(
                f"Patient request: {state['request']}\n\n"
                f"Authorized record search results:\n{state['context']}\n\n"
                "Answer using only these results."
            )
        ),
    ]
    result = llm.invoke(messages)
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
    graph = _build_graph()
    state: RecordAgentState = {
        "subject": subject,
        "request": request.strip(),
        "context": "",
        "response": "",
    }
    result = graph.invoke(state)
    return result["response"]

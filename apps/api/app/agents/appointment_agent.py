from __future__ import annotations

from typing import TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from app.services.llm import get_llm


class AppointmentAgentState(TypedDict, total=False):
    user_request: str
    response: str


SYSTEM_PROMPT = """You are the appointment assistant for a healthcare scheduling platform.
Help users find and schedule appointments, but do not diagnose, prescribe, or make clinical decisions.
Never claim an appointment is booked unless a booking tool has actually succeeded.
If required scheduling details are missing, ask a concise clarification question.
"""


def respond(state: AppointmentAgentState) -> AppointmentAgentState:
    llm = get_llm()
    result = llm.invoke(
        [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=state["user_request"]),
        ]
    )
    return {**state, "response": str(result.content)}


def build_appointment_graph():
    graph = StateGraph(AppointmentAgentState)
    graph.add_node("respond", respond)
    graph.add_edge(START, "respond")
    graph.add_edge("respond", END)
    return graph.compile()

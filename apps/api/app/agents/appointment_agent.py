from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class AppointmentAgentState(TypedDict, total=False):
    user_request: str
    response: str


def respond(state: AppointmentAgentState) -> AppointmentAgentState:
    return {
        **state,
        "response": (
            "Appointment requests are routed through controlled provider, availability, "
            "and booking tools. No database mutation is performed directly by the model."
        ),
    }


def build_appointment_graph() -> StateGraph:
    graph = StateGraph(AppointmentAgentState)
    graph.add_node("respond", respond)
    graph.add_edge(START, "respond")
    graph.add_edge("respond", END)
    return graph

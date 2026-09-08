from __future__ import annotations

from datetime import date, datetime
from typing import TypedDict
from uuid import UUID

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import StructuredTool
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing_extensions import Annotated

from app.db.session import SessionLocal
from app.services.appointment_tools import book_appointment, get_available_slots, search_providers
from app.services.llm import get_llm
from app.services.patient_identity import require_patient_by_external_id


class AppointmentAgentState(TypedDict, total=False):
    user_request: str
    patient_subject: str
    response: str
    messages: Annotated[list, add_messages]


SYSTEM_PROMPT = """You are the appointment assistant for a healthcare scheduling platform.
Help users find and schedule appointments, but do not diagnose, prescribe, or make clinical decisions.
Never claim an appointment is booked unless the booking tool has actually succeeded.
Use the provider and availability tools for scheduling facts. Ask concise clarification questions when
required information is missing. Appointment times must include an explicit timezone.
The authenticated patient identity is supplied by the application and must never be requested from or
inferred from the user. The booking tool does not accept a patient ID.
"""


def build_tools(authenticated_subject: str) -> list[StructuredTool]:
    def _search_providers(specialty: str) -> list[dict[str, str]]:
        with SessionLocal() as db:
            return search_providers(db, specialty)

    def _get_available_slots(provider_id: str, requested_date: date) -> list[dict[str, str]]:
        with SessionLocal() as db:
            return get_available_slots(db, UUID(provider_id), requested_date)

    def _book_authenticated_patient(
        provider_id: str,
        starts_at: datetime,
        ends_at: datetime,
        reason: str | None = None,
    ) -> dict[str, str]:
        with SessionLocal() as db:
            patient = require_patient_by_external_id(db, authenticated_subject)
            return book_appointment(
                db,
                patient.id,
                UUID(provider_id),
                starts_at,
                ends_at,
                reason,
            )

    return [
        StructuredTool.from_function(
            _search_providers,
            name="search_providers",
            description="Find healthcare providers by specialty. Use this before selecting a provider.",
        ),
        StructuredTool.from_function(
            _get_available_slots,
            name="get_available_slots",
            description="Return currently available appointment slots for a provider on a date.",
        ),
        StructuredTool.from_function(
            _book_authenticated_patient,
            name="book_appointment",
            description="Book an appointment for the authenticated patient after a valid provider and available slot are known. Never supply or request a patient ID.",
        ),
    ]


def build_appointment_graph(authenticated_subject: str):
    tools = build_tools(authenticated_subject)
    llm = get_llm().bind_tools(tools)
    tool_node = ToolNode(tools)

    def call_model(state: AppointmentAgentState) -> AppointmentAgentState:
        messages = state.get("messages", [])
        result = llm.invoke([SystemMessage(content=SYSTEM_PROMPT), *messages])
        return {"messages": [result]}

    def route_after_model(state: AppointmentAgentState) -> str:
        last = state["messages"][-1]
        if isinstance(last, AIMessage) and last.tool_calls:
            return "tools"
        return "done"

    def call_tools(state: AppointmentAgentState) -> AppointmentAgentState:
        result = tool_node.invoke(state)
        return {"messages": result["messages"]}

    def finalize(state: AppointmentAgentState) -> AppointmentAgentState:
        last = state["messages"][-1]
        response = last.content if isinstance(last, AIMessage) else str(last.content)
        return {"response": str(response)}

    graph = StateGraph(AppointmentAgentState)
    graph.add_node("model", call_model)
    graph.add_node("tools", call_tools)
    graph.add_node("finalize", finalize)
    graph.add_edge(START, "model")
    graph.add_conditional_edges("model", route_after_model, {"tools": "tools", "done": "finalize"})
    graph.add_edge("tools", "model")
    graph.add_edge("finalize", END)
    return graph.compile()


def invoke_appointment_agent(user_request: str, authenticated_subject: str) -> str:
    graph = build_appointment_graph(authenticated_subject)
    result = graph.invoke(
        {
            "user_request": user_request,
            "patient_subject": authenticated_subject,
            "messages": [HumanMessage(content=user_request)],
        }
    )
    return result["response"]

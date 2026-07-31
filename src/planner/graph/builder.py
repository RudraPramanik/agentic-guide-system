"""Compile the planner LangGraph once and cache the singleton (P5.11)."""

from __future__ import annotations

from typing import Any, Literal

from langgraph.graph import END, START, StateGraph

from src.planner.graph.nodes.agent import agent_node
from src.planner.graph.nodes.parse_preferences import parse_preferences
from src.planner.graph.nodes.record_evaluation import record_evaluation
from src.planner.graph.nodes.tool_executor import tool_executor_node
from src.planner.graph.nodes.write_narrative import write_narrative
from src.planner.graph.state import TravelState

_compiled: Any | None = None


def _route_after_tools(
    state: dict[str, Any],
) -> Literal["write_narrative", "agent", "__end__"]:
    if state.get("needs_clarification"):
        return "__end__"
    if state.get("plan_complete"):
        return "write_narrative"
    return "agent"


def build_planner_graph() -> Any:
    """Build and compile the planner graph. Raises loudly on wiring errors."""
    graph = StateGraph(TravelState)
    graph.add_node("parse_preferences", parse_preferences)
    graph.add_node("agent", agent_node)
    graph.add_node("tool_executor", tool_executor_node)
    graph.add_node("write_narrative", write_narrative)
    graph.add_node("record_evaluation", record_evaluation)

    graph.add_edge(START, "parse_preferences")
    graph.add_edge("parse_preferences", "agent")
    graph.add_edge("agent", "tool_executor")  # unconditional every cycle
    graph.add_conditional_edges(
        "tool_executor",
        _route_after_tools,
        {
            "write_narrative": "write_narrative",
            "agent": "agent",
            "__end__": END,
        },
    )
    graph.add_edge("write_narrative", "record_evaluation")
    graph.add_edge("record_evaluation", END)
    return graph.compile()


def get_compiled_graph() -> Any:
    """Return process-wide compiled graph singleton (no ToolContext closure)."""
    global _compiled
    if _compiled is None:
        _compiled = build_planner_graph()
    return _compiled

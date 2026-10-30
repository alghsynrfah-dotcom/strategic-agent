
import sqlite3
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from backend.graph.state import AgentState
from backend.nodes.agent import TOOLS, agent
from backend.nodes.analyze_risks import analyze_risks
from backend.nodes.ask_clarification import ask_clarification
from backend.nodes.assess_problem import assess_problem
from backend.nodes.compare_solutions import compare_solutions
from backend.nodes.draft_statement import draft_statement
from backend.nodes.finalize_statement import finalize_statement
from backend.nodes.load_context import load_context
from backend.nodes.plan_solution import plan_solution


def route_entry(state):
    """Edits restart problem assessment; normal requests load context."""
    if state.get("user_action") == "edit":
        return "assess_problem"
    return "load_context"


def route_from_agent(state):
    """Route to the tool selected by the agent."""
    return state["next_tool"]


builder = StateGraph(AgentState)

builder.add_node("load_context", load_context)
builder.add_node("assess_problem", assess_problem)
builder.add_node("agent", agent)
builder.add_node("ask_clarification", ask_clarification)
builder.add_node("draft_statement", draft_statement)
builder.add_node("finalize_statement", finalize_statement)
builder.add_node("plan_solution", plan_solution)
builder.add_node("analyze_risks", analyze_risks)
builder.add_node("compare_solutions", compare_solutions)

builder.add_conditional_edges(
    START,
    route_entry,
    {
        "load_context": "load_context",
        "assess_problem": "assess_problem",
    },
)

builder.add_edge("load_context", "assess_problem")
builder.add_edge("assess_problem", "agent")

builder.add_conditional_edges(
    "agent",
    route_from_agent,
    {name: name for name in TOOLS},
)

builder.add_edge("ask_clarification", END)
builder.add_edge("draft_statement", END)

# Finalize -> Plan -> Risks -> Solution comparison
builder.add_edge("finalize_statement", "plan_solution")
builder.add_edge("plan_solution", "analyze_risks")
builder.add_edge("analyze_risks", "compare_solutions")
builder.add_edge("compare_solutions", END)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

checkpoint_conn = sqlite3.connect(
    DATA_DIR / "checkpoints.db",
    check_same_thread=False,
)

graph = builder.compile(checkpointer=SqliteSaver(checkpoint_conn))

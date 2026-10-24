import sqlite3
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from backend.graph.router import route_entry, route_from_agent
from backend.graph.state import AgentState
from backend.nodes.agent import TOOLS, agent
from backend.nodes.ask_clarification import ask_clarification
from backend.nodes.assess_problem import assess_problem
from backend.nodes.draft_statement import draft_statement
from backend.nodes.finalize_statement import finalize_statement
from backend.nodes.load_context import load_context
from backend.nodes.revise_statement import revise_statement

builder = StateGraph(AgentState)

builder.add_node("load_context", load_context)
builder.add_node("assess_problem", assess_problem)
builder.add_node("agent", agent)
builder.add_node("ask_clarification", ask_clarification)
builder.add_node("draft_statement", draft_statement)
builder.add_node("revise_statement", revise_statement)
builder.add_node("finalize_statement", finalize_statement)

builder.add_edge(START, "load_context")

builder.add_conditional_edges(
    "load_context",
    route_entry,
    {"assess_problem": "assess_problem", "agent": "agent"},
)

builder.add_edge("assess_problem", "agent")

# الـ agent بيختار وحدة من الأدوات
builder.add_conditional_edges("agent", route_from_agent, {name: name for name in TOOLS})

for tool in TOOLS:
    builder.add_edge(tool, END)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

checkpoint_conn = sqlite3.connect(DATA_DIR / "checkpoints.db", check_same_thread=False)
graph = builder.compile(checkpointer=SqliteSaver(checkpoint_conn))


import operator
from typing import Annotated, List, Literal, TypedDict


class AgentState(TypedDict, total=False):
    # Project context
    project_id: str
    domain: Literal["financial", "economic"]
    messages: Annotated[List[dict], operator.add]
    memory: str
    knowledge: str
    user_action: Literal["message", "edit", "confirm", "proceed"]

    # Agent decisions
    initial_problem: str
    assessment: dict
    questions_asked: int
    next_tool: str
    decision: Literal[
        "ask",
        "draft",
        "finalize",
        "plan",
        "risks",
        "compare",
    ]

    # Problem statement
    statement: str
    previous_statement: str
    edit_feedback: str
    statement_status: Literal[
        "none",
        "draft",
        "confirmed",
        "unconfirmed",
    ]
    assumptions: List[str]

    # Analysis outputs
    plan: str
    risks: str
    solution_comparison: str
    response: str

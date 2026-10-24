import operator
from typing import Annotated, List, Literal, TypedDict


class AgentState(TypedDict, total=False):
    # من الباك
    project_id: str
    domain: Literal["financial", "economic"]
    messages: Annotated[List[dict], operator.add]   # المحادثة بتتراكم
    memory: str
    knowledge: str
    user_action: Literal["message", "edit", "confirm", "proceed"]

    # عقل الوكيل
    initial_problem: str
    assessment: dict
    questions_asked: int
    next_tool: str                # الأداة اللي اختارها الـ agent
    decision: Literal["ask", "draft", "revise", "finalize"]

    # المخرجات
    statement: str
    statement_status: Literal["none", "draft", "confirmed", "unconfirmed"]
    assumptions: List[str]
    response: str

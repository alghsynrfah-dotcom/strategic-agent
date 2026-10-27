from backend import events
from backend.agent.llm import stream_text
from backend.events import Kind
from backend.nodes.helpers import detect_language, format_conversation
from backend.prompts.prompts import PLAN_PROMPT

UNCONFIRMED_NOTE = (
    "The statement was NOT confirmed by the user, so the plan must say it is based on an unconfirmed statement."
)


def plan_solution(state):
    """أداة: بتخطط حل للمشكلة بناءً على البيان (المعتمد أو غير المعتمد)."""
    events.progress(Kind.PLAN, "Planning the solution")

    messages = state.get("messages", [])
    caveat = "none" if state.get("statement_status") == "confirmed" else UNCONFIRMED_NOTE

    prompt = PLAN_PROMPT.format(
        language=detect_language(messages),
        statement=state.get("statement", ""),
        conversation=format_conversation(messages, max_chars=1200),
        caveat=caveat,
    )
    text = stream_text(prompt, section="plan")

    return {"plan": text, "decision": "plan"}

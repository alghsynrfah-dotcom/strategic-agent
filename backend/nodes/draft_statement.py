from backend import events
from backend.agent.llm import stream_text
from backend.events import Kind
from backend.nodes.helpers import (
    detect_language,
    format_conversation,
    join_list,
    last_user_message,
)
from backend.nodes.statement_guard import ensure_valid
from backend.prompts.prompts import DRAFT_PROMPT


def draft_statement(state):
    """أداة: بتصيغ بيان المشكلة من كل المعلومات، وبتعيد الصياغة من الصفر بعد التعديل."""
    events.progress(Kind.DRAFT, "Writing the problem statement")

    a = state["assessment"]
    messages = state.get("messages", [])

    previous = state.get("statement", "")
    action = state.get("user_action", "message")
    feedback = last_user_message(messages) if previous and action in ("edit", "message") else ""

    prompt = DRAFT_PROMPT.format(
        language=detect_language(messages),
        conversation=format_conversation(messages),
        known_facts=join_list(a.get("known_facts")),
        missing_info=join_list(a.get("missing_info")),
        previous_statement=previous or "none",
        feedback=feedback or "none",
    )
    text = ensure_valid(stream_text(prompt), state)

    events.progress(Kind.AWAITING, "Please confirm or edit the problem statement")

    return {
        "statement": text,
        "statement_status": "draft",
        "assumptions": a.get("missing_info", []),
        "plan": "",       # البيان تغيّر: الخطة والمخاطر القديمة ما عادت صالحة
        "risks": "",
        "response": text,
        "decision": "draft",
        "messages": [{"role": "assistant", "content": text}],
    }

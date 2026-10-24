from backend import events
from backend.agent.llm import stream_text
from backend.events import Kind
from backend.nodes.helpers import detect_language, last_user_message
from backend.nodes.statement_guard import ensure_valid
from backend.prompts.prompts import REVISE_PROMPT


def revise_statement(state):
    """أداة: بتعدّل البيان حسب ملاحظات المستخدم فقط."""
    events.progress(Kind.REVISE, "Revising the problem statement")

    messages = state.get("messages", [])

    prompt = REVISE_PROMPT.format(
        language=detect_language(messages),
        statement=state.get("statement", ""),
        feedback=last_user_message(messages),
    )
    text = ensure_valid(stream_text(prompt), state)

    events.progress(Kind.AWAITING, "Please confirm or edit the problem statement")

    return {
        "statement": text,
        "statement_status": "draft",
        "response": text,
        "decision": "revise",
        "messages": [{"role": "assistant", "content": text}],
    }

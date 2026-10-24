from langchain_core.messages import HumanMessage

from backend import events
from backend.agent.llm import get_model
from backend.events import Kind
from backend.nodes.helpers import detect_language, format_conversation, is_valid_statement
from backend.prompts.prompts import FIX_PROMPT


def ensure_valid(text: str, state: dict) -> str:
    """الحارس: إذا البيان مكسور بنصلحو مرة وحدة، وإذا فشل بنرجع للسابق."""
    if is_valid_statement(text):
        return text

    events.progress(Kind.GUARD, "Statement structure broken, repairing")

    messages = state.get("messages", [])
    prompt = FIX_PROMPT.format(
        language=detect_language(messages),
        statement=text,
        conversation=format_conversation(messages),
    )
    fixed = str(get_model().invoke([HumanMessage(content=prompt)]).content).strip()

    if not is_valid_statement(fixed):
        fixed = state.get("statement") or text
        events.progress(Kind.GUARD, "Repair failed, keeping the previous statement")

    events.replace_statement(fixed)
    return fixed

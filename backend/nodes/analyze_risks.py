from backend import events
from backend.agent.llm import stream_text
from backend.events import Kind
from backend.nodes.helpers import detect_language
from backend.prompts.prompts import RISKS_PROMPT


def analyze_risks(state):
    """أداة: بتحلل مخاطر تنفيذ الخطة بالنسبة للمشكلة."""
    events.progress(Kind.RISKS, "Analyzing the risks")

    prompt = RISKS_PROMPT.format(
        language=detect_language(state.get("messages", [])),
        statement=state.get("statement", ""),
        plan=state.get("plan", ""),
    )
    text = stream_text(prompt, section="risks")

    return {"risks": text, "decision": "risks"}

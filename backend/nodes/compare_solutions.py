
from backend import events
from backend.agent.llm import stream_text
from backend.events import Kind
from backend.nodes.helpers import detect_language, format_conversation
from backend.prompts.prompts import COMPARE_SOLUTIONS_PROMPT


def compare_solutions(state):
    """Compare three alternative solutions and recommend the best fit."""

    events.progress(
        Kind.COMPARISON,
        "Comparing alternative solutions and selecting a recommendation",
    )

    prompt = COMPARE_SOLUTIONS_PROMPT.format(
        language=detect_language(state.get("messages", [])),
        statement=state.get("statement", ""),
        plan=state.get("plan", ""),
        risks=state.get("risks", ""),
        conversation=format_conversation(
            state.get("messages", []),
            max_chars=1200,
        ),
    )

    comparison = stream_text(prompt, section="comparison")

    return {
        "solution_comparison": comparison,
        "decision": "compare",
    }

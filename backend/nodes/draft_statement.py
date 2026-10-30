
from backend import events
from backend.agent.llm import stream_text
from backend.events import Kind
from backend.nodes.helpers import (
    detect_language,
    format_conversation,
    join_list,
)
from backend.nodes.statement_guard import ensure_valid
from backend.prompts.prompts import DRAFT_PROMPT


def draft_statement(state):
    """Write a new problem statement using the conversation and edit feedback."""
    events.progress(Kind.DRAFT, "Writing the problem statement")

    assessment = state.get("assessment") or {}
    messages = state.get("messages", [])

    previous = (
        state.get("previous_statement")
        or state.get("statement")
        or ""
    )

    feedback = state.get("edit_feedback", "")

    # Preserve compatibility with normal follow-up messages that
    # request a change to an existing statement.
    if (
        not feedback
        and previous
        and state.get("user_action") == "message"
    ):
        for message in reversed(messages):
            if message.get("role") == "user":
                feedback = message.get("content", "")
                break

    prompt = DRAFT_PROMPT.format(
        language=detect_language(messages),
        conversation=format_conversation(messages),
        known_facts=join_list(assessment.get("known_facts")),
        missing_info=join_list(assessment.get("missing_info")),
        previous_statement=previous or "none",
        feedback=feedback or "none",
    )

    text = ensure_valid(stream_text(prompt), state)

    events.progress(
        Kind.AWAITING,
        "Please confirm or edit the problem statement",
    )

    return {
        "statement": text,
        "statement_status": "draft",
        "assumptions": assessment.get("missing_info", []),
        "plan": "",
        "risks": "",
        "solution_comparison": "",
        "response": text,
        "decision": "draft",
        "messages": [{"role": "assistant", "content": text}],
        # Clear temporary edit data after the new statement is generated.
        "previous_statement": "",
        "edit_feedback": "",
    }

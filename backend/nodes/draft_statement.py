from backend import events
from backend.agent.llm import ask_json, stream_text
from backend.events import Kind
from backend.nodes.helpers import (
    detect_language,
    format_conversation,
    join_list,
)
from backend.nodes.statement_guard import ensure_valid
from backend.prompts.prompts import (
    ASSUMPTIONS_PROMPT,
    DRAFT_PROMPT,
)


def draft_statement(state):
    """Write a problem statement and generate structured assumptions."""

    events.progress(Kind.DRAFT, "Writing the problem statement")

    assessment = state.get("assessment") or {}
    messages = state.get("messages", [])

    previous = (
        state.get("previous_statement")
        or state.get("statement")
        or ""
    )

    feedback = state.get("edit_feedback", "")

    # Preserve compatibility with normal follow-up messages
    # that request a change to an existing statement.
    if (
        not feedback
        and previous
        and state.get("user_action") == "message"
    ):
        for message in reversed(messages):
            if message.get("role") == "user":
                feedback = message.get("content", "")
                break

    language = detect_language(messages)
    conversation = format_conversation(messages)
    known_facts = join_list(assessment.get("known_facts"))
    missing_info = assessment.get("missing_info") or []

    # Keep the original statement generation and streaming unchanged.
    prompt = DRAFT_PROMPT.format(
        language=language,
        conversation=conversation,
        known_facts=known_facts,
        missing_info=join_list(missing_info),
        previous_statement=previous or "none",
        feedback=feedback or "none",
    )

    text = ensure_valid(stream_text(prompt), state)

    # New feature: generate structured assumptions after the statement.
    assumptions = []

    if missing_info:
        assumptions_prompt = ASSUMPTIONS_PROMPT.format(
            language=language,
            statement=text,
            conversation=conversation,
            known_facts=known_facts,
            missing_info=join_list(missing_info),
        )

        try:
            raw = ask_json(assumptions_prompt)
            generated = raw.get("assumptions", [])

            if isinstance(generated, list):
                for item in generated:
                    if not isinstance(item, dict):
                        continue

                    assumption = str(
                        item.get("assumption", "")
                    ).strip()

                    reason = str(
                        item.get("reason", "")
                    ).strip()

                    confidence = str(
                        item.get("confidence", "Low")
                    ).strip().capitalize()

                    if not assumption:
                        continue

                    if confidence not in ("High", "Medium", "Low"):
                        confidence = "Low"

                    assumptions.append({
                        "assumption": assumption,
                        "reason": reason,
                        "confidence": confidence,
                    })

        except Exception as exc:
            # Assumption generation must never break statement drafting.
            print(
                f"[ASSUMPTIONS FALLBACK] "
                f"{type(exc).__name__}: {exc}",
                flush=True,
            )
            assumptions = []

    events.progress(
        Kind.AWAITING,
        "Please confirm or edit the problem statement",
    )

    return {
        "statement": text,
        "statement_status": "draft",
        "assumptions": assumptions,
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

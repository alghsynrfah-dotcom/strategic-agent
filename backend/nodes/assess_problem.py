from backend import events
from backend.agent.llm import ask_json
from backend.events import Kind
from backend.graph.schemas import Assessment
from backend.nodes.helpers import format_conversation
from backend.prompts.prompts import ASSESS_PROMPT


DEFAULT_QUESTIONS = {
    "problem": "What problem or goal would you like to solve?",
    "context": "What does your company do?",
    "impact": "What is being affected by this problem?",
}


def _has(raw: dict, name: str) -> bool:
    evidence = str(raw.get(f"{name}_evidence", "")).strip()
    return bool(raw.get(f"has_{name}")) and bool(evidence)


def assess_problem(state):
    if (
        state.get("user_action") in ("confirm", "proceed")
        and state.get("statement")
    ):
        events.progress(
            Kind.ASSESSMENT,
            "Nothing new to assess, keeping the previous assessment",
        )
        return {"assessment": state.get("assessment") or {}}

    events.progress(Kind.THINKING, "Analyzing the problem")

    prompt = ASSESS_PROMPT.format(
        domain=state.get("domain", ""),
        conversation=format_conversation(state.get("messages", [])),
        memory=state.get("memory") or "none",
        knowledge=state.get("knowledge") or "none",
    )

    try:
        raw = ask_json(prompt)

        elements = {
            name: _has(raw, name)
            for name in ("problem", "context", "impact")
        }

        missing = [
            name for name, found in elements.items()
            if not found
        ]

        question = str(raw.get("question", "")).strip()

        if missing and not question:
            question = DEFAULT_QUESTIONS[missing[0]]

        assessment = Assessment(
            clarity=(
                "clear"
                if not missing
                else ("partial" if len(missing) == 1 else "vague")
            ),
            known_facts=[
                str(item) for item in raw.get("known_facts", [])
            ],
            missing_info=missing,
            critical_missing=bool(missing),
            most_important_question=question if missing else "",
            ready_to_draft=not missing,
            reason=f"elements found: {elements}",
        )

    except Exception as exc:
        print(
            f"[ASSESS FALLBACK] {type(exc).__name__}: {exc}",
            flush=True,
        )

        assessment = Assessment(
            clarity="vague",
            missing_info=["problem details"],
            critical_missing=True,
            most_important_question=(
                "Can you describe the problem in more detail?"
            ),
            ready_to_draft=False,
            reason="Assessment fallback",
        )

    events.progress(
        Kind.ASSESSMENT,
        f"{assessment.reason} -> "
        f"ready_to_draft={assessment.ready_to_draft}",
    )

    result = {
        "assessment": assessment.model_dump(),
    }

    # When the user edits the problem, clear the old results
    # after reassessing the problem from the beginning.
    if state.get("user_action") == "edit":
        result.update({
            "statement": "",
            "statement_status": "none",
            "assumptions": [],
            "plan": "",
            "risks": "",
            "response": "",
            "decision": "",
            "next_tool": "",
            "questions_asked": 0,
        })

    return result

from backend import events
from backend.events import Kind


def load_context(state):
    """بيجهز السياق: المشكلة الأولية + الذاكرة والمعرفة اللي جمعها الباك."""
    events.progress(Kind.START, "Request received")

    first_problem = ""
    for m in state.get("messages", []):
        if m["role"] == "user":
            first_problem = m["content"]
            break

    memory = state.get("memory", "")
    knowledge = state.get("knowledge", "")
    asked = state.get("questions_asked", 0)

    events.progress(
        Kind.CONTEXT,
        f"Context loaded: knowledge={len(knowledge)} chars, memory={'yes' if memory else 'no'}",
    )

    return {
        "initial_problem": state.get("initial_problem") or first_problem,
        "questions_asked": asked,
        "memory": memory,
        "knowledge": knowledge,
        "statement_status": state.get("statement_status", "none"),
    }

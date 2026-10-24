from backend import events
from backend.nodes.helpers import detect_language

TEXTS = {
    "English": {
        "confirmed": "The problem statement was confirmed.",
        "unconfirmed": "Continuing without confirmation. The statement stays unconfirmed.",
    },
    "Arabic": {
        "confirmed": "تم اعتماد بيان المشكلة.",
        "unconfirmed": "تابعنا بدون تأكيد. بيان المشكلة بقي غير معتمد.",
    },
}


def finalize_statement(state):
    """أداة: تأكيد البيان، أو المتابعة بدون تأكيد (بيضل غير معتمد)."""
    language = detect_language(state.get("messages", []))

    status = "confirmed" if state.get("user_action") == "confirm" else "unconfirmed"
    text = TEXTS[language][status]

    events.token(text)

    return {
        "statement_status": status,
        "response": text,
        "decision": "finalize",
        "messages": [{"role": "assistant", "content": text}],
    }

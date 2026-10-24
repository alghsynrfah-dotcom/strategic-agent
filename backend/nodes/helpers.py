import re


def format_conversation(messages, max_chars=2500):
    """بنحصر المحادثة بآخر max_chars حرف لأن سياق الموديل صغير."""
    lines = [f"{m['role']}: {m['content']}" for m in messages]
    return "\n".join(lines)[-max_chars:]


def join_list(items):
    return "; ".join(items) if items else "none"


def last_user_message(messages):
    for m in reversed(messages):
        if m["role"] == "user":
            return m["content"]
    return ""


def is_valid_statement(text: str) -> bool:
    """بيتأكد إنه البيان فيه 3 أجزاء مرقمة وكل جزء فيه نص حقيقي."""
    parts = re.split(r"(?:^|\s)[123]\.\s", " " + text)
    pieces = [x.strip() for x in parts[1:]]
    if len(pieces) < 3:
        return False
    return all(len(x.split()) >= 3 for x in pieces[:3])


def detect_language(messages) -> str:
    """بيكشف لغة المستخدم من نسبة الأحرف العربية بكلامو."""
    text = " ".join(m["content"] for m in messages if m["role"] == "user")
    letters = sum(1 for c in text if c.isalpha())
    arabic = sum(1 for c in text if "\u0600" <= c <= "\u06FF")
    return "Arabic" if letters and arabic / letters > 0.3 else "English"


def previous_questions(messages) -> str:
    """الأسئلة اللي الوكيل سألها قبل (ليتجنب تكرارها)."""
    asked = [
        m["content"].strip()
        for m in messages
        if m["role"] == "assistant" and m["content"].strip().endswith(("?", "؟"))
    ]
    return " | ".join(asked) if asked else "none"

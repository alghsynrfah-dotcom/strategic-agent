"""المكان الوحيد اللي بيرسل أحداث الـ Streaming للواجهة."""
from langgraph.config import get_stream_writer


class Kind:
    """أنواع الأحداث، بدل ما نكتب النصوص بكل مكان."""
    START = "start"
    CONTEXT = "context"
    THINKING = "thinking"
    ASSESSMENT = "assessment"
    AGENT = "agent"
    TOOL = "tool"
    ASK = "ask"
    DRAFT = "draft"
    PLAN = "plan"
    RISKS = "risks"
    GUARD = "guard"
    AWAITING = "awaiting_confirmation"
    TOKEN = "token"
    STATEMENT_REPLACE = "statement_replace"


def _send(event: dict) -> None:
    try:
        writer = get_stream_writer()
    except Exception:
        return  # برا الـ graph (مثلاً بالاختبار) ما في قناة، فنتجاهل
    writer(event)


def progress(kind: str, message: str) -> None:
    """حدث تقدم (بيظهر بالشريط الرمادي)."""
    _send({"kind": kind, "message": message})


def token(text: str, section: str = "") -> None:
    """كلمة من الرد. section فاضي = المحادثة، plan أو risks = صندوقها بالواجهة."""
    _send({"kind": Kind.TOKEN, "text": text, "section": section})


def replace_statement(text: str) -> None:
    """استبدال البيان المعروض بنسخة مصلّحة."""
    _send({"kind": Kind.STATEMENT_REPLACE, "text": text})

from pathlib import Path

KNOWLEDGE_DIR = Path(__file__).resolve().parent / "knowledge"
MAX_KNOWLEDGE_CHARS = 1500   # سياق الموديل صغير


def load_knowledge(domain: str) -> str:
    """المعرفة المصرح بها: ملف ملاحظات لكل مجال."""
    path = KNOWLEDGE_DIR / f"{domain}.md"
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")[:MAX_KNOWLEDGE_CHARS]


def load_memory(project: dict) -> str:
    """الذاكرة: البيان المؤكد السابق للمشروع من القاعدة، إن وجد."""
    confirmed = (project.get("confirmed_statement") or "").strip()
    return f"Previously confirmed problem statement: {confirmed}" if confirmed else ""


def build_context(project: dict) -> dict:
    """الباك بيجمع الذاكرة والمعرفة قبل ما يمررهم للوكيل."""
    return {
        "memory": load_memory(project),
        "knowledge": load_knowledge(project["domain"]),
    }

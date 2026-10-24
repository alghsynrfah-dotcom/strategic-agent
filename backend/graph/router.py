MAX_QUESTIONS = 3


def route_entry(state):
    """أول قرار: كل شي بيبدأ بالتقييم، إلا التأكيد والمتابعة على بيان موجود."""
    action = state.get("user_action", "message")
    has_statement = bool(state.get("statement"))

    if has_statement and action in ("confirm", "proceed"):
        return "agent"
    return "assess_problem"      # رسالة أو تعديل: نرجع لبداية التقييم


def route_from_agent(state):
    """الأداة اللي اختارها الـ agent هي الـ node الجاي."""
    return state["next_tool"]

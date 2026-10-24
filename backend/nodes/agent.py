from backend import events
from backend.agent.llm import ask_json
from backend.events import Kind
from backend.graph.router import MAX_QUESTIONS
from backend.nodes.helpers import join_list, last_user_message
from backend.prompts.prompts import AGENT_PROMPT

# الأدوات اللي الـ agent بيختار منها (كل أداة = node)
TOOLS = {
    "ask_clarification": "Ask the user ONE clarifying question about the first missing element.",
    "draft_statement": "Write the 3-part problem statement now; missing items become assumptions.",
    "revise_statement": "Revise the existing problem statement according to the user's feedback.",
    "finalize_statement": "Confirm the statement, or continue without confirmation.",
}


def allowed_tools(state) -> list:
    """السياسة (بالكود): أي أدوات مسموحة بهالحالة. أول أداة هي الخيار الأأمن."""
    action = state.get("user_action", "message")

    # في بيان موجود
    if state.get("statement"):
        if action in ("confirm", "proceed"):
            return ["finalize_statement"]
        return ["revise_statement"]

    # ما في بيان لسا
    a = state.get("assessment") or {}
    ready = a.get("ready_to_draft") or not a.get("critical_missing", True)
    asked = state.get("questions_asked", 0)

    if action == "proceed" or ready or asked >= MAX_QUESTIONS:
        return ["draft_statement"]
    return ["ask_clarification", "draft_statement"]


def agent(state):
    """عقدة الـ agent: بتختار الأداة اللي لازم تشتغل بهالدور."""
    events.progress(Kind.AGENT, "Agent is choosing a tool")

    allowed = allowed_tools(state)
    reason = "only one valid tool"

    if len(allowed) == 1:
        tool = allowed[0]
    else:
        # في أكتر من خيار: الموديل بيقرر
        a = state.get("assessment") or {}
        prompt = AGENT_PROMPT.format(
            tools="\n".join(f"- {name}: {TOOLS[name]}" for name in allowed),
            last_message=last_user_message(state.get("messages", [])),
            known_facts=join_list(a.get("known_facts")),
            missing_info=join_list(a.get("missing_info")),
            questions_asked=state.get("questions_asked", 0),
        )
        tool = ""
        try:
            choice = ask_json(prompt)
            tool = str(choice.get("tool", "")).strip()
            reason = str(choice.get("reason", "")).strip() or "model choice"
        except Exception as exc:
            print(f"[AGENT FALLBACK] {type(exc).__name__}: {exc}", flush=True)

        if tool not in allowed:
            tool = allowed[0]            # الخيار الآمن
            reason = "invalid choice, using the safe default"

    events.progress(Kind.TOOL, f"Agent chose: {tool} ({reason})")
    return {"next_tool": tool}

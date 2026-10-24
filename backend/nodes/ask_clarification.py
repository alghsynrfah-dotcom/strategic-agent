from backend import events
from backend.agent.llm import stream_text
from backend.events import Kind
from backend.nodes.helpers import (
    detect_language,
    join_list,
    last_user_message,
    previous_questions,
)
from backend.prompts.prompts import ASK_PROMPT


def ask_clarification(state):
    """أداة: بتطرح أهم سؤال توضيحي واحد، بلغة المستخدم وبدون تكرار."""
    events.progress(Kind.ASK, "Preparing a clarifying question")

    a = state["assessment"]
    messages = state.get("messages", [])
    question = a.get("most_important_question") or "Can you share more details about the problem?"

    prompt = ASK_PROMPT.format(
        language=detect_language(messages),
        question=question,
        known_facts=join_list(a.get("known_facts")),
        previous_questions=previous_questions(messages),
        last_message=last_user_message(messages),
    )
    text = stream_text(prompt)

    return {
        "response": text,
        "decision": "ask",
        "questions_asked": state.get("questions_asked", 0) + 1,
        "messages": [{"role": "assistant", "content": text}],
    }

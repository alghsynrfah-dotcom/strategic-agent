import json
import os
import re
from functools import lru_cache

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from backend import events

load_dotenv()


@lru_cache(maxsize=1)
def get_model():
    api_url = os.getenv("VLLM_API_URL")
    api_key = os.getenv("VLLM_API_KEY")
    model_name = os.getenv("MODEL_NAME")

    for name, value in [
        ("VLLM_API_URL", api_url),
        ("VLLM_API_KEY", api_key),
        ("MODEL_NAME", model_name),
    ]:
        if not value:
            raise ValueError(f"{name} is missing from .env")

    return ChatOpenAI(
        model=model_name,
        temperature=0,
        api_key=api_key,
        base_url=api_url,
        timeout=120,
    )


def ask_json(prompt: str) -> dict:
    """Ask the model and parse a JSON object from its reply."""
    reply = get_model().invoke([HumanMessage(content=prompt)]).content
    match = re.search(r"\{.*\}", str(reply), re.DOTALL)
    if not match:
        raise ValueError("Model did not return JSON")
    return json.loads(match.group(0))


def stream_text(prompt: str) -> str:
    """Stream the model reply token by token to the UI. Returns full text."""
    full_text = ""

    for chunk in get_model().stream([HumanMessage(content=prompt)]):
        piece = chunk.content
        if isinstance(piece, str) and piece:
            full_text += piece
            events.token(piece)

    return full_text.strip()

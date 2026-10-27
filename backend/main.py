import json
import time
import uuid
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend import storage
from backend.context import build_context
from backend.events import Kind
from backend.graph.graph import graph

app = FastAPI(title="Strategic Intelligent Agent API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",    
        "http://localhost:5500",
        "http://127.0.0.1:5500",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

storage.init_db()


class ProjectCreate(BaseModel):
    domain: Literal["financial", "economic"]


class ChatRequest(BaseModel):
    project_id: str
    message: str = Field("", max_length=3000)
    user_action: Literal["message", "edit", "confirm", "proceed"] = "message"


def sse(event: str, data: dict) -> str:
    payload = json.dumps(data, ensure_ascii=False, default=str)
    return f"event: {event}\ndata: {payload}\n\n"


def build_result(state: dict, project_id: str, execution_time: float) -> dict:
    return {
        "project_id": project_id,
        "decision": state.get("decision", ""),
        "response": state.get("response", ""),
        "statement": state.get("statement", ""),
        "statement_status": state.get("statement_status", "none"),
        "assumptions": state.get("assumptions", []),
        "plan": state.get("plan", ""),
        "risks": state.get("risks", ""),
        "questions_asked": state.get("questions_asked", 0),
        "execution_time": round(execution_time, 3),
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/projects")
def create_project(request: ProjectCreate):
    project_id = str(uuid.uuid4())
    storage.create_project(project_id, request.domain)
    return {"project_id": project_id, "domain": request.domain}


@app.get("/projects/{project_id}")
def get_project(project_id: str):
    project = storage.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    return {**project, "messages": storage.list_messages(project_id)}


@app.post("/chat/stream")
def chat_stream(request: ChatRequest):
    project = storage.get_project(request.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    text = request.message.strip()
    if request.user_action in ("message", "edit") and not text:
        raise HTTPException(status_code=422, detail="Message cannot be empty.")

    config = {
        "configurable": {"thread_id": request.project_id},
        "recursion_limit": 15,
    }

    state_input = {
        "project_id": request.project_id,
        "domain": project["domain"],
        **build_context(project),
        "user_action": request.user_action,
        "messages": [{"role": "user", "content": text}] if text else [],
    }

    if text:
        storage.add_message(request.project_id, "user", text)

    def event_stream():
        start_time = time.perf_counter()

        try:
            for chunk in graph.stream(state_input, config=config, stream_mode="custom"):
                if chunk.get("kind") == Kind.TOKEN:
                    yield sse("token", chunk)
                else:
                    yield sse("progress", chunk)

            state = dict(graph.get_state(config).values)
            result = build_result(state, request.project_id, time.perf_counter() - start_time)

            # حفظ رد الوكيل + المشكلة الأولية + البيان وحالته + الخطة والمخاطر
            if result["response"]:
                storage.add_message(request.project_id, "assistant", result["response"])
            storage.update_project(
                request.project_id,
                state.get("initial_problem", ""),
                state.get("statement", ""),
                state.get("statement_status", "none"),
                state.get("plan", ""),
                state.get("risks", ""),
            )

            yield sse("done", result)

        except Exception as exc:
            print(f"[API ERROR] {type(exc).__name__}: {exc}", flush=True)
            yield sse("error", {"error": f"{type(exc).__name__}: {exc}"})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

"""
api/main.py

FastAPI application entry point.

Endpoints
---------
  POST /chat          – Send a message; returns the agent's reply
  GET  /session/{id}  – Retrieve session history from checkpointer
  GET  /health        – Liveness check
"""
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.agents.graph import build_graph
from app.memory.checkpointer import get_checkpointer
from app.config import get_settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App-level state (graph is built once at startup)
# ---------------------------------------------------------------------------

_graph = None
_checkpointer_ctx = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _graph, _checkpointer_ctx

    s = get_settings()
    if s.langchain_tracing_v2:
        import os
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_API_KEY"] = s.langchain_api_key
        os.environ["LANGCHAIN_PROJECT"] = s.langchain_project

    logger.info("Starting up: building graph with Supabase checkpointer")
    _checkpointer_ctx = get_checkpointer()
    checkpointer = await _checkpointer_ctx.__aenter__()
    _graph = build_graph(checkpointer)

    yield

    logger.info("Shutting down: closing checkpointer")
    await _checkpointer_ctx.__aexit__(None, None, None)


app = FastAPI(
    title="Sales Agent API",
    version="1.0.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    session_id: str
    message: str
    lead_email: Optional[str] = None   # if known, pre-loads CRM context


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    intent: str
    lead_score: float


# ---------------------------------------------------------------------------
# Chat endpoint
# ---------------------------------------------------------------------------

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    if _graph is None:
        raise HTTPException(status_code=503, detail="Graph not initialised")

    # Thread config ties the LangGraph checkpoint to this session
    config = {"configurable": {"thread_id": req.session_id}}

    # Pre-load CRM context if an email was provided
    crm_context: dict = {}
    if req.lead_email:
        from app.tools.sales_tools import lookup_lead
        crm_context = lookup_lead.invoke({"email": req.lead_email}) or {}

    initial_state = {
        "messages": [{"role": "user", "content": req.message}],
        "session_id": req.session_id,
        "crm_context": crm_context,
        "intent": "",
        "next": "product",
    }

    try:
        result = await _graph.ainvoke(initial_state, config=config)
    except Exception as e:
        logger.exception("Graph invocation failed for session %s", req.session_id)
        raise HTTPException(status_code=500, detail=str(e))

    # Last message from the assistant
    reply = ""
    for msg in reversed(result.get("messages", [])):
        role = getattr(msg, "type", None) or msg.get("role", "")
        if role in ("ai", "assistant"):
            reply = msg.content if hasattr(msg, "content") else msg.get("content", "")
            break

    return ChatResponse(
        session_id=req.session_id,
        reply=reply,
        intent=result.get("intent", ""),
        lead_score=result.get("lead_score", 0.0),
    )


# ---------------------------------------------------------------------------
# Session history endpoint
# ---------------------------------------------------------------------------

@app.get("/session/{session_id}")
async def get_session(session_id: str):
    if _graph is None:
        raise HTTPException(status_code=503, detail="Graph not initialised")

    config = {"configurable": {"thread_id": session_id}}
    try:
        state = await _graph.aget_state(config)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Session not found: {e}")

    messages = [
        {
            "role": getattr(m, "type", "unknown"),
            "content": getattr(m, "content", str(m)),
        }
        for m in state.values.get("messages", [])
    ]
    return {
        "session_id": session_id,
        "messages": messages,
        "lead_score": state.values.get("lead_score", 0.0),
        "intent": state.values.get("intent", ""),
    }


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok", "graph_ready": _graph is not None}

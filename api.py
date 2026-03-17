"""
FastAPI backend — wraps the Python agent for the Next.js frontend.
Run: uvicorn api:app --reload --port 8000
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.agent import AgentState, run_turn
from src.ingest import get_client

app = FastAPI(title="ContextShop API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

qdrant = get_client()

# In-memory session store: session_id → AgentState
_sessions: dict[str, AgentState] = {}


class ChatRequest(BaseModel):
    session_id: str
    message: str


class MetricsOut(BaseModel):
    turn_num: int
    avg_product_score: float
    total_tokens: int
    episodic_chunks: int
    preference_chunks: int
    facts_extracted: int
    summary_created: bool
    scores: list[float]


class ChatResponse(BaseModel):
    answer: str
    session_id: str
    metrics: MetricsOut


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    state = _sessions.get(req.session_id, AgentState(session_id=req.session_id))

    try:
        answer, new_state = run_turn(req.message, state, qdrant, verbose=False)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    _sessions[req.session_id] = new_state
    latest = new_state.tracker.turns[-1]

    return ChatResponse(
        answer=answer,
        session_id=req.session_id,
        metrics=MetricsOut(
            turn_num=latest.turn_num,
            avg_product_score=round(latest.avg_product_score, 3),
            total_tokens=latest.total_tokens,
            episodic_chunks=latest.episodic_chunks,
            preference_chunks=latest.preference_chunks,
            facts_extracted=latest.facts_extracted,
            summary_created=latest.summary_created,
            scores=[round(t.avg_product_score, 3) for t in new_state.tracker.turns],
        ),
    )


@app.delete("/session/{session_id}")
def reset_session(session_id: str):
    _sessions.pop(session_id, None)
    return {"status": "reset", "session_id": session_id}


@app.get("/health")
def health():
    return {"status": "ok"}

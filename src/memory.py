"""
WRITE + COMPRESS strategies.

Write:    after each turn, extract user preference facts → embed → upsert to user_preferences/
Compress: every N turns, summarize conversation history → embed → upsert to episodic_memory/
"""

import json
import time
import uuid
from dataclasses import dataclass

from openai import OpenAI
from fastembed import TextEmbedding
from qdrant_client import QdrantClient, models

from src.config import (
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    COLLECTION_EPISODIC,
    COLLECTION_PREFERENCES,
    COMPRESS_EVERY_N_TURNS,
    DENSE_MODEL,
    LLM_FAST,
)

_dense_model: TextEmbedding | None = None


def _get_dense_model() -> TextEmbedding:
    global _dense_model
    if _dense_model is None:
        _dense_model = TextEmbedding(DENSE_MODEL)
    return _dense_model


def _embed(text: str) -> list[float]:
    return list(_get_dense_model().embed([text]))[0].tolist()


@dataclass(frozen=True)
class PreferenceFact:
    fact: str
    category: str
    confidence: float


@dataclass(frozen=True)
class ConversationTurn:
    turn_num: int
    user_query: str
    agent_answer: str


_FACT_EXTRACTION_PROMPT = """You are analyzing a single conversation turn between a user and a retail shopping assistant.

Extract any user preferences, constraints, or facts revealed. Return ONLY valid JSON — an array of objects.
Each object: {{"fact": str, "category": str, "confidence": float 0-1}}

Categories: brand, price_range, style, material, use_case, size, color, sport, other

Examples:
- User mentions "under $100" → {{"fact": "budget under $100", "category": "price_range", "confidence": 0.95}}
- User mentions "Nike shoes" → {{"fact": "prefers Nike brand", "category": "brand", "confidence": 0.8}}
- No clear preference → return []

Conversation turn:
User: {user_query}
Assistant: {agent_answer}

Return JSON array only, no other text."""


_COMPRESSION_PROMPT = """Summarize these {n} conversation turns in 2-3 sentences.

Preserve:
- user's stated needs and goals
- budget or constraints mentioned
- products or brands discussed
- any decisions or preferences expressed

Discard: greetings, filler, repeated information.

Turns:
{turns_text}

Summary (2-3 sentences only):"""


def _get_llm_client() -> OpenAI:
    return OpenAI(
        base_url=OPENROUTER_BASE_URL,
        api_key=OPENROUTER_API_KEY,
        default_headers={"X-Title": "ContextShop"},
    )


def extract_preferences(turn: ConversationTurn) -> list[PreferenceFact]:
    """Call LLM to extract user facts from a single conversation turn."""
    client = _get_llm_client()

    prompt = _FACT_EXTRACTION_PROMPT.format(
        user_query=turn.user_query,
        agent_answer=turn.agent_answer,
    )

    response = client.chat.completions.create(
        model=LLM_FAST,
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.choices[0].message.content.strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        facts_data = json.loads(raw)
        return [
            PreferenceFact(
                fact=f.get("fact", ""),
                category=f.get("category", "other"),
                confidence=float(f.get("confidence", 0.5)),
            )
            for f in facts_data
            if f.get("fact")
        ]
    except (json.JSONDecodeError, KeyError):
        return []


def compress_turns(turns: list[ConversationTurn]) -> str:
    """Call LLM to compress N conversation turns into a summary."""
    client = _get_llm_client()

    turns_text = "\n".join(
        f"Turn {t.turn_num}:\nUser: {t.user_query}\nAssistant: {t.agent_answer}"
        for t in turns
    )

    prompt = _COMPRESSION_PROMPT.format(n=len(turns), turns_text=turns_text)

    response = client.chat.completions.create(
        model=LLM_FAST,
        max_tokens=256,
        messages=[{"role": "user", "content": prompt}],
    )

    return response.choices[0].message.content.strip()


def upsert_preferences(client: QdrantClient, facts: list[PreferenceFact], session_id: str) -> int:
    """Embed and upsert preference facts to Qdrant, namespaced by session_id."""
    if not facts:
        return 0

    points = []
    for fact in facts:
        vec = _embed(fact.fact)
        points.append(
            models.PointStruct(
                id=str(uuid.uuid4()),
                vector={"dense": vec},
                payload={
                    "fact": fact.fact,
                    "category": fact.category,
                    "confidence": fact.confidence,
                    "timestamp": time.time(),
                    "session_id": session_id,
                },
            )
        )

    client.upsert(collection_name=COLLECTION_PREFERENCES, points=points)
    return len(points)


def upsert_episodic(client: QdrantClient, summary: str, turn_count: int, session_id: str) -> None:
    """Embed and upsert a compressed conversation summary, namespaced by session_id."""
    vec = _embed(summary)
    client.upsert(
        collection_name=COLLECTION_EPISODIC,
        points=[
            models.PointStruct(
                id=str(uuid.uuid4()),
                vector={"dense": vec},
                payload={
                    "summary": summary,
                    "turn_count": turn_count,
                    "timestamp": time.time(),
                    "session_id": session_id,
                },
            )
        ],
    )


def should_compress(turn_num: int) -> bool:
    return turn_num > 0 and turn_num % COMPRESS_EVERY_N_TURNS == 0


def process_turn_memory(
    qdrant: QdrantClient,
    turn: ConversationTurn,
    recent_turns: list[ConversationTurn],
    session_id: str,
) -> dict:
    """
    After each agent turn:
    1. Extract and upsert preference facts (Write strategy)
    2. If trigger: compress recent turns and upsert (Compress strategy)

    Returns dict with counts for metrics.
    """
    facts = extract_preferences(turn)
    facts_upserted = upsert_preferences(qdrant, facts, session_id)

    summary_created = False
    if should_compress(turn.turn_num) and len(recent_turns) >= COMPRESS_EVERY_N_TURNS:
        turns_to_compress = recent_turns[-COMPRESS_EVERY_N_TURNS:]
        summary = compress_turns(turns_to_compress)
        upsert_episodic(qdrant, summary, turn.turn_num, session_id)
        summary_created = True

    return {
        "facts_extracted": len(facts),
        "facts_upserted": facts_upserted,
        "summary_created": summary_created,
        "facts": [f.fact for f in facts],
    }

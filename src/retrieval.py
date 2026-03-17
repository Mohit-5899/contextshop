"""
SELECT strategy: retrieve just the right chunks from all 3 collections.

Products: hybrid search (SPLADE sparse + dense, RRF fusion)
Episodic memory: semantic search (dense only)
User preferences: semantic search (dense only)
"""

from dataclasses import dataclass

from fastembed import SparseTextEmbedding, TextEmbedding
from qdrant_client import QdrantClient, models
from qdrant_client.models import Fusion, FusionQuery, Prefetch, SparseVector

from src.config import (
    COLLECTION_EPISODIC,
    COLLECTION_PREFERENCES,
    COLLECTION_PRODUCTS,
    DENSE_MODEL,
    SPARSE_MODEL,
)

# Module-level model singletons (loaded once)
_dense_model: TextEmbedding | None = None
_sparse_model: SparseTextEmbedding | None = None


def _get_dense_model() -> TextEmbedding:
    global _dense_model
    if _dense_model is None:
        _dense_model = TextEmbedding(DENSE_MODEL)
    return _dense_model


def _get_sparse_model() -> SparseTextEmbedding:
    global _sparse_model
    if _sparse_model is None:
        _sparse_model = SparseTextEmbedding(SPARSE_MODEL)
    return _sparse_model


@dataclass(frozen=True)
class RetrievedChunk:
    source: str          # "products" | "episodic" | "preferences"
    content: str         # human-readable text for context window
    score: float
    payload: dict


def _embed_dense(text: str) -> list[float]:
    model = _get_dense_model()
    return list(model.embed([text]))[0].tolist()


def _embed_sparse(text: str) -> SparseVector:
    model = _get_sparse_model()
    result = list(model.embed([text]))[0]
    return SparseVector(indices=result.indices.tolist(), values=result.values.tolist())


def search_products(client: QdrantClient, query: str, limit: int = 5) -> list[RetrievedChunk]:
    """Hybrid search: SPLADE sparse + dense vectors, fused with RRF."""
    dense_vec = _embed_dense(query)
    sparse_vec = _embed_sparse(query)

    results = client.query_points(
        collection_name=COLLECTION_PRODUCTS,
        prefetch=[
            Prefetch(query=dense_vec, using="dense", limit=20),
            Prefetch(query=sparse_vec, using="sparse", limit=20),
        ],
        query=FusionQuery(fusion=Fusion.RRF),
        limit=limit,
        with_payload=True,
    )

    return [
        RetrievedChunk(
            source="products",
            content=_format_product(r.payload),
            score=r.score,
            payload=r.payload,
        )
        for r in results.points
    ]


def search_episodic(
    client: QdrantClient, query: str, session_id: str, limit: int = 3
) -> list[RetrievedChunk]:
    """Semantic search over compressed conversation summaries for this session."""
    dense_vec = _embed_dense(query)

    results = client.query_points(
        collection_name=COLLECTION_EPISODIC,
        query=dense_vec,
        using="dense",
        limit=limit,
        with_payload=True,
        query_filter=models.Filter(
            must=[models.FieldCondition(key="session_id", match=models.MatchValue(value=session_id))]
        ),
    )

    return [
        RetrievedChunk(
            source="episodic",
            content=r.payload.get("summary", ""),
            score=r.score,
            payload=r.payload,
        )
        for r in results.points
    ]


def search_preferences(
    client: QdrantClient, query: str, session_id: str, limit: int = 5
) -> list[RetrievedChunk]:
    """Semantic search over learned user preference facts for this session."""
    dense_vec = _embed_dense(query)

    results = client.query_points(
        collection_name=COLLECTION_PREFERENCES,
        query=dense_vec,
        using="dense",
        limit=limit,
        with_payload=True,
        query_filter=models.Filter(
            must=[models.FieldCondition(key="session_id", match=models.MatchValue(value=session_id))]
        ),
    )

    return [
        RetrievedChunk(
            source="preferences",
            content=r.payload.get("fact", ""),
            score=r.score,
            payload=r.payload,
        )
        for r in results.points
    ]


def search_all(
    client: QdrantClient,
    query: str,
    session_id: str,
    product_limit: int = 5,
    episodic_limit: int = 3,
    preference_limit: int = 5,
) -> dict[str, list[RetrievedChunk]]:
    """Search all three collections and return grouped results."""
    return {
        "products": search_products(client, query, product_limit),
        "episodic": search_episodic(client, query, session_id, episodic_limit),
        "preferences": search_preferences(client, query, session_id, preference_limit),
    }


def avg_product_score(chunks: list[RetrievedChunk]) -> float:
    """Average retrieval score for product results — used in metrics."""
    if not chunks:
        return 0.0
    return sum(c.score for c in chunks) / len(chunks)


def _format_product(payload: dict) -> str:
    title = payload.get("title", "Unknown")
    price = payload.get("price", "N/A")
    rating = payload.get("rating", 0)
    desc = payload.get("description", "")[:200]
    return f"[{title}] Price: ${price} | Rating: {rating}/5 | {desc}"

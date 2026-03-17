"""
Token budget allocation + XML context assembly.

Allocates the 8K token budget across 3 collection results and assembles
the final context string with XML tags for clear LLM parsing.
"""

import tiktoken

from src.config import (
    BUDGET_EPISODIC_RATIO,
    BUDGET_PREFERENCES_RATIO,
    BUDGET_PRODUCTS_RATIO,
    TOKEN_BUDGET,
)
from src.retrieval import RetrievedChunk

_encoder = tiktoken.get_encoding("cl100k_base")

SYSTEM_RESERVE = 600   # tokens reserved for system prompt
OUTPUT_RESERVE = 1_200  # tokens reserved for model output


def count_tokens(text: str) -> int:
    return len(_encoder.encode(text))


def _trim_to_budget(chunks: list[RetrievedChunk], budget: int) -> list[RetrievedChunk]:
    """Return as many chunks as fit within the token budget, highest score first."""
    kept = []
    used = 0
    for chunk in sorted(chunks, key=lambda c: c.score, reverse=True):
        tokens = count_tokens(chunk.content)
        if used + tokens > budget:
            break
        kept.append(chunk)
        used += tokens
    return kept


def _allocate_budgets() -> dict[str, int]:
    available = TOKEN_BUDGET - SYSTEM_RESERVE - OUTPUT_RESERVE
    return {
        "products": int(available * BUDGET_PRODUCTS_RATIO),
        "episodic": int(available * BUDGET_EPISODIC_RATIO),
        "preferences": int(available * BUDGET_PREFERENCES_RATIO),
    }


def assemble_context(
    retrieved: dict[str, list[RetrievedChunk]],
    query: str,
) -> tuple[str, dict]:
    """
    Build the context string with XML tags.

    Returns:
        context_str: the assembled context to inject into the LLM prompt
        stats: token usage breakdown for metrics
    """
    budgets = _allocate_budgets()

    trimmed_products = _trim_to_budget(retrieved.get("products", []), budgets["products"])
    trimmed_episodic = _trim_to_budget(retrieved.get("episodic", []), budgets["episodic"])
    trimmed_preferences = _trim_to_budget(retrieved.get("preferences", []), budgets["preferences"])

    products_text = "\n".join(f"- {c.content}" for c in trimmed_products)
    episodic_text = "\n".join(f"- {c.content}" for c in trimmed_episodic)
    preferences_text = "\n".join(f"- {c.content}" for c in trimmed_preferences)

    parts = []

    if products_text:
        parts.append(f"<products>\n{products_text}\n</products>")

    if episodic_text:
        parts.append(f"<conversation_memory>\n{episodic_text}\n</conversation_memory>")

    if preferences_text:
        parts.append(f"<user_preferences>\n{preferences_text}\n</user_preferences>")

    parts.append(f"<query>\n{query}\n</query>")

    context_str = "\n\n".join(parts)

    stats = {
        "products_chunks": len(trimmed_products),
        "episodic_chunks": len(trimmed_episodic),
        "preference_chunks": len(trimmed_preferences),
        "total_tokens": count_tokens(context_str),
        "products_tokens": count_tokens(products_text),
        "episodic_tokens": count_tokens(episodic_text),
        "preferences_tokens": count_tokens(preferences_text),
    }

    return context_str, stats


SYSTEM_PROMPT = """You are a helpful retail shopping assistant specializing in sports and outdoor equipment.

You have access to:
- <products>: relevant products from the catalog
- <conversation_memory>: summaries of past conversations with this user
- <user_preferences>: known facts about this user's preferences

Use all available context to give specific, personalized recommendations.
Be concise and direct. Mention product names and prices when relevant.
If user preferences are available, tailor your answer to them."""

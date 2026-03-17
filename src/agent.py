"""
Main agent loop.

Ties together: retrieval (Select) → context assembly → LLM answer → memory update (Write + Compress).
"""

import uuid
from dataclasses import dataclass, field

from openai import OpenAI
from qdrant_client import QdrantClient

from src.config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, LLM_MAIN
from src.context_builder import SYSTEM_PROMPT, assemble_context
from src.memory import ConversationTurn, process_turn_memory
from src.metrics import MetricsTracker, TurnMetrics
from src.retrieval import avg_product_score, search_all


@dataclass
class AgentState:
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    turn_num: int = 0
    history: list[ConversationTurn] = field(default_factory=list)
    tracker: MetricsTracker = field(default_factory=MetricsTracker)


def run_turn(
    query: str,
    state: AgentState,
    qdrant: QdrantClient,
    verbose: bool = True,
) -> tuple[str, AgentState]:
    """
    Process one user query. Returns (answer, updated_state).

    State is never mutated — a new AgentState is returned.
    """
    # 1. SELECT: retrieve from all 3 collections (memory filtered by session_id)
    retrieved = search_all(qdrant, query, session_id=state.session_id)

    # 2. BUILD context with token budget
    context_str, context_stats = assemble_context(retrieved, query)

    # 3. GENERATE answer
    answer = _call_llm(context_str)

    # 4. Build turn record
    turn = ConversationTurn(
        turn_num=state.turn_num,
        user_query=query,
        agent_answer=answer,
    )

    # 5. WRITE + COMPRESS: update memory in Qdrant (tagged with session_id)
    mem_stats = process_turn_memory(qdrant, turn, state.history, session_id=state.session_id)

    # 6. Record metrics
    product_score = avg_product_score(retrieved["products"])
    turn_metrics = TurnMetrics(
        turn_num=state.turn_num,
        query=query,
        avg_product_score=product_score,
        total_tokens=context_stats["total_tokens"],
        products_chunks=context_stats["products_chunks"],
        episodic_chunks=context_stats["episodic_chunks"],
        preference_chunks=context_stats["preference_chunks"],
        facts_extracted=mem_stats["facts_extracted"],
        summary_created=mem_stats["summary_created"],
        answer_preview=answer[:120],
    )

    if verbose:
        state.tracker.print_turn(turn_metrics)

    # 7. Return new state (immutable pattern — new object, same session_id)
    new_history = [*state.history, turn]
    new_tracker = state.tracker
    new_tracker.record(turn_metrics)

    return answer, AgentState(
        session_id=state.session_id,
        turn_num=state.turn_num + 1,
        history=new_history,
        tracker=new_tracker,
    )


def _call_llm(context_str: str) -> str:
    client = OpenAI(
        base_url=OPENROUTER_BASE_URL,
        api_key=OPENROUTER_API_KEY,
        default_headers={"X-Title": "ContextShop"},
    )
    response = client.chat.completions.create(
        model=LLM_MAIN,
        max_tokens=512,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": context_str},
        ],
    )
    return response.choices[0].message.content.strip()


def run_interactive(qdrant: QdrantClient) -> None:
    """Interactive CLI loop."""
    state = AgentState()
    print(f"\nContextShop — Retail AI Agent  [session: {state.session_id[:8]}]")
    print("Type your shopping question. 'quit' to exit. 'stats' for metrics.\n")

    while True:
        try:
            query = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            break

        if not query:
            continue
        if query.lower() == "quit":
            break
        if query.lower() == "stats":
            state.tracker.print_comparison()
            state.tracker.print_all_scores()
            continue

        answer, state = run_turn(query, state, qdrant)
        print(f"\nAssistant: {answer}\n")

    print("\nSession ended.")
    if state.history:
        state.tracker.print_comparison()
        state.tracker.print_all_scores()

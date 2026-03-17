"""
Demo script: cold start → warm context comparison.

Runs a scripted conversation showing measurable context improvement.
Run: python demo.py
"""

import time

from src.agent import AgentState, run_turn
from src.ingest import get_client

DEMO_TURNS = [
    "I need a good running shoe",
    "I prefer something waterproof, my budget is around $80 to $120",
    "Do you have anything from Nike or Adidas in that range?",
    "What about trail running specifically? I run on muddy terrain",
    "Can you also recommend some running socks to go with it?",
    # Repeat original query — should be measurably better now
    "I need a good running shoe",
]


def run_demo() -> None:
    qdrant = get_client()
    state = AgentState()

    print("\n" + "=" * 60)
    print("ContextShop — Context Engineering Demo")
    print("=" * 60)
    print("\nThis demo shows how context improves over 6 turns.")
    print("Turn 0 and Turn 5 ask the same question.")
    print("Watch the retrieval scores and memory chunks grow.\n")
    time.sleep(1)

    cold_answer = None
    warm_answer = None

    for i, query in enumerate(DEMO_TURNS):
        print(f"\n[Sending turn {i}]: {query}")
        answer, state = run_turn(query, state, qdrant, verbose=True)

        if i == 0:
            cold_answer = answer
        if i == len(DEMO_TURNS) - 1:
            warm_answer = answer

    # Final comparison
    print("\n" + "=" * 60)
    print("SAME QUERY — DIFFERENT CONTEXT")
    print("=" * 60)
    print(f"\nQuery: 'I need a good running shoe'\n")
    print(f"COLD (Turn 0):\n{cold_answer}\n")
    print(f"WARM (Turn {len(DEMO_TURNS) - 1}):\n{warm_answer}\n")

    state.tracker.print_comparison()
    state.tracker.print_all_scores()


if __name__ == "__main__":
    run_demo()

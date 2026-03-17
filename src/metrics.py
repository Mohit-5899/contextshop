"""
Track and display context improvement metrics across conversation turns.

Shows: retrieval scores, token usage, memory growth — the proof that context improves.
"""

from dataclasses import dataclass, field


@dataclass
class TurnMetrics:
    turn_num: int
    query: str
    avg_product_score: float
    total_tokens: int
    products_chunks: int
    episodic_chunks: int
    preference_chunks: int
    facts_extracted: int
    summary_created: bool
    answer_preview: str  # first 120 chars


@dataclass
class MetricsTracker:
    turns: list[TurnMetrics] = field(default_factory=list)

    def record(self, metrics: TurnMetrics) -> None:
        self.turns.append(metrics)

    def print_turn(self, m: TurnMetrics) -> None:
        mem_active = m.episodic_chunks > 0 or m.preference_chunks > 0
        mem_label = "WARM" if mem_active else "COLD"
        print(
            f"\n{'='*60}\n"
            f"Turn {m.turn_num} [{mem_label}]\n"
            f"Query: {m.query[:80]}\n"
            f"{'─'*60}\n"
            f"  Retrieval score (avg): {m.avg_product_score:.3f}\n"
            f"  Context tokens used:   {m.total_tokens}\n"
            f"  Products retrieved:    {m.products_chunks}\n"
            f"  Episodic memory:       {m.episodic_chunks} chunks\n"
            f"  User preferences:      {m.preference_chunks} facts\n"
            f"  New facts extracted:   {m.facts_extracted}\n"
            f"  Compression triggered: {'yes' if m.summary_created else 'no'}\n"
            f"{'─'*60}\n"
            f"Answer: {m.answer_preview}...\n"
        )

    def print_comparison(self) -> None:
        if len(self.turns) < 2:
            print("Not enough turns for comparison yet.")
            return

        cold = self.turns[0]
        warm = self.turns[-1]

        score_delta = warm.avg_product_score - cold.avg_product_score
        token_delta = warm.total_tokens - cold.total_tokens
        pref_growth = warm.preference_chunks - cold.preference_chunks
        ep_growth = warm.episodic_chunks - cold.episodic_chunks

        print(
            f"\n{'='*60}\n"
            f"CONTEXT IMPROVEMENT SUMMARY\n"
            f"{'='*60}\n"
            f"  Turns compared: Turn {cold.turn_num} (cold) → Turn {warm.turn_num} (warm)\n"
            f"\n"
            f"  Retrieval score:  {cold.avg_product_score:.3f} → {warm.avg_product_score:.3f}  "
            f"({'+' if score_delta >= 0 else ''}{score_delta:.3f})\n"
            f"\n"
            f"  Token efficiency:\n"
            f"    Products tokens: {cold.products_chunks} → {warm.products_chunks} chunks\n"
            f"    Total context:   {cold.total_tokens} → {warm.total_tokens} tokens\n"
            f"    Delta:           {'+' if token_delta >= 0 else ''}{token_delta} tokens\n"
            f"\n"
            f"  Memory growth:\n"
            f"    Preference facts: +{pref_growth} chunks added\n"
            f"    Episodic memory:  +{ep_growth} summaries added\n"
            f"\n"
            f"{'='*60}"
        )

    def print_all_scores(self) -> None:
        print("\nRetrieval score progression:")
        for m in self.turns:
            bar = "█" * int(m.avg_product_score * 20)
            mem = f"[E:{m.episodic_chunks} P:{m.preference_chunks}]"
            print(f"  Turn {m.turn_num}: {bar:<20} {m.avg_product_score:.3f} {mem}")

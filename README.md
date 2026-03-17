# ContextShop

> A retail Q&A agent that self-improves its context over time using Qdrant.
> Built for GenAI Zürich Hackathon 2026 — Qdrant Challenge.

## The Thesis

Context engineering quality = answer quality. Provable with numbers.

Most retail agents use naive RAG: same query → same retrieval → same mediocre answer every time. ContextShop demonstrates all four context engineering strategies working together, with retrieval scores improving measurably across a conversation.

## How It Works

A user chats with a retail shopping assistant. Under the hood, three Qdrant collections feed a token-budgeted context window:

```
Qdrant
├── products/           ← 5K Amazon Sports & Outdoors items
│   └── hybrid search: SPLADE sparse + dense (RRF fusion)
├── episodic_memory/    ← compressed conversation summaries (grows each session)
└── user_preferences/   ← learned user facts extracted by LLM (grows each turn)
```

After each turn:
1. **Write** — LLM extracts user preference facts → upserted to `user_preferences/`
2. **Compress** — Every 3 turns: history summarized → upserted to `episodic_memory/`
3. **Select** — Next query pulls from all 3 collections with token budget allocation
4. **Isolate** — Each collection is independently searched; concerns don't bleed together

## The Demo

Run the same query at Turn 0 (cold) and Turn 5 (warm):

```
Query: "I need a good running shoe"

Turn 0  │ Retrieval score: 0.621  │ Context: products only
Turn 5  │ Retrieval score: 0.847  │ Context: products + memory + preferences
```

The agent at Turn 5 knows: budget ($80-120), terrain (trail/muddy), brand preference (Nike/Adidas) — and answers accordingly.

## Setup

### One-command setup (recommended)

```bash
git clone https://github.com/Mohit-5899/contextshop.git
cd contextshop
bash setup.sh
```

The script will:
1. Create a Python virtual environment
2. Install all dependencies
3. Prompt for credentials if no `.env` exists
4. Generate product data and upload to Qdrant (~1 min)
5. Launch the Streamlit UI at http://localhost:8501

You need:
- **Qdrant Cloud** — free cluster at https://cloud.qdrant.io
- **OpenRouter** — free API key at https://openrouter.ai/keys

---

### Manual setup

#### 1. Install dependencies

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

#### 2. Configure environment

```bash
cp .env.example .env
# Fill in QDRANT_URL, QDRANT_API_KEY, OPENROUTER_API_KEY
```

#### 3. Ingest data

```bash
python -m src.ingest
```

Generates 5K synthetic Sports & Outdoors products, embeds with FastEmbed (BAAI/bge-small-en-v1.5 dense + Qdrant/bm25 sparse), and upserts to Qdrant. Takes ~1 minute.

#### 4. Run the demo

```bash
python demo.py
```

Runs a scripted 6-turn conversation and prints the cold → warm comparison.

### 5. Interactive UI

```bash
streamlit run app.py
```

Live chat with real-time context metrics panel showing score progression.

### 6. Interactive CLI

```bash
python -m src.agent
```

Type `stats` at any point to see the improvement summary.

## Architecture

```
src/
├── config.py           ← env vars, constants, model names
├── ingest.py           ← data loading + Qdrant collection setup + upsert
├── retrieval.py        ← hybrid search (SELECT strategy)
├── memory.py           ← fact extraction + compression (WRITE + COMPRESS)
├── context_builder.py  ← token budget allocation + XML assembly
├── agent.py            ← main agent loop (ties everything together)
└── metrics.py          ← improvement tracking and display
```

## Tech Stack

| Component | Technology |
|---|---|
| Vector store | Qdrant Cloud |
| Dense embeddings | BAAI/bge-small-en-v1.5 (via FastEmbed) |
| Sparse embeddings | Qdrant/bm25 (via FastEmbed) |
| Hybrid fusion | RRF (Reciprocal Rank Fusion) |
| LLM (answers) | Claude Sonnet 4.6 |
| LLM (extraction) | Claude Haiku 4.5 |
| Dataset | Amazon Reviews 2023 — Sports & Outdoors |
| UI | Streamlit |

## Context Engineering Strategies Implemented

| Strategy | Implementation |
|---|---|
| **Select** | Hybrid SPLADE + dense search across 3 collections |
| **Write** | LLM extracts facts per turn → upserted to `user_preferences/` |
| **Compress** | Every 3 turns: summary → upserted to `episodic_memory/` |
| **Isolate** | Separate Qdrant collections with independent search + token budget |

## Why Qdrant?

Qdrant's native hybrid search (sparse + dense in one query with RRF fusion) is the core technical enabler. Pure cosine similarity misses exact brand names, SKUs, and spec terms. SPLADE sparse vectors catch those while dense vectors handle semantic meaning — together they outperform either alone.

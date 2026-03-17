# ContextShop — CLAUDE.md

GenAI Zürich Hackathon 2026 · Qdrant Challenge · GenAI in Retail track
Deadline: 18 March 2026 ~4:30pm IST

---

## Project Goal

Build a retail Q&A agent that **self-improves its context over time** using Qdrant.

The thesis: context engineering quality directly determines answer quality.
Prove it quantitatively — cold start vs. warmed-up context, measured by retrieval relevance scores.

---

## Core Concept: Context Engineering

Context engineering is the discipline of filling the LLM context window with exactly the right information. Four strategies, all implemented here:

| Strategy | Action | Failure Mode Prevented |
|---|---|---|
| **Select** | Retrieve just the right chunks via hybrid search | Context confusion (noise) |
| **Write** | Persist learned facts outside the window to Qdrant | Information loss |
| **Compress** | Summarize old interactions → embed → store | Context distraction (overload) |
| **Isolate** | Separate Qdrant collections per concern | All four modes |

---

## Architecture

### Three Qdrant Collections

```
Qdrant Cloud
├── products/              ← Static product catalog (Amazon data)
│   ├── dense vectors      (FastEmbed, all-MiniLM-L6-v2)
│   ├── sparse vectors     (SPLADE via FastEmbed)
│   └── payload            {title, price, category, rating, asin}
│
├── episodic_memory/       ← Compressed summaries of past interactions
│   ├── dense vectors      (embedded summaries)
│   └── payload            {summary, turn_count, timestamp}
│
└── user_preferences/      ← Learned user facts extracted per interaction
    ├── dense vectors      (embedded preference statements)
    └── payload            {fact, confidence, category, timestamp}
```

### Query Flow

```
User query
    ↓
[1] Hybrid search on products/        ← SPLADE sparse + dense (Select)
[2] Semantic search on episodic_memory/  ← what did we discuss before (Select)
[3] Semantic search on user_preferences/ ← what do we know about this user (Select)
    ↓
Token budget allocation (products 60% / episodic 25% / preferences 15%)
    ↓
Context assembly with XML tags:
  <products>...</products>
  <memory>...</memory>
  <preferences>...</preferences>
  <query>...</query>
    ↓
LLM generates answer
    ↓
[4] Extract new user facts → upsert user_preferences/  (Write)
[5] If turn_count % 3 == 0: compress history → upsert episodic_memory/  (Compress)
```

---

## Tech Stack

```
Python 3.11+
qdrant-client>=1.9.0     Qdrant Cloud SDK
fastembed>=0.3.0         SPLADE sparse + dense embeddings (local, no API cost)
anthropic>=0.25.0        Claude for answers + fact extraction
datasets / pandas        Amazon product data loading
streamlit                Demo UI (last step, optional)
python-dotenv            Environment config
```

---

## Dataset

**Amazon Product Reviews — Sports & Outdoors**
- Source: https://cseweb.ucsd.edu/~jmcauley/datasets/amazon_v2/
- Use 5K–10K item subset for the demo (fast ingest, clear demo)
- Fields used: title, description, price, category, average_rating, asin

---

## Project Structure

```
contextshop/
├── CLAUDE.md                  ← this file
├── ideas.md                   ← brainstorming and project rationale
├── .env                       ← QDRANT_URL, QDRANT_API_KEY, ANTHROPIC_API_KEY
├── requirements.txt
│
├── src/
│   ├── ingest.py              ← load Amazon data → embed → upsert to products/
│   ├── memory.py              ← Write + Compress strategies (episodic + preferences)
│   ├── retrieval.py           ← Select strategy (hybrid search across collections)
│   ├── context_builder.py     ← token budget allocation + XML assembly
│   ├── agent.py               ← main agent loop
│   └── metrics.py             ← relevance scores, token counts, improvement tracking
│
├── data/
│   └── sports_outdoors_5k.jsonl   ← local subset of Amazon data
│
├── demo.py                    ← CLI demo: cold → warm comparison
└── app.py                     ← Streamlit UI (optional)
```

---

## Key Implementation Notes

### Hybrid Search (Qdrant SPLADE)

Use `fastembed` with `SPLADE++` model for sparse vectors.
Use `all-MiniLM-L6-v2` for dense vectors.
Fusion method: **RRF (Reciprocal Rank Fusion)** — Qdrant default, no tuning needed.

```python
# Qdrant hybrid query pattern
results = client.query_points(
    collection_name="products",
    prefetch=[
        Prefetch(query=dense_vector, using="dense", limit=20),
        Prefetch(query=sparse_vector, using="sparse", limit=20),
    ],
    query=FusionQuery(fusion=Fusion.RRF),
    limit=5
)
```

### Token Budget

Total budget: 8K tokens (keep it tight for fast LLM calls)
- System prompt: ~500 tokens
- Products: ~4,800 tokens (60%)
- Episodic memory: ~2,000 tokens (25%)
- User preferences: ~1,200 tokens (15%)
- User query + output reserved: remainder

### Fact Extraction (Write Strategy)

After every LLM answer, run a second lightweight LLM call:
```
"From this conversation turn, extract any user preferences, constraints, or facts.
Return as JSON: [{fact: str, category: str, confidence: 0-1}]"
```
Embed each fact → upsert to `user_preferences/`.

### Compression Trigger (Compress Strategy)

Every 3 turns:
```
"Summarize the last 3 conversation turns into 2-3 sentences preserving:
- user's stated needs, constraints, price range
- products discussed
- any decisions made"
```
Embed summary → upsert to `episodic_memory/`.

---

## Demo Script (Cold → Warm)

Run `demo.py` which executes:

1. **Turn 0 (cold):** "I need a good running shoe"
   - Only `products/` collection active
   - Show retrieval scores + answer

2. **Turn 1–4:** user interacts, preferences learned, episodic memory builds

3. **Turn 5 (warm):** Same query: "I need a good running shoe"
   - All 3 collections active
   - Show improved retrieval scores + more specific answer

4. **Side-by-side diff** of context window: Turn 0 vs Turn 5

---

## Judging Criteria Mapping

| Criterion | How We Address It |
|---|---|
| Code quality | Clean src/ structure, typed functions, no mutation |
| Feature usage | Qdrant hybrid search, sparse vectors, multiple collections, payload filtering |
| Creativity | Context engineering thesis + quantitative proof |
| Presentation | Before/after demo with live metrics |
| Usefulness | Retail agent that provably improves — deployable pattern |

---

## Environment Variables

```
QDRANT_URL=https://your-cluster.qdrant.io
QDRANT_API_KEY=your_key
ANTHROPIC_API_KEY=your_key
COLLECTION_PRODUCTS=products
COLLECTION_EPISODIC=episodic_memory
COLLECTION_PREFERENCES=user_preferences
```

---

## Build Order

1. `ingest.py` — get data into Qdrant first (foundation for everything)
2. `retrieval.py` — hybrid search working
3. `memory.py` — Write + Compress strategies
4. `context_builder.py` — token budget assembly
5. `agent.py` — tie it all together
6. `metrics.py` — relevance scores for demo
7. `demo.py` — cold vs warm comparison script
8. README + Devpost one-pager

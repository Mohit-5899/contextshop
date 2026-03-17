import os
from dotenv import load_dotenv

load_dotenv()


def _require(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise EnvironmentError(f"Missing required environment variable: {key}")
    return value


# Qdrant
QDRANT_URL: str = _require("QDRANT_URL")
QDRANT_API_KEY: str = _require("QDRANT_API_KEY")

# OpenRouter
OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"

# Collection names
COLLECTION_PRODUCTS: str = os.getenv("COLLECTION_PRODUCTS", "products")
COLLECTION_EPISODIC: str = os.getenv("COLLECTION_EPISODIC", "episodic_memory")
COLLECTION_PREFERENCES: str = os.getenv("COLLECTION_PREFERENCES", "user_preferences")

# Embedding models
DENSE_MODEL: str = "BAAI/bge-small-en-v1.5"
SPARSE_MODEL: str = "Qdrant/bm25"
DENSE_DIM: int = 384

# Token budget (total 8K, keeps LLM calls fast)
TOKEN_BUDGET: int = 8_000
BUDGET_PRODUCTS_RATIO: float = 0.60
BUDGET_EPISODIC_RATIO: float = 0.25
BUDGET_PREFERENCES_RATIO: float = 0.15

# Memory triggers
COMPRESS_EVERY_N_TURNS: int = 3

# LLM models (OpenRouter model IDs)
LLM_MAIN: str = "anthropic/claude-sonnet-4-5"   # answers
LLM_FAST: str = "anthropic/claude-haiku-4-5"    # fact extraction, compression

# Dataset
DATASET_NAME: str = "McAuley-Lab/Amazon-Reviews-2023"
DATASET_SUBSET: str = "raw_meta_Sports_and_Outdoors"
DATASET_MAX_ITEMS: int = 5_000
DATA_PATH: str = "data/products.jsonl"

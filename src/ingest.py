"""
Ingest pipeline: load Amazon product data → embed → upsert to Qdrant products collection.

Implements the SELECT strategy foundation: hybrid search (dense + sparse vectors).
"""

# Load .env and set HF_HOME BEFORE any huggingface imports
import os
from dotenv import load_dotenv
load_dotenv()
if hf_home := os.getenv("HF_HOME"):
    os.environ["HF_HOME"] = hf_home
    os.makedirs(hf_home, exist_ok=True)

import json
from dataclasses import dataclass
from typing import Iterator

from fastembed import SparseTextEmbedding, TextEmbedding
from qdrant_client import QdrantClient, models
from tqdm import tqdm

from src.config import (
    COLLECTION_EPISODIC,
    COLLECTION_PREFERENCES,
    COLLECTION_PRODUCTS,
    DATA_PATH,
    DATASET_MAX_ITEMS,
    DATASET_NAME,
    DATASET_SUBSET,
    DENSE_DIM,
    DENSE_MODEL,
    QDRANT_API_KEY,
    QDRANT_URL,
    SPARSE_MODEL,
)

@dataclass(frozen=True)
class Product:
    asin: str
    title: str
    description: str
    price: str
    category: str
    rating: float


def get_client() -> QdrantClient:
    return QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)


def _make_product_text(product: Product) -> str:
    return f"{product.title}. {product.description} Price: {product.price}. Category: {product.category}."


def generate_synthetic_products(n: int = 1000) -> list[Product]:
    """Generate realistic synthetic sports & outdoors products for demo."""
    import random

    brands = ["Nike", "Adidas", "Columbia", "The North Face", "Patagonia", "Salomon",
              "Brooks", "ASICS", "Merrell", "Arc'teryx", "Under Armour", "Osprey",
              "Black Diamond", "Marmot", "Reebok", "New Balance", "Saucony", "Hoka"]

    categories = ["Running Shoes", "Trail Running", "Hiking Boots", "Waterproof Jackets",
                  "Backpacks", "Trekking Poles", "Climbing Gear", "Camping Tents",
                  "Sleeping Bags", "Running Socks", "Compression Tights", "Sports Watches",
                  "Hydration Packs", "Cycling Helmets", "Ski Goggles", "Snow Boots"]

    materials = ["Gore-Tex", "Merino wool", "recycled polyester", "mesh", "nylon",
                 "down insulation", "synthetic insulation", "carbon fiber", "foam"]

    features = [
        "waterproof and breathable", "lightweight at only {w}oz", "4mm drop sole",
        "EVA foam midsole", "Vibram outsole", "moisture-wicking lining",
        "YKK zippers", "DWR coating", "reinforced toe cap", "adjustable straps",
        "reflective details for low-light visibility", "antimicrobial treatment",
        "ergonomic fit", "quick-dry fabric", "compression support"
    ]

    random.seed(42)
    products = []

    for i in range(n):
        brand = random.choice(brands)
        category = random.choice(categories)
        material = random.choice(materials)
        feat1 = random.choice(features).format(w=random.randint(6, 24))
        feat2 = random.choice(features).format(w=random.randint(6, 24))
        price = round(random.uniform(29.99, 299.99), 2)
        rating = round(random.uniform(3.5, 5.0), 1)

        title = f"{brand} {category} - {material.title()} Series Model {100 + i}"
        description = (
            f"Professional-grade {category.lower()} from {brand}. "
            f"Made with {material}, {feat1}. Also features {feat2}. "
            f"Ideal for trail running, hiking, and outdoor adventures. "
            f"Available in multiple sizes and colorways."
        )

        products.append(Product(
            asin=f"B{i:09d}",
            title=title,
            description=description,
            price=str(price),
            category=category,
            rating=rating,
        ))

    return products


def load_products_from_hf() -> list[Product]:
    """Generate synthetic products and cache to DATA_PATH."""
    print(f"Generating {DATASET_MAX_ITEMS} synthetic products...")
    products = generate_synthetic_products(DATASET_MAX_ITEMS)

    os.makedirs("data", exist_ok=True)
    with open(DATA_PATH, "w") as f:
        for p in products:
            f.write(json.dumps(p.__dict__) + "\n")

    print(f"Cached {len(products)} products to {DATA_PATH}")
    return products


def load_products_from_cache() -> list[Product]:
    products = []
    with open(DATA_PATH) as f:
        for line in f:
            data = json.loads(line)
            products.append(Product(**data))
    return products


def load_products() -> list[Product]:
    if os.path.exists(DATA_PATH):
        print(f"Loading products from cache: {DATA_PATH}")
        return load_products_from_cache()
    return load_products_from_hf()


def _create_or_replace_collection(
    client: QdrantClient,
    name: str,
    vectors_config: dict,
    sparse_vectors_config: dict | None = None,
) -> None:
    if client.collection_exists(name):
        client.delete_collection(name)
    kwargs = {"collection_name": name, "vectors_config": vectors_config}
    if sparse_vectors_config:
        kwargs["sparse_vectors_config"] = sparse_vectors_config
    client.create_collection(**kwargs)
    print(f"Created collection: {name}")


def _setup_products_collection(client: QdrantClient) -> None:
    _create_or_replace_collection(
        client,
        COLLECTION_PRODUCTS,
        vectors_config={"dense": models.VectorParams(size=DENSE_DIM, distance=models.Distance.COSINE)},
        sparse_vectors_config={"sparse": models.SparseVectorParams()},
    )


def _setup_memory_collections(client: QdrantClient) -> None:
    for name in (COLLECTION_EPISODIC, COLLECTION_PREFERENCES):
        _create_or_replace_collection(
            client,
            name,
            vectors_config={"dense": models.VectorParams(size=DENSE_DIM, distance=models.Distance.COSINE)},
        )
        # Index session_id payload field for fast filtered queries
        client.create_payload_index(
            collection_name=name,
            field_name="session_id",
            field_schema=models.PayloadSchemaType.KEYWORD,
        )


def _batch(items: list, size: int) -> Iterator[list]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


def upsert_products(client: QdrantClient, products: list[Product]) -> None:
    dense_model = TextEmbedding(DENSE_MODEL)
    sparse_model = SparseTextEmbedding(SPARSE_MODEL)

    batch_size = 64
    point_id = 0

    for batch in tqdm(_batch(products, batch_size), desc="Upserting products", total=len(products) // batch_size + 1):
        texts = [_make_product_text(p) for p in batch]

        dense_vecs = list(dense_model.embed(texts))
        sparse_vecs = list(sparse_model.embed(texts))

        points = []
        for product, dense, sparse in zip(batch, dense_vecs, sparse_vecs):
            points.append(
                models.PointStruct(
                    id=point_id,
                    vector={
                        "dense": dense.tolist(),
                        "sparse": models.SparseVector(
                            indices=sparse.indices.tolist(),
                            values=sparse.values.tolist(),
                        ),
                    },
                    payload={
                        "asin": product.asin,
                        "title": product.title,
                        "description": product.description,
                        "price": product.price,
                        "category": product.category,
                        "rating": product.rating,
                    },
                )
            )
            point_id += 1

        client.upsert(collection_name=COLLECTION_PRODUCTS, points=points)


def run_ingest() -> None:
    client = get_client()
    print("Setting up Qdrant collections...")
    _setup_products_collection(client)
    _setup_memory_collections(client)

    products = load_products()
    print(f"Loaded {len(products)} products. Upserting to Qdrant...")
    upsert_products(client, products)
    print("Ingest complete.")


if __name__ == "__main__":
    run_ingest()

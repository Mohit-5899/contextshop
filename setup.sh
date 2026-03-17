#!/bin/bash
set -e

echo ""
echo "========================================"
echo "  ContextShop — Setup & Launch"
echo "========================================"
echo ""

# ── 1. Check Python ───────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
  echo "ERROR: python3 not found. Install Python 3.11+ and retry."
  exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(sys.version_info.minor)')
if [ "$PYTHON_VERSION" -lt 11 ]; then
  echo "ERROR: Python 3.11+ required (found 3.$PYTHON_VERSION)."
  exit 1
fi

# ── 2. Virtual environment ────────────────────────────────────
if [ ! -d "venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv venv
fi
source venv/bin/activate
echo "Virtual environment ready."

# ── 3. Install dependencies ───────────────────────────────────
echo ""
echo "Installing dependencies..."
pip install -r requirements.txt -q
echo "Dependencies installed."

# ── 4. Check / create .env ───────────────────────────────────
if [ ! -f ".env" ]; then
  echo ""
  echo "No .env file found. Let's set up your credentials."
  echo "(Get a free Qdrant cluster at https://cloud.qdrant.io)"
  echo "(Get a free OpenRouter key at https://openrouter.ai/keys)"
  echo ""

  read -p "QDRANT_URL: " QDRANT_URL
  read -p "QDRANT_API_KEY: " QDRANT_API_KEY
  read -p "OPENROUTER_API_KEY: " OPENROUTER_API_KEY

  cat > .env <<EOF
QDRANT_URL=$QDRANT_URL
QDRANT_API_KEY=$QDRANT_API_KEY
OPENROUTER_API_KEY=$OPENROUTER_API_KEY

COLLECTION_PRODUCTS=products
COLLECTION_EPISODIC=episodic_memory
COLLECTION_PREFERENCES=user_preferences
EOF
  echo ""
  echo ".env created."
else
  echo ".env found."
fi

# ── 5. Ingest data (skip if products.jsonl already cached) ────
echo ""
if [ -f "data/products.jsonl" ]; then
  echo "Product data already cached. Skipping ingest."
else
  echo "Generating product data and uploading to Qdrant..."
  python3 -m src.ingest
fi

# ── 6. Launch ─────────────────────────────────────────────────
echo ""
echo "========================================"
echo "  Launching ContextShop..."
echo "  Open: http://localhost:8501"
echo "========================================"
echo ""
streamlit run app.py

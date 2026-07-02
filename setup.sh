#!/usr/bin/env bash
# setup.sh — Linux/Mac setup (for standardised scoring environment)
set -e

echo ""
echo "=== Hybrid Routing Agent Setup ==="

# 1. Python venv
if [ ! -d ".venv" ]; then
  echo "[1/4] Creating virtual environment..."
  python3 -m venv .venv
fi
source .venv/bin/activate

# 2. Install deps
echo "[2/4] Installing Python dependencies..."
pip install -r requirements.txt -q

# 3. .env
if [ ! -f ".env" ]; then
  echo "[3/4] Copying .env.example → .env (edit it to set FIREWORKS_API_KEY)"
  cp .env.example .env
else
  echo "[3/4] .env already exists — skipping"
fi

# 4. Ollama
echo "[4/4] Checking Ollama..."
if command -v ollama &>/dev/null; then
  echo "  Ollama found. Pulling phi3:mini..."
  ollama pull phi3:mini
else
  echo "  WARNING: Ollama not installed. Install from https://ollama.com"
  echo "  Then run: ollama pull phi3:mini"
fi

echo ""
echo "=== Setup complete ==="
echo "Next:"
echo "  1. Edit .env — set FIREWORKS_API_KEY"
echo "  2. ollama serve   (separate terminal)"
echo "  3. python eval/eval.py --verbose"
echo "  4. python main.py \"What is the capital of France?\""

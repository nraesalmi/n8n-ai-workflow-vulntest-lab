#!/bin/bash
# ============================================
# Pull Ollama Model
# ============================================
# Usage:
#   ./scripts/pull-model.sh              # Pulls default model from .env
#   ./scripts/pull-model.sh llama3       # Pulls specific model
# ============================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Load .env if it exists
if [ -f "$PROJECT_DIR/.env" ]; then
    set -a
    source "$PROJECT_DIR/.env"
    set +a
fi

MODEL="${1:-${OLLAMA_MODEL:-mistral}}"

echo "========================================"
echo " Pulling Ollama model: $MODEL"
echo "========================================"

docker exec -it n8n-ollama ollama pull "$MODEL"

echo ""
echo "Model '$MODEL' is ready."
echo "Verify with: docker exec n8n-ollama ollama list"

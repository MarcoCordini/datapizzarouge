#!/bin/bash
set -e

echo "🔧 Avvio DataPizzaRouge API - Sviluppo"

# Directory dello script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Aggiungi ~/.local/bin al PATH per i pacchetti installati con --user
export PATH="$HOME/.local/bin:$PATH"

# Verifica environment
if [ ! -f ".env" ]; then
    echo "❌ File .env non trovato!"
    exit 1
fi

# Load environment
export $(cat .env | grep -v '^#' | xargs)

echo "✓ Avvio server in modalità sviluppo (hot-reload attivo)..."
echo "✓ API disponibile su: http://localhost:8000"
echo "✓ Docs disponibili su: http://localhost:8000/docs"
echo ""

# Avvia Uvicorn in modalità sviluppo con reload
exec uvicorn api:app \
  --host 0.0.0.0 \
  --port 8000 \
  --reload \
  --log-level debug

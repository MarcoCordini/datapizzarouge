#!/bin/bash
set -e

echo "🚀 Avvio DataPizzaRouge API - Produzione"

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

# Verifica API keys
if [ -z "$OPENAI_API_KEY" ] || [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "❌ API Keys non configurate nel file .env!"
    exit 1
fi

# Crea logs directory
mkdir -p logs

# Verifica che gunicorn sia installato
if ! command -v gunicorn &> /dev/null; then
    echo "❌ Gunicorn non trovato! Installa con: pip install gunicorn"
    exit 1
fi

echo "✓ Avvio server con Gunicorn + Uvicorn workers..."
echo "✓ Configurazione: gunicorn_config.py"
echo "✓ Log disponibili in: logs/access.log e logs/error.log"
echo ""

# Avvia Gunicorn con Uvicorn workers
exec gunicorn api:app \
  -c gunicorn_config.py \
  --log-file=-

#!/bin/bash

echo "🔧 Configurazione PATH per pacchetti Python --user"

# Controlla se ~/.local/bin è già nel PATH
if [[ ":$PATH:" == *":$HOME/.local/bin:"* ]]; then
    echo "✓ ~/.local/bin è già nel PATH"
else
    echo "➜ Aggiunta ~/.local/bin al PATH..."

    # Aggiungi a .bashrc
    if [ -f "$HOME/.bashrc" ]; then
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
        echo "✓ Aggiunto a ~/.bashrc"
    fi

    # Aggiungi a .bash_profile se esiste
    if [ -f "$HOME/.bash_profile" ]; then
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bash_profile"
        echo "✓ Aggiunto a ~/.bash_profile"
    fi

    # Aggiungi a .profile come fallback
    if [ -f "$HOME/.profile" ]; then
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.profile"
        echo "✓ Aggiunto a ~/.profile"
    fi

    echo ""
    echo "✅ PATH configurato! Esegui uno dei seguenti comandi:"
    echo "   source ~/.bashrc"
    echo "   oppure chiudi e riapri il terminale"
fi

# Verifica che gunicorn sia installato
echo ""
echo "🔍 Verifica installazioni..."
if command -v gunicorn &> /dev/null; then
    echo "✓ gunicorn trovato: $(which gunicorn)"
else
    echo "⚠️  gunicorn non trovato. Installa con:"
    echo "   pip3 install --user gunicorn"
fi

if command -v uvicorn &> /dev/null; then
    echo "✓ uvicorn trovato: $(which uvicorn)"
else
    echo "⚠️  uvicorn non trovato. Installa con:"
    echo "   pip3 install --user 'uvicorn[standard]'"
fi

if command -v python3 &> /dev/null; then
    echo "✓ python3 versione: $(python3 --version)"
else
    echo "❌ python3 non trovato!"
fi

# Guida Comandi - DataPizzaRouge

Guida pratica con tutti i comandi per usare il sistema RAG con Qdrant Cloud.

---

## Setup Iniziale (Una Volta Sola)

### 1. Configura Qdrant Cloud

Hai già creato l'account gratuito su https://cloud.qdrant.io

**Ottieni le credenziali**:
- Vai su Qdrant Cloud dashboard
- Crea un cluster (se non l'hai già fatto)
- Copia l'URL del cluster (es: `https://xyz-example.aws.qdrant.io:6333`)
- Copia l'API Key dalla sezione "API Keys"

### 2. Configura .env

Apri il file `.env` e modifica:

```bash
# === API KEYS ===
OPENAI_API_KEY=sk-proj-your-openai-key-here
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key-here

# === QDRANT CLOUD ===
QDRANT_MODE=cloud
QDRANT_URL=https://your-cluster.aws.qdrant.io:6333
QDRANT_API_KEY=your-qdrant-api-key-here

# === CRAWLER ===
MAX_PAGES=100
CONCURRENT_REQUESTS=16
DOWNLOAD_DELAY=0.5
DEPTH_LIMIT=10

# === RAG ===
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
TOP_K_RETRIEVAL=5

# === EMBEDDINGS ===
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSIONS=1536
EMBEDDING_BATCH_SIZE=100

# === LLM ===
LLM_MODEL=claude-sonnet-4-5-20250929
LLM_MAX_TOKENS=4096
LLM_TEMPERATURE=0.7

# === LOGGING ===
LOG_LEVEL=INFO
LOG_FILE=datapizzarouge.log
```

### 3. Verifica Configurazione

```bash
python cli.py setup
```

**Output atteso**:
```
✓ OpenAI API Key: Configurata
✓ Anthropic API Key: Configurata
✓ Qdrant: Connesso (cloud mode)
✓ Configurazione valida!
```

---

## Workflow Completo: Primo Crawl

### Step 1: Crawl Sito Web

```bash
python cli.py crawl https://www.tuosito.com --max-pages 50
```

**Cosa fa**:
- Crawla fino a 50 pagine del sito
- Salva HTML in `data/raw/www.tuosito.com/`
- Rispetta robots.txt
- Mostra progress bar

**Output**:
```
🕷️  Avvio crawl di: https://www.tuosito.com
📄 Pagine crawlate: 50
✓ Crawl completato!
```

**Opzioni utili**:
```bash
# Crawl più pagine
python cli.py crawl https://www.tuosito.com --max-pages 200

# Specifica directory output custom
python cli.py crawl https://www.tuosito.com --output-dir ./data/custom
```

### Step 2: Lista Domini Crawlati

```bash
python cli.py list-domains
```

**Output**:
```
Domini crawlati:
- www.tuosito.com (50 pagine, 2.3 MB)
```

### Step 3: Ingestion (Crea Vector Store)

**Prima volta - nome auto-generato**:
```bash
python cli.py ingest --domain www.tuosito.com
```

**Con nome fisso (CONSIGLIATO per aggiornamenti)**:
```bash
python cli.py ingest --domain www.tuosito.com --collection tuosito_latest
```

**Cosa fa**:
1. Legge HTML da `data/raw/`
2. Pulisce HTML → testo
3. Chunking semantico (1000 char + overlap)
4. Genera embeddings (OpenAI)
5. Carica su Qdrant Cloud

**Output**:
```
📚 Processamento dominio: www.tuosito.com
🔄 Pulizia HTML...
✂️  Chunking...
🔢 Generazione embeddings... [████████████] 100%
☁️  Caricamento su Qdrant Cloud...
✓ Collection 'tuosito_latest' creata con 234 documenti
```

**Opzioni utili**:
```bash
# Limita pagine da processare
python cli.py ingest --domain www.tuosito.com --collection tuosito_latest --max-pages 20

# Forza ricreazione (per aggiornamenti settimanali)
python cli.py ingest --domain www.tuosito.com --collection tuosito_latest --force
```

### Step 4: Verifica Collection

```bash
python cli.py list-collections
```

**Output**:
```
Collection disponibili su Qdrant Cloud:
1. tuosito_latest (234 documenti, 1536 dim)
```

**Info dettagliate**:
```bash
python cli.py stats --collection tuosito_latest
```

**Output**:
```
Collection: tuosito_latest
- Documenti: 234
- Dimensione vettori: 1536
- Status: green
```

### Step 5: Test Chat RAG

```bash
python cli.py chat --collection tuosito_latest
```

**Esempio conversazione**:
```
🤖 Chat RAG - DataPizzaRouge
Collection: tuosito_latest
Digita la tua domanda (o /quit per uscire)

Tu: Quali sono i prodotti principali?

🔍 Ricerca in corso...
📚 Trovati 5 documenti rilevanti

🤖 Assistente:
I prodotti principali sono...

[Risposta completa basata sul contenuto del sito]

📎 Fonti:
- Prodotti | https://www.tuosito.com/prodotti
- Catalogo | https://www.tuosito.com/catalogo

---
Tu: /sources

📎 Fonti ultima risposta:
1. https://www.tuosito.com/prodotti (score: 0.87)
   "Testo del chunk..."

2. https://www.tuosito.com/catalogo (score: 0.83)
   "Testo del chunk..."

---
Tu: /quit

👋 Arrivederci!
```

**Comandi nella chat**:
- `/quit` o `/exit` - Esci dalla chat
- `/clear` - Pulisci cronologia conversazione
- `/sources` - Mostra fonti dettagliate ultima risposta
- `/info` - Info sulla collection corrente

---

## Workflow Aggiornamenti Settimanali

Per siti che cambiano contenuto regolarmente (es: ogni settimana).

### Primo Setup (una volta sola)

```bash
# 1. Crawl iniziale
python cli.py crawl https://www.tuosito.com --max-pages 100

# 2. Crea collection con NOME FISSO
python cli.py ingest --domain www.tuosito.com --collection tuosito_latest
```

### Aggiornamento Settimanale (ripeti ogni settimana)

```bash
# 1. Re-crawl sito (sovrascrive dati vecchi)
python cli.py crawl https://www.tuosito.com --max-pages 100

# 2. Aggiorna collection (--force sovrascrive)
python cli.py ingest --domain www.tuosito.com --collection tuosito_latest --force
```

### Automazione con Script

**Windows (PowerShell)**:
```powershell
# Crea file: update_tuosito.ps1
$SITE_URL = "https://www.tuosito.com"
$DOMAIN = "www.tuosito.com"
$COLLECTION = "tuosito_latest"

Write-Host "=== Aggiornamento RAG - $(Get-Date) ===" -ForegroundColor Cyan

# Crawl
python cli.py crawl $SITE_URL --max-pages 100

# Ingest
python cli.py ingest --domain $DOMAIN --collection $COLLECTION --force

Write-Host "✓ Aggiornamento completato!" -ForegroundColor Green
```

**Esegui manualmente**:
```powershell
.\update_tuosito.ps1
```

**Automatizza con Task Scheduler**:
1. Apri "Task Scheduler" Windows
2. Crea nuovo task → Trigger: Settimanale (es: Domenica 3 AM)
3. Action: `powershell.exe -File "D:\path\to\update_tuosito.ps1"`

**Linux/Mac (Bash)**:
```bash
# Crea file: update_tuosito.sh
#!/bin/bash
SITE_URL="https://www.tuosito.com"
DOMAIN="www.tuosito.com"
COLLECTION="tuosito_latest"

cd /path/to/datapizzarouge
python cli.py crawl $SITE_URL --max-pages 100
python cli.py ingest --domain $DOMAIN --collection $COLLECTION --force
```

**Automatizza con cron**:
```bash
# Crontab: ogni domenica alle 3 AM
0 3 * * 0 /path/to/update_tuosito.sh
```

---

## API Server (per Blazor)

### Avvio API

**Windows**:
```bash
start_api.bat
```

**Linux/Mac**:
```bash
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

**Output**:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

### Verifica API

**Health Check**:
```bash
curl http://localhost:8000/health
```

**Output JSON**:
```json
{
  "status": "healthy",
  "qdrant_connected": true,
  "openai_configured": true,
  "anthropic_configured": true,
  "timestamp": "2026-01-05T15:30:00"
}
```

### Test API Completo

```bash
python test_api.py
```

**Output**:
```
============================================================
Test API DataPizzaRouge
============================================================
Base URL: http://localhost:8000

✓ Health Check
  Status: healthy, Qdrant: True

✓ Lista Collection
  Trovate 1 collection: ['tuosito_latest']

✓ Info Collection 'tuosito_latest'
  Points: 234, Status: green

✓ Retrieval 'tuosito_latest'
  Trovati 5 documenti

✓ Query RAG 'tuosito_latest'
  Risposta: I prodotti principali sono... | Risultati: 5

============================================================
✓ Tutti i test completati!
============================================================

API pronta per l'uso!
Documentazione: http://localhost:8000/docs
```

### Documentazione Swagger

Apri browser: **http://localhost:8000/docs**

Interfaccia interattiva per testare tutti gli endpoint.

---

## Comandi Utili

### Gestione Collection

```bash
# Lista tutte le collection
python cli.py list-collections

# Statistiche collection specifica
python cli.py stats --collection tuosito_latest

# Elimina collection (Qdrant dashboard o API)
```

### Gestione Dati Raw

```bash
# Lista domini crawlati
python cli.py list-domains

# Visualizza info dominio
# (mostra quante pagine, dimensione, data ultimo crawl)
```

### Debug e Log

```bash
# Visualizza log
cat datapizzarouge.log

# Windows
type datapizzarouge.log

# Log in real-time (Linux/Mac)
tail -f datapizzarouge.log
```

### Pulizia

```bash
# Rimuovi dati raw di un dominio
rm -rf data/raw/www.vecchiosito.com

# Windows
rmdir /s data\raw\www.vecchiosito.com
```

---

## Esempi Pratici

### Esempio 1: Sito Aziendale

```bash
# Setup iniziale
python cli.py crawl https://www.azienda.com --max-pages 50
python cli.py ingest --domain www.azienda.com --collection azienda_latest

# Chat
python cli.py chat --collection azienda_latest
> Quali sono i contatti dell'azienda?
> Descrivi i servizi offerti
```

### Esempio 2: Documentazione Tecnica

```bash
# Crawl docs (possono essere tante pagine)
python cli.py crawl https://docs.framework.io --max-pages 200

# Ingest
python cli.py ingest --domain docs.framework.io --collection framework_docs

# Chat tecnica
python cli.py chat --collection framework_docs
> Come si configura il sistema?
> Esempi di API usage
```

### Esempio 3: Blog Personale

```bash
# Crawl limitato
python cli.py crawl https://myblog.com --max-pages 30

# Ingest
python cli.py ingest --domain myblog.com --collection my_blog

# Query tematiche
python cli.py chat --collection my_blog
> Riassumi i post sul machine learning
> Quali sono i tutorial più recenti?
```

---

## Troubleshooting

### Errore: "Qdrant connection failed"

**Problema**: API Key o URL sbagliati

**Soluzione**:
```bash
# 1. Verifica .env
cat .env | grep QDRANT

# 2. Testa connessione
python cli.py setup

# 3. Verifica URL termini con porta :6333
QDRANT_URL=https://xyz.aws.qdrant.io:6333
```

### Errore: "OpenAI API Key not configured"

**Problema**: API Key mancante o invalida

**Soluzione**:
```bash
# Verifica .env
cat .env | grep OPENAI_API_KEY

# Testa key su OpenAI Platform
# https://platform.openai.com/api-keys
```

### Errore: "Collection not found"

**Problema**: Collection non esiste su Qdrant Cloud

**Soluzione**:
```bash
# 1. Lista collection disponibili
python cli.py list-collections

# 2. Se vuota, ri-fai ingestion
python cli.py ingest --domain tuodomain.com --collection nome_collection
```

### Crawl troppo lento

**Problema**: DOWNLOAD_DELAY troppo alto

**Soluzione**:
```bash
# Nel .env, riduci delay
DOWNLOAD_DELAY=0.25
CONCURRENT_REQUESTS=24
```

### API timeout

**Problema**: Query molto lunghe

**Soluzione**:
```bash
# Nel .env, aumenta token max
LLM_MAX_TOKENS=8192

# Riduci top-k per meno context
TOP_K_RETRIEVAL=3
```

---

## Parametri Ottimali

### Siti Piccoli (<100 pagine)

```bash
MAX_PAGES=100
CHUNK_SIZE=800
CHUNK_OVERLAP=150
TOP_K_RETRIEVAL=5
```

### Siti Medi (100-500 pagine)

```bash
MAX_PAGES=500
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
TOP_K_RETRIEVAL=5
```

### Siti Grandi (>500 pagine)

```bash
MAX_PAGES=1000
CHUNK_SIZE=1200
CHUNK_OVERLAP=250
TOP_K_RETRIEVAL=7
```

### Documentazione Tecnica (molto strutturata)

```bash
CHUNK_SIZE=1500
CHUNK_OVERLAP=300
TOP_K_RETRIEVAL=10
```

---

## Quick Reference

### Workflow Base

```bash
# 1. Setup (una volta)
python cli.py setup

# 2. Crawl
python cli.py crawl <URL> --max-pages <N>

# 3. Ingest
python cli.py ingest --domain <domain> --collection <nome>

# 4. Chat
python cli.py chat --collection <nome>
```

### Workflow Aggiornamenti

```bash
# Re-crawl + Re-ingest con --force
python cli.py crawl <URL>
python cli.py ingest --domain <domain> --collection <nome> --force
```

### API Workflow

```bash
# 1. Avvia API
start_api.bat  # Windows
uvicorn api:app --reload  # Linux/Mac

# 2. Test
python test_api.py

# 3. Documentazione
# http://localhost:8000/docs
```

---

## Link Utili

- **Qdrant Cloud Dashboard**: https://cloud.qdrant.io
- **OpenAI API Keys**: https://platform.openai.com/api-keys
- **Anthropic API Keys**: https://console.anthropic.com/settings/keys
- **API Docs (locale)**: http://localhost:8000/docs
- **Guida Blazor**: `README_BLAZOR.md`
- **Quick Start Blazor**: `QUICKSTART_BLAZOR.md`

---

Buon RAG! 🚀

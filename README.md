# DataPizzaRouge

Sistema RAG (Retrieval-Augmented Generation) per web crawling con integrazione Anthropic Claude e datapizza-ai.

Crawla siti web, processa contenuti e fornisce una chat interattiva intelligente basata sui contenuti crawlati.

## Caratteristiche

- **Web Crawling**: Scrapy spider per crawling completo di domini
- **Elaborazione Intelligente**: Pulizia HTML e chunking semantico
- **Vector Store**: Qdrant per storage e retrieval efficiente
- **RAG Pipeline**: Integrazione completa con OpenAI embeddings
- **Chat Interattiva**: CLI chat con Anthropic Claude
- **Configurabile**: Parametri personalizzabili via .env

## Stack Tecnologico

- **Crawler**: Scrapy
- **Embeddings**: OpenAI (text-embedding-3-small)
- **Vector Store**: Qdrant (locale o cloud)
- **LLM**: Anthropic Claude (via datapizza-ai)
- **Processing**: BeautifulSoup, custom chunker
- **CLI**: Click

## Installazione

### 1. Prerequisiti

- Python 3.13+
- Docker (per Qdrant locale)

### 2. Clona il repository

```bash
cd datapizzarouge
```

### 3. Installa dependencies

```bash
pip install -r requirements.txt
```

### 4. Configura environment

Copia `.env.example` in `.env` e configura le API keys:

```bash
cp .env.example .env
```

Modifica `.env`:

```bash
# API Keys (OBBLIGATORIE)
OPENAI_API_KEY=sk-proj-your-key-here
ANTHROPIC_API_KEY=sk-ant-your-key-here

# Altre configurazioni (opzionali, hanno default)
QDRANT_MODE=local
MAX_PAGES=1000
CHUNK_SIZE=1000
```

### 5. Avvia Qdrant (locale)

```bash
docker run -p 6333:6333 -v ./data/qdrant:/qdrant/storage qdrant/qdrant
```

Oppure usa Qdrant cloud (configura `QDRANT_URL` e `QDRANT_API_KEY` in `.env`).

### 6. Verifica configurazione

```bash
python cli.py setup
```

## Uso Rapido

### Workflow Completo

```bash
# 1. Crawl sito
python cli.py crawl https://example.com --max-pages 100

# 2. Processa e crea vector store
python cli.py ingest --domain example.com

# 3. Avvia chat interattiva
python cli.py chat --collection crawl_example_com_20260105
```

### Workflow per Aggiornamenti Periodici (Settimanali)

Per siti che cambiano contenuto regolarmente, usa una **collection con nome fisso**:

```bash
# PRIMO SETUP (una volta sola)
python cli.py crawl https://www.mysite.com
python cli.py ingest --domain www.mysite.com --collection mysite_latest

# AGGIORNAMENTO SETTIMANALE (automatizzabile)
python cli.py crawl https://www.mysite.com
python cli.py ingest --domain www.mysite.com --collection mysite_latest --force

# Chat usa sempre lo stesso nome collection
python cli.py chat --collection mysite_latest
```

**Vantaggi**:
- ✅ Nome collection fisso e prevedibile (perfetto per API)
- ✅ `--force` sovrascrive la collection esistente
- ✅ Non accumula collection vecchie
- ✅ Ideale per automazione (cron/Task Scheduler)

**Automazione Windows** (Task Scheduler):
```powershell
# update_rag.ps1
cd D:\path\to\datapizzarouge
python cli.py crawl https://www.mysite.com
python cli.py ingest --domain www.mysite.com --collection mysite_latest --force
```

**Automazione Linux** (crontab):
```bash
# Ogni domenica alle 3 AM
0 3 * * 0 cd /path/to/datapizzarouge && python cli.py crawl https://www.mysite.com && python cli.py ingest --domain www.mysite.com --collection mysite_latest --force
```

## Comandi CLI

### `crawl` - Crawla un sito web

```bash
python cli.py crawl <URL> [OPTIONS]

Opzioni:
  --max-pages, -m INTEGER  Numero massimo di pagine (default: 1000)
  --output-dir, -o PATH    Directory output (default: ./data/raw)

Esempio:
  python cli.py crawl https://docs.python.org --max-pages 50
```

### `ingest` - Processa dati crawlati

```bash
python cli.py ingest [OPTIONS]

Opzioni:
  --domain, -d TEXT        Dominio da processare
  --collection, -c TEXT    Nome collection (default: auto-generato)
  --max-pages, -m INTEGER  Max pagine da processare
  --force, -f              Forza ricreazione collection

Esempio:
  python cli.py ingest --domain docs.python.org
  python cli.py ingest  # Modalità interattiva
```

### `chat` - Chat interattiva

```bash
python cli.py chat [OPTIONS]

Opzioni:
  --collection, -c TEXT  Nome collection da usare

Esempio:
  python cli.py chat --collection crawl_python_docs_20260105
  python cli.py chat  # Modalità interattiva

Comandi nella chat:
  /quit, /exit, /q  - Esci
  /clear            - Pulisci cronologia
  /sources          - Mostra fonti ultima risposta
  /info             - Info collection
```

### `list-collections` - Lista collection

```bash
python cli.py list-collections

Mostra tutte le collection disponibili con statistiche.
```

### `stats` - Statistiche collection

```bash
python cli.py stats [OPTIONS]

Opzioni:
  --collection, -c TEXT  Nome collection

Esempio:
  python cli.py stats --collection crawl_python_docs_20260105
```

### `setup` - Verifica configurazione

```bash
python cli.py setup

Mostra configurazione corrente e verifica API keys e connessioni.
```

## Struttura del Progetto

```
datapizzarouge/
├── cli.py                     # CLI principale
├── config.py                  # Configurazione
├── requirements.txt           # Dependencies
├── .env                       # Variabili d'ambiente
│
├── crawler/                   # Scrapy crawler
│   ├── settings.py
│   ├── pipelines.py
│   └── spiders/
│       └── domain_spider.py
│
├── processors/                # Elaborazione contenuti
│   ├── html_cleaner.py       # Pulizia HTML
│   └── content_chunker.py    # Chunking semantico
│
├── storage/                   # Storage
│   ├── raw_data_store.py     # Gestione dati raw
│   └── vector_store_manager.py  # Gestione Qdrant
│
├── rag/                       # Pipeline RAG
│   ├── ingestion_pipeline.py    # Ingestion
│   ├── retrieval_pipeline.py    # Retrieval
│   └── chat_interface.py        # Chat
│
└── data/                      # Dati (gitignored)
    ├── raw/                   # Dati crawlati
    └── qdrant/                # Storage Qdrant
```

## Configurazione Avanzata

### File `.env`

Tutte le configurazioni sono in `.env`:

```bash
# === API KEYS ===
OPENAI_API_KEY=sk-proj-...
ANTHROPIC_API_KEY=sk-ant-...

# === QDRANT ===
QDRANT_MODE=local              # "local" o "cloud"
QDRANT_HOST=localhost
QDRANT_PORT=6333
# QDRANT_URL=https://...      # Solo per cloud
# QDRANT_API_KEY=...          # Solo per cloud

# === CRAWLER ===
MAX_PAGES=1000                 # Limite pagine
CONCURRENT_REQUESTS=16         # Richieste parallele
DOWNLOAD_DELAY=0.5             # Delay (secondi)
DEPTH_LIMIT=10                 # Profondità max

# === RAG ===
CHUNK_SIZE=1000                # Dimensione chunk (caratteri)
CHUNK_OVERLAP=200              # Overlap chunk
TOP_K_RETRIEVAL=5              # Top-K risultati

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

### Parametri RAG

**Chunk Size**: Dimensione ottimale dipende dal contenuto:
- **500-1000**: Buono per contenuti brevi (FAQ, articoli)
- **1000-1500**: Bilanciato per la maggior parte dei casi
- **1500-2000**: Documenti lunghi e tecnici

**Chunk Overlap**: Previene perdita di context ai confini:
- **15-20%** del chunk size è un buon default
- Aumenta per contenuti molto correlati

**Top-K Retrieval**: Numero di chunk da recuperare:
- **3-5**: Risposta veloce e focalizzata
- **5-10**: Più context, risposta completa
- **>10**: Può introdurre noise

## Esempi d'Uso

### Esempio 1: Documentazione Python

```bash
# Crawl documentazione Python
python cli.py crawl https://docs.python.org/3/ --max-pages 200

# Ingestion
python cli.py ingest --domain docs.python.org

# Chat
python cli.py chat
> Cosa sono i decorators in Python?
```

### Esempio 2: Blog Personale

```bash
# Crawl blog
python cli.py crawl https://myblog.com --max-pages 50

# Ingestion con custom collection
python cli.py ingest --domain myblog.com --collection my_blog_v1

# Chat
python cli.py chat --collection my_blog_v1
> Riassumi i post sull'intelligenza artificiale
```

### Esempio 3: Sito Aziendale

```bash
# Crawl sito aziendale
python cli.py crawl https://company.com

# Ingestion limitata
python cli.py ingest --domain company.com --max-pages 100

# Statistiche
python cli.py stats --collection crawl_company_com_20260105
```

## Troubleshooting

### Errore: "OPENAI_API_KEY non configurata"

Assicurati che `.env` esista e contenga le API keys:

```bash
cp .env.example .env
# Modifica .env con le tue keys
```

### Errore: "Connessione a Qdrant fallita"

Verifica che Qdrant sia in esecuzione:

```bash
docker ps  # Verifica container Qdrant
docker run -p 6333:6333 qdrant/qdrant  # Avvia se non running
```

### Errore: "Scrapy non trovato"

Installa dependencies:

```bash
pip install -r requirements.txt
```

### Contenuto insufficiente dopo crawling

- Verifica che il sito sia accessibile
- Alcuni siti bloccano crawler (verifica robots.txt)
- Aumenta `DOWNLOAD_DELAY` per siti con rate limiting
- Controlla log del crawler: `datapizzarouge.log`

### RAG restituisce risposte non rilevanti

Tuning parametri:

1. **Aumenta Top-K**: `TOP_K_RETRIEVAL=10`
2. **Riduci Chunk Size**: `CHUNK_SIZE=800`
3. **Aumenta Overlap**: `CHUNK_OVERLAP=250`
4. **Ricrea collection** con nuovi parametri

## Sviluppo

### Test componenti individuali

```bash
# Test HTML cleaner
python processors/html_cleaner.py

# Test content chunker
python processors/content_chunker.py

# Test vector store
python storage/vector_store_manager.py

# Test retrieval
python rag/retrieval_pipeline.py
```

### Logging

Logs salvati in `datapizzarouge.log`.

Cambia livello in `.env`:

```bash
LOG_LEVEL=DEBUG  # DEBUG, INFO, WARNING, ERROR
```

## Integrazione API REST (Blazor, React, ecc.)

DataPizzaRouge include un'**API REST FastAPI** per integrare il RAG con applicazioni web/mobile.

### Avvio API Server

```bash
# Sviluppo (con auto-reload)
uvicorn api:app --host 0.0.0.0 --port 8000 --reload

# Produzione
uvicorn api:app --host 0.0.0.0 --port 8000
```

**Documentazione automatica**: http://localhost:8000/docs

### Endpoint Principali

- **POST /api/query** - Query RAG completa (retrieval + risposta Claude)
- **POST /api/retrieval** - Solo retrieval documenti
- **GET /api/collections** - Lista collection disponibili
- **GET /api/collections/{name}** - Info collection
- **GET /health** - Health check sistema

### Integrazione Blazor

**1. Copia `RagApiClient.cs` nel tuo progetto Blazor**

**2. Registra in Program.cs:**
```csharp
builder.Services.AddHttpClient<RagApiClient>(client => {
    client.BaseAddress = new Uri("http://localhost:8000");
});
```

**3. Usa nei componenti:**
```csharp
@inject RagApiClient RagClient

private async Task AskQuestion()
{
    var response = await RagClient.QueryAsync(
        collection: "ruffino_latest",
        query: "Quali sono i prodotti?"
    );

    // response.Answer contiene la risposta
    // response.Sources contiene le fonti
}
```

**Guida completa**: Vedi `README_BLAZOR.md`

**Componente esempio**: `RagChat.razor` - Chat UI completa pronta all'uso

**Test API**: `python test_api.py`

---

## Limitazioni

- **JavaScript rendering**: Scrapy non esegue JS. Per SPA usa Playwright (non incluso)
- **Rate limiting**: Rispetta rate limits dei siti (configurabile)
- **Siti molto grandi**: Limitare con `MAX_PAGES` per evitare tempi lunghi
- **Duplicati**: Possibile presenza di contenuti duplicati (future: deduplication)

## Roadmap

- [x] **API REST FastAPI** - Completato! ✅
- [x] **Integrazione Blazor** - Client C# + componente chat ✅
- [ ] Deduplicazione automatica contenuti
- [ ] Supporto multi-dominio in singola collection
- [ ] Hybrid search (keyword + vector)
- [ ] Export/Import collection
- [ ] Incremental updates (re-crawl solo modifiche)
- [ ] Supporto Playwright per SPA
- [ ] Streaming responses API
- [ ] Rate limiting API
- [ ] Authentication/Authorization API

## Licenza

MIT

## Crediti

Powered by:
- [datapizza-ai](https://github.com/datapizza-labs/datapizza-ai) - Framework RAG
- [Scrapy](https://scrapy.org/) - Web crawling
- [Qdrant](https://qdrant.tech/) - Vector database
- [OpenAI](https://openai.com/) - Embeddings
- [Anthropic](https://anthropic.com/) - Claude LLM

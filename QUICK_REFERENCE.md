# DataPizzaRouge - Quick Reference

Riferimento rapido per comandi e API.

---

## 🚀 Setup Rapido

```bash
# Clone e setup
git clone git@github.com:MarcoCordini/datapizzarouge.git && cd datapizzarouge
pip install -r requirements.txt
cp .env.example .env && nano .env
python cli.py setup

# Workflow base
python cli.py crawl https://example.com --max-pages 50
python cli.py ingest --domain example.com
python cli.py chat
```

---

## 📟 Comandi CLI

| Comando | Descrizione | Esempio |
|---------|-------------|---------|
| `setup` | Verifica configurazione | `python cli.py setup` |
| `crawl` | Crawla sito web | `python cli.py crawl https://example.com -m 100` |
| `ingest` | Processa dati crawlati | `python cli.py ingest -d example.com -c my_docs` |
| `ingest-docs` | Processa documenti locali | `python cli.py ingest-docs --dir ./docs -c docs` |
| `chat` | Chat interattiva | `python cli.py chat -c my_docs` |
| `list-collections` | Lista collection | `python cli.py list-collections` |
| `stats` | Statistiche collection | `python cli.py stats -c my_docs` |

### Opzioni Comuni

```bash
# Crawl
--max-pages, -m      # Limite pagine (default: 100)
--output-dir, -o     # Directory output

# Ingest
--domain, -d         # Dominio da processare
--collection, -c     # Nome collection
--max-pages, -m      # Limite pagine
--force, -f          # Sovrascrive collection

# Ingest-docs
--dir, -d            # Directory documenti (required)
--collection, -c     # Nome collection (required)
--recursive          # Cerca in subdirectory (default: true)
--force, -f          # Sovrascrive collection
--extensions, -e     # Filtro estensioni (ripetibile)
```

---

## 🌐 API Endpoints

**Base URL:** `https://gemellidigitali.almapro.it/apirag`

| Method | Endpoint | Descrizione |
|--------|----------|-------------|
| GET | `/` | Info API |
| GET | `/health` | Health check |
| POST | `/api/query` | Query RAG (retrieval + Claude) |
| POST | `/api/retrieval` | Solo retrieval documenti |
| GET | `/api/collections` | Lista collection |
| GET | `/api/collections/{name}` | Info collection |
| GET | `/api/domains` | Lista domini crawlati |
| GET | `/api/domains/{domain}` | Info dominio |

### Swagger UI
📖 **Documentazione interattiva:** https://gemellidigitali.almapro.it/apirag/docs

---

## 🔧 Esempi curl

### Health Check
```bash
curl https://gemellidigitali.almapro.it/apirag/health
```

### Query RAG
```bash
curl -X POST https://gemellidigitali.almapro.it/apirag/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "collection": "my_docs",
    "query": "Come funziona?",
    "top_k": 5,
    "include_sources": true
  }'
```

### Retrieval Only
```bash
curl -X POST https://gemellidigitali.almapro.it/apirag/api/retrieval \
  -H "Content-Type: application/json" \
  -d '{
    "collection": "my_docs",
    "query": "test",
    "top_k": 5,
    "score_threshold": 0.7
  }'
```

### Lista Collection
```bash
curl https://gemellidigitali.almapro.it/apirag/api/collections
```

### Info Collection
```bash
curl https://gemellidigitali.almapro.it/apirag/api/collections/my_docs
```

---

## 💻 Blazor/C# - Quick Start

### 1. Registra HttpClient
```csharp
// Program.cs
builder.Services.AddHttpClient("RagApi", client =>
{
    client.BaseAddress = new Uri("https://gemellidigitali.almapro.it/apirag/");
    client.Timeout = TimeSpan.FromMinutes(5);
});
builder.Services.AddScoped<IRagService, RagService>();
```

### 2. Query
```csharp
var request = new QueryRequest
{
    Collection = "my_docs",
    Query = "Come funziona?",
    TopK = 5,
    IncludeSources = true
};

var response = await ragService.QueryAsync(request);
Console.WriteLine(response.Answer);
```

### 3. Retrieval
```csharp
var request = new RetrievalRequest
{
    Collection = "my_docs",
    Query = "test",
    TopK = 5,
    ScoreThreshold = 0.7
};

var results = await ragService.RetrievalAsync(request);
foreach (var r in results)
{
    Console.WriteLine($"{r.Score:F2} - {r.Url}");
}
```

---

## 🔧 Gestione Server

### Systemd Service
```bash
# Start/Stop/Restart
sudo systemctl start datapizzarouge
sudo systemctl stop datapizzarouge
sudo systemctl restart datapizzarouge

# Status
sudo systemctl status datapizzarouge

# Enable auto-start
sudo systemctl enable datapizzarouge

# Disable auto-start
sudo systemctl disable datapizzarouge
```

### Logs
```bash
# Systemd logs (real-time)
sudo journalctl -u datapizzarouge -f

# Systemd logs (ultimi 100)
sudo journalctl -u datapizzarouge -n 100

# Application logs
tail -f ~/rag_tools/datapizzarouge/logs/access.log
tail -f ~/rag_tools/datapizzarouge/logs/error.log

# Apache logs
sudo tail -f /var/log/apache2/access.log | grep apirag
sudo tail -f /var/log/apache2/error.log
```

### Aggiornamenti
```bash
cd ~/rag_tools/datapizzarouge
git pull origin main
sudo systemctl restart datapizzarouge
```

---

## 📊 Monitoring

### Check Status
```bash
# API health
curl https://gemellidigitali.almapro.it/apirag/health | jq

# Service status
sudo systemctl status datapizzarouge

# Porta in ascolto
sudo ss -tlnp | grep 8000
```

### Performance
```bash
# Worker processes
ps aux | grep gunicorn

# Memory usage
ps aux | grep gunicorn | awk '{sum+=$6} END {print sum/1024 " MB"}'

# Request rate (access log)
tail -n 1000 ~/rag_tools/datapizzarouge/logs/access.log | \
  grep "POST /api/query" | wc -l
```

---

## 🐛 Troubleshooting Veloce

| Problema | Comando Check | Soluzione |
|----------|---------------|-----------|
| API non risponde | `curl https://gemellidigitali.almapro.it/apirag/health` | `sudo systemctl restart datapizzarouge` |
| Qdrant non connesso | `python cli.py setup` | Verifica `.env` e `config.py` |
| Collection non trovata | `python cli.py list-collections` | Verifica nome collection |
| Timeout | Logs: `sudo journalctl -u datapizzarouge -n 50` | Aumenta timeout in `gunicorn_config.py` |
| 502 Bad Gateway | `sudo systemctl status datapizzarouge` | Service non attivo, riavvia |
| API key mancante | `python cli.py setup` | Aggiungi keys in `.env` |

### Quick Fixes

```bash
# Restart tutto
sudo systemctl restart datapizzarouge
sudo systemctl restart apache2

# Clear logs
> ~/rag_tools/datapizzarouge/logs/access.log
> ~/rag_tools/datapizzarouge/logs/error.log

# Test configurazione
python cli.py setup
sudo apache2ctl configtest

# Check port conflicts
sudo lsof -i :8000
```

---

## 📁 Formati Documenti Supportati

| Formato | Estensione | Note |
|---------|------------|------|
| PDF | `.pdf` | Testo + OCR immagini |
| Word | `.docx` | Testo, tabelle, immagini |
| Excel | `.xlsx`, `.xls` | Celle, formule |
| PowerPoint | `.pptx` | Slide, note |
| Immagini | `.jpg`, `.png`, `.bmp` | OCR con EasyOCR |
| Markdown | `.md` | Testo formattato |

---

## 🔐 Environment Variables

```bash
# .env file
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

QDRANT_MODE=disk                    # disk | memory | docker
QDRANT_HOST=localhost
QDRANT_PORT=6333

MAX_PAGES=100
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
TOP_K_RETRIEVAL=5

EMBEDDING_MODEL=text-embedding-3-small
LLM_MODEL=claude-sonnet-4-5-20251022
```

---

## 📞 URLs Importanti

- **API Production:** https://gemellidigitali.almapro.it/apirag
- **Swagger UI:** https://gemellidigitali.almapro.it/apirag/docs
- **Health Check:** https://gemellidigitali.almapro.it/apirag/health
- **GitHub Repo:** https://github.com/MarcoCordini/datapizzarouge

---

## 🎯 Workflow Templates

### Web Crawling
```bash
python cli.py crawl https://docs.example.com -m 200
python cli.py ingest -d docs.example.com -c docs_latest
python cli.py chat -c docs_latest
```

### Document Processing
```bash
python cli.py ingest-docs --dir ./documents -c company_kb --force
curl -X POST .../api/query -d '{"collection":"company_kb","query":"..."}'
```

### Aggiornamento Periodico
```bash
# Script bash
python cli.py crawl $URL -m 200
python cli.py ingest -d $DOMAIN -c $COLLECTION --force
```

### Crontab Example
```cron
# Aggiorna ogni lunedì alle 2 AM
0 2 * * 1 /path/to/update-script.sh >> /var/log/rag-update.log 2>&1
```

---

**Per documentazione completa, vedi:** `GUIDA_COMPLETA.md`

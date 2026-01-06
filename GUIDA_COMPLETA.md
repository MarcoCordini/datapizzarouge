# DataPizzaRouge - Guida Completa

Sistema RAG (Retrieval-Augmented Generation) per web crawling e document processing con Anthropic Claude.

## 📚 Indice

1. [Quick Start](#quick-start)
2. [Comandi CLI](#comandi-cli)
3. [API REST Endpoints](#api-rest-endpoints)
4. [Esempi Pratici](#esempi-pratici)
5. [Integrazione Blazor/C#](#integrazione-blazorc)
6. [Workflow Completi](#workflow-completi)
7. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Setup Iniziale

```bash
# 1. Clone repository
git clone git@github.com:MarcoCordini/datapizzarouge.git
cd datapizzarouge

# 2. Installa dipendenze
pip install -r requirements.txt

# 3. Configura environment
cp .env.example .env
nano .env  # Aggiungi le API keys

# 4. Verifica configurazione
python cli.py setup
```

### Workflow Base

```bash
# 1. Crawla un sito
python cli.py crawl https://example.com --max-pages 50

# 2. Processa i dati
python cli.py ingest --domain example.com

# 3. Chat interattiva
python cli.py chat --collection [nome-collection]
```

### API Server

```bash
# Sviluppo
./start_dev.sh

# Produzione
./start_production.sh

# Systemd (produzione)
sudo systemctl start datapizzarouge
```

---

## Comandi CLI

### `setup` - Verifica Configurazione

Controlla che tutto sia configurato correttamente.

```bash
python cli.py setup
```

**Output:**
- API keys (OpenAI, Anthropic)
- Connessione Qdrant
- Impostazioni chunk size, modelli, etc.
- Path directories

**Esempio output:**
```
============================================================
  CONFIGURAZIONE
============================================================

API Keys:
  OpenAI: ✓
  Anthropic: ✓

Qdrant:
  Modalità: disk
  Host: localhost:6333
  Connessione: ✓
  Collection: 3

Impostazioni:
  Max pages: 100
  Chunk size: 1000
  Chunk overlap: 200
  Top-K retrieval: 5
  Embedding model: text-embedding-3-small
  LLM model: claude-sonnet-4-5-20251022

✓ Configurazione valida!
```

---

### `crawl` - Crawla Sito Web

Scarica pagine da un sito web usando Scrapy.

**Sintassi:**
```bash
python cli.py crawl <URL> [opzioni]
```

**Opzioni:**
- `--max-pages, -m`: Numero massimo di pagine (default: 100)
- `--output-dir, -o`: Directory output (default: data/raw)

**Esempi:**

```bash
# Base
python cli.py crawl https://example.com

# Con limite pagine
python cli.py crawl https://example.com --max-pages 200

# Output custom
python cli.py crawl https://example.com -o ./my-data
```

**Output:**
- File JSON in `data/raw/[domain]/`
- Ogni file contiene: URL, titolo, contenuto, metadata

---

### `ingest` - Processa Dati Crawlati

Elabora i dati crawlati e crea vector store Qdrant.

**Sintassi:**
```bash
python cli.py ingest [opzioni]
```

**Opzioni:**
- `--domain, -d`: Dominio da processare
- `--collection, -c`: Nome collection custom
- `--max-pages, -m`: Limita numero pagine
- `--force, -f`: Sovrascrive collection esistente

**Esempi:**

```bash
# Interattivo (mostra lista domini)
python cli.py ingest

# Dominio specifico
python cli.py ingest --domain example.com

# Collection con nome fisso (per aggiornamenti periodici)
python cli.py ingest --domain example.com --collection site_latest

# Sovrascrive collection (utile per refresh settimanali)
python cli.py ingest --domain example.com --collection site_latest --force

# Limita numero pagine
python cli.py ingest --domain example.com --max-pages 50
```

**Output:**
```
============================================================
  RISULTATI
============================================================
✓ Ingestion completata!

Collection: crawl_example_com_20260106
Pagine processate: 45
Pagine fallite: 0
Chunk creati: 523
Chunk inseriti: 523

Prossimo passo:
  python cli.py chat --collection crawl_example_com_20260106
```

---

### `ingest-docs` - Processa Documenti Locali

Elabora documenti locali (PDF, Word, Excel, PowerPoint, immagini con OCR).

**Sintassi:**
```bash
python cli.py ingest-docs --dir <directory> --collection <nome> [opzioni]
```

**Opzioni:**
- `--dir, -d`: Directory con documenti (richiesto)
- `--collection, -c`: Nome collection (richiesto)
- `--recursive/--no-recursive`: Cerca in subdirectory (default: true)
- `--force, -f`: Sovrascrive collection esistente
- `--extensions, -e`: Estensioni da processare (ripetibile)

**Formati Supportati:**
- PDF (`.pdf`) - Estrazione testo e OCR per immagini
- Word (`.docx`) - Testo, tabelle, immagini
- Excel (`.xlsx`, `.xls`) - Celle, formule, grafici
- PowerPoint (`.pptx`) - Slide, note, testo
- Immagini (`.jpg`, `.png`, `.bmp`) - OCR con EasyOCR
- Markdown (`.md`) - Testo formattato

**Esempi:**

```bash
# Processa tutti i documenti in una directory
python cli.py ingest-docs --dir ./documents --collection my_docs

# Solo PDF e Word
python cli.py ingest-docs --dir ./docs --collection my_docs -e .pdf -e .docx

# Non ricorsivo (solo directory principale)
python cli.py ingest-docs --dir ./docs --collection my_docs --no-recursive

# Forza ricreazione (aggiorna documenti)
python cli.py ingest-docs --dir ./docs --collection my_docs --force

# Documenti aziendali con filtri
python cli.py ingest-docs \
  --dir /mnt/shared/documents \
  --collection company_knowledge \
  -e .pdf -e .docx -e .xlsx \
  --force
```

**Output:**
```
============================================================
  RISULTATI
============================================================
✓ Ingestion completata!

Collection: my_docs
Documenti processati: 127
Documenti falliti: 2
Chunk creati: 1843
Chunk inseriti: 1843

Prossimo passo:
  python cli.py chat --collection my_docs
```

---

### `chat` - Chat Interattiva

Avvia sessione di chat con RAG usando Claude.

**Sintassi:**
```bash
python cli.py chat [--collection <nome>]
```

**Opzioni:**
- `--collection, -c`: Collection da usare (se omesso, mostra lista)

**Esempi:**

```bash
# Interattivo (mostra lista collection)
python cli.py chat

# Collection specifica
python cli.py chat --collection crawl_example_com_20260106
```

**Comandi durante la chat:**
- Scrivi una domanda e premi Enter
- `exit` o `quit`: Esci
- `Ctrl+C`: Interrompi

**Esempio sessione:**
```
============================================================
  CHAT RAG
============================================================
Collection: crawl_example_com_20260106
Documenti disponibili: 523 chunks

Fai una domanda (o 'exit' per uscire):

> Quali sono le funzionalità principali del prodotto?

🤖 [Risposta di Claude basata sui documenti crawlati]

Fonti:
- https://example.com/features (score: 0.89)
- https://example.com/about (score: 0.85)

> exit

Arrivederci!
```

---

### `list-collections` - Lista Collection

Mostra tutte le collection Qdrant disponibili.

**Sintassi:**
```bash
python cli.py list-collections
```

**Esempio output:**
```
============================================================
  COLLECTION
============================================================

📦 crawl_example_com_20260106
   Documenti: 523
   Vector size: 1536
   Distance: Cosine

📦 company_docs
   Documenti: 1843
   Vector size: 1536
   Distance: Cosine

Totale: 2 collection
```

---

### `stats` - Statistiche Collection

Mostra statistiche dettagliate per una collection.

**Sintassi:**
```bash
python cli.py stats [--collection <nome>]
```

**Opzioni:**
- `--collection, -c`: Collection (se omesso, mostra lista)

**Esempio:**
```bash
python cli.py stats --collection crawl_example_com_20260106
```

**Output:**
```
============================================================
  STATISTICHE COLLECTION
============================================================

Nome: crawl_example_com_20260106
Documenti (points): 523
Vector size: 1536
Distance metric: Cosine
Status: green
```

---

## API REST Endpoints

**Base URL Production:** `https://gemellidigitali.almapro.it/apirag`
**Base URL Development:** `http://localhost:8000`

**Documentazione Interattiva:** `https://gemellidigitali.almapro.it/apirag/docs`

### Autenticazione

Al momento l'API non richiede autenticazione. Per ambienti production, considera di aggiungere API key o OAuth.

---

### `GET /` - Info API

Informazioni di base sull'API.

**Request:**
```bash
curl https://gemellidigitali.almapro.it/apirag/
```

**Response:**
```json
{
  "name": "DataPizzaRouge API",
  "version": "1.0.0",
  "docs": "/docs",
  "health": "/health"
}
```

---

### `GET /health` - Health Check

Verifica stato dei servizi.

**Request:**
```bash
curl https://gemellidigitali.almapro.it/apirag/health
```

**Response:**
```json
{
  "status": "healthy",
  "qdrant_connected": true,
  "openai_configured": true,
  "anthropic_configured": true,
  "timestamp": "2026-01-06T10:30:00.000Z"
}
```

**Status Codes:**
- `200 OK`: Tutto funzionante
- `503 Service Unavailable`: Problemi con Qdrant o altri servizi

---

### `POST /api/query` - Query RAG

Esegue query RAG completa: retrieval + generazione risposta con Claude.

**Request:**
```bash
curl -X POST https://gemellidigitali.almapro.it/apirag/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "collection": "crawl_example_com_20260106",
    "query": "Quali sono le funzionalità principali?",
    "top_k": 5,
    "include_sources": true,
    "include_history": false
  }'
```

**Request Body:**
```json
{
  "collection": "string",        // Nome collection (required)
  "query": "string",             // Domanda utente (required)
  "top_k": 5,                    // Numero risultati (default: 5, max: 20)
  "include_sources": true,       // Include fonti (default: true)
  "include_history": false       // Include cronologia chat (default: false)
}
```

**Response:**
```json
{
  "answer": "Le funzionalità principali includono...",
  "sources": "Fonti:\n- https://example.com/features (score: 0.89)\n- https://example.com/about (score: 0.85)",
  "num_results": 5,
  "tokens_used": 1234,
  "timestamp": "2026-01-06T10:30:00.000Z"
}
```

**Status Codes:**
- `200 OK`: Query eseguita con successo
- `404 Not Found`: Collection non trovata
- `422 Unprocessable Entity`: Parametri non validi
- `500 Internal Server Error`: Errore durante processing

---

### `POST /api/retrieval` - Solo Retrieval

Recupera documenti rilevanti senza generare risposta (utile per debug o implementazioni custom).

**Request:**
```bash
curl -X POST https://gemellidigitali.almapro.it/apirag/api/retrieval \
  -H "Content-Type: application/json" \
  -d '{
    "collection": "crawl_example_com_20260106",
    "query": "funzionalità",
    "top_k": 5,
    "score_threshold": 0.7
  }'
```

**Request Body:**
```json
{
  "collection": "string",        // Nome collection (required)
  "query": "string",             // Query di ricerca (required)
  "top_k": 5,                    // Numero risultati (default: 5, max: 20)
  "score_threshold": 0.7         // Soglia minima score (optional, 0.0-1.0)
}
```

**Response:**
```json
[
  {
    "id": "uuid-chunk-123",
    "score": 0.89,
    "text": "Le funzionalità principali del prodotto includono...",
    "url": "https://example.com/features",
    "page_title": "Funzionalità - Example",
    "chunk_index": 2
  },
  {
    "id": "uuid-chunk-456",
    "score": 0.85,
    "text": "Il nostro sistema offre...",
    "url": "https://example.com/about",
    "page_title": "Chi Siamo - Example",
    "chunk_index": 0
  }
]
```

---

### `GET /api/collections` - Lista Collection

Restituisce lista di tutte le collection disponibili.

**Request:**
```bash
curl https://gemellidigitali.almapro.it/apirag/api/collections
```

**Response:**
```json
[
  "crawl_example_com_20260106",
  "company_docs",
  "site_latest"
]
```

---

### `GET /api/collections/{collection_name}` - Info Collection

Informazioni dettagliate su una collection specifica.

**Request:**
```bash
curl https://gemellidigitali.almapro.it/apirag/api/collections/crawl_example_com_20260106
```

**Response:**
```json
{
  "name": "crawl_example_com_20260106",
  "points_count": 523,
  "vector_size": 1536,
  "distance": "Cosine",
  "status": "green"
}
```

**Status Codes:**
- `200 OK`: Collection trovata
- `404 Not Found`: Collection non esiste

---

### `GET /api/domains` - Lista Domini Crawlati

Restituisce lista di tutti i domini crawlati disponibili.

**Request:**
```bash
curl https://gemellidigitali.almapro.it/apirag/api/domains
```

**Response:**
```json
[
  "example.com",
  "mysite.it",
  "docs.company.com"
]
```

---

### `GET /api/domains/{domain}` - Info Dominio

Informazioni su un dominio crawlato specifico.

**Request:**
```bash
curl https://gemellidigitali.almapro.it/apirag/api/domains/example.com
```

**Response:**
```json
{
  "domain": "example.com",
  "page_count": 45,
  "total_size_mb": 12.5,
  "first_crawl": "2026-01-05T14:30:00",
  "last_crawl": "2026-01-06T10:00:00"
}
```

---

## Esempi Pratici

### 1. Crawl + Ingestion + Query Completo

```bash
# Step 1: Crawla sito
python cli.py crawl https://docs.python.org --max-pages 100

# Step 2: Verifica domini disponibili
python cli.py ingest
# (Seleziona "docs.python.org" dalla lista)

# Step 3: Collection con nome fisso per aggiornamenti futuri
python cli.py ingest --domain docs.python.org --collection python_docs

# Step 4: Chat interattiva
python cli.py chat --collection python_docs
```

### 2. Ingestion Documenti Aziendali

```bash
# Processa directory documenti
python cli.py ingest-docs \
  --dir /mnt/company/documents \
  --collection company_knowledge \
  -e .pdf -e .docx -e .xlsx \
  --recursive

# Usa l'API per query
curl -X POST https://gemellidigitali.almapro.it/apirag/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "collection": "company_knowledge",
    "query": "Qual è la policy sulle ferie?",
    "top_k": 3
  }'
```

### 3. Aggiornamento Settimanale Automatico

Script bash per refresh automatico:

```bash
#!/bin/bash
# update-knowledge.sh

SITE_URL="https://docs.company.com"
COLLECTION="company_docs_latest"

echo "🔄 Aggiornamento knowledge base..."

# Crawl nuovo contenuto
python cli.py crawl "$SITE_URL" --max-pages 200

# Estrai dominio
DOMAIN=$(echo "$SITE_URL" | sed -E 's|https?://([^/]+).*|\1|')

# Aggiorna collection (sovrascrive)
python cli.py ingest \
  --domain "$DOMAIN" \
  --collection "$COLLECTION" \
  --force

echo "✅ Aggiornamento completato!"
```

Aggiungi a crontab:
```bash
# Ogni lunedì alle 2:00 AM
0 2 * * 1 /path/to/update-knowledge.sh >> /var/log/rag-update.log 2>&1
```

### 4. Multi-Collection Search

Per cercare in più collection:

```bash
# Via API (ripeti per ogni collection)
for collection in "docs_v1" "docs_v2" "docs_v3"; do
  echo "Searching in $collection:"
  curl -X POST https://gemellidigitali.almapro.it/apirag/api/retrieval \
    -H "Content-Type: application/json" \
    -d "{
      \"collection\": \"$collection\",
      \"query\": \"authentication\",
      \"top_k\": 3
    }" | jq '.[] | .url'
  echo ""
done
```

### 5. Debug Retrieval Quality

Testa quality del retrieval senza LLM:

```bash
# Retrieval only con threshold
curl -X POST https://gemellidigitali.almapro.it/apirag/api/retrieval \
  -H "Content-Type: application/json" \
  -d '{
    "collection": "my_docs",
    "query": "password reset",
    "top_k": 10,
    "score_threshold": 0.75
  }' | jq '.[] | {score, url, text: .text[:100]}'
```

---

## Integrazione Blazor/C#

### Setup HttpClient

```csharp
// Program.cs o Startup.cs
builder.Services.AddHttpClient("RagApi", client =>
{
    client.BaseAddress = new Uri("https://gemellidigitali.almapro.it/apirag/");
    client.Timeout = TimeSpan.FromMinutes(5); // RAG può richiedere tempo
});
```

### Model Classes

```csharp
// Models/RagModels.cs
using System.Text.Json.Serialization;

public class QueryRequest
{
    [JsonPropertyName("collection")]
    public string Collection { get; set; }

    [JsonPropertyName("query")]
    public string Query { get; set; }

    [JsonPropertyName("top_k")]
    public int TopK { get; set; } = 5;

    [JsonPropertyName("include_sources")]
    public bool IncludeSources { get; set; } = true;

    [JsonPropertyName("include_history")]
    public bool IncludeHistory { get; set; } = false;
}

public class QueryResponse
{
    [JsonPropertyName("answer")]
    public string Answer { get; set; }

    [JsonPropertyName("sources")]
    public string? Sources { get; set; }

    [JsonPropertyName("num_results")]
    public int NumResults { get; set; }

    [JsonPropertyName("tokens_used")]
    public int? TokensUsed { get; set; }

    [JsonPropertyName("timestamp")]
    public string Timestamp { get; set; }
}

public class RetrievalRequest
{
    [JsonPropertyName("collection")]
    public string Collection { get; set; }

    [JsonPropertyName("query")]
    public string Query { get; set; }

    [JsonPropertyName("top_k")]
    public int TopK { get; set; } = 5;

    [JsonPropertyName("score_threshold")]
    public double? ScoreThreshold { get; set; }
}

public class RetrievalResult
{
    [JsonPropertyName("id")]
    public string Id { get; set; }

    [JsonPropertyName("score")]
    public double Score { get; set; }

    [JsonPropertyName("text")]
    public string Text { get; set; }

    [JsonPropertyName("url")]
    public string Url { get; set; }

    [JsonPropertyName("page_title")]
    public string PageTitle { get; set; }

    [JsonPropertyName("chunk_index")]
    public int ChunkIndex { get; set; }
}

public class HealthResponse
{
    [JsonPropertyName("status")]
    public string Status { get; set; }

    [JsonPropertyName("qdrant_connected")]
    public bool QdrantConnected { get; set; }

    [JsonPropertyName("openai_configured")]
    public bool OpenaiConfigured { get; set; }

    [JsonPropertyName("anthropic_configured")]
    public bool AnthropicConfigured { get; set; }

    [JsonPropertyName("timestamp")]
    public string Timestamp { get; set; }
}
```

### Service Layer

```csharp
// Services/RagService.cs
using System.Net.Http.Json;
using System.Text.Json;

public interface IRagService
{
    Task<QueryResponse> QueryAsync(QueryRequest request);
    Task<List<RetrievalResult>> RetrievalAsync(RetrievalRequest request);
    Task<List<string>> GetCollectionsAsync();
    Task<HealthResponse> HealthCheckAsync();
}

public class RagService : IRagService
{
    private readonly HttpClient _httpClient;
    private readonly ILogger<RagService> _logger;

    public RagService(IHttpClientFactory httpClientFactory, ILogger<RagService> logger)
    {
        _httpClient = httpClientFactory.CreateClient("RagApi");
        _logger = logger;
    }

    public async Task<QueryResponse> QueryAsync(QueryRequest request)
    {
        try
        {
            var response = await _httpClient.PostAsJsonAsync("api/query", request);
            response.EnsureSuccessStatusCode();
            return await response.Content.ReadFromJsonAsync<QueryResponse>();
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error querying RAG API");
            throw;
        }
    }

    public async Task<List<RetrievalResult>> RetrievalAsync(RetrievalRequest request)
    {
        try
        {
            var response = await _httpClient.PostAsJsonAsync("api/retrieval", request);
            response.EnsureSuccessStatusCode();
            return await response.Content.ReadFromJsonAsync<List<RetrievalResult>>();
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error retrieving documents");
            throw;
        }
    }

    public async Task<List<string>> GetCollectionsAsync()
    {
        try
        {
            return await _httpClient.GetFromJsonAsync<List<string>>("api/collections");
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error getting collections");
            throw;
        }
    }

    public async Task<HealthResponse> HealthCheckAsync()
    {
        try
        {
            return await _httpClient.GetFromJsonAsync<HealthResponse>("health");
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error checking health");
            throw;
        }
    }
}
```

### Blazor Component Example

```razor
@page "/chat"
@inject IRagService RagService

<h3>Chat RAG</h3>

<div class="chat-container">
    @if (collections == null)
    {
        <p><em>Caricamento collection...</em></p>
    }
    else
    {
        <div class="form-group">
            <label>Collection:</label>
            <select @bind="selectedCollection" class="form-control">
                <option value="">-- Seleziona --</option>
                @foreach (var coll in collections)
                {
                    <option value="@coll">@coll</option>
                }
            </select>
        </div>

        <div class="form-group">
            <label>Domanda:</label>
            <textarea @bind="userQuery" class="form-control" rows="3"
                      placeholder="Scrivi la tua domanda..."></textarea>
        </div>

        <button @onclick="SubmitQuery" class="btn btn-primary"
                disabled="@(string.IsNullOrEmpty(selectedCollection) || isLoading)">
            @if (isLoading)
            {
                <span class="spinner-border spinner-border-sm"></span>
                <span>Elaborazione...</span>
            }
            else
            {
                <span>Invia</span>
            }
        </button>

        @if (!string.IsNullOrEmpty(errorMessage))
        {
            <div class="alert alert-danger mt-3">@errorMessage</div>
        }

        @if (response != null)
        {
            <div class="response-container mt-4">
                <h4>Risposta:</h4>
                <div class="answer">@response.Answer</div>

                @if (!string.IsNullOrEmpty(response.Sources))
                {
                    <div class="sources mt-3">
                        <h5>Fonti:</h5>
                        <pre>@response.Sources</pre>
                    </div>
                }

                <div class="metadata text-muted mt-2">
                    <small>
                        Documenti trovati: @response.NumResults |
                        Token usati: @response.TokensUsed |
                        @response.Timestamp
                    </small>
                </div>
            </div>
        }
    }
</div>

@code {
    private List<string> collections;
    private string selectedCollection;
    private string userQuery;
    private QueryResponse response;
    private bool isLoading;
    private string errorMessage;

    protected override async Task OnInitializedAsync()
    {
        try
        {
            collections = await RagService.GetCollectionsAsync();
        }
        catch (Exception ex)
        {
            errorMessage = $"Errore caricamento collection: {ex.Message}";
        }
    }

    private async Task SubmitQuery()
    {
        if (string.IsNullOrEmpty(selectedCollection) || string.IsNullOrEmpty(userQuery))
            return;

        isLoading = true;
        errorMessage = null;
        response = null;

        try
        {
            var request = new QueryRequest
            {
                Collection = selectedCollection,
                Query = userQuery,
                TopK = 5,
                IncludeSources = true
            };

            response = await RagService.QueryAsync(request);
        }
        catch (Exception ex)
        {
            errorMessage = $"Errore: {ex.Message}";
        }
        finally
        {
            isLoading = false;
        }
    }
}
```

### Registra Service

```csharp
// Program.cs
builder.Services.AddScoped<IRagService, RagService>();
```

---

## Workflow Completi

### Workflow 1: Knowledge Base Aziendale

**Obiettivo:** Creare knowledge base da documentazione interna

```bash
# 1. Organizza documenti
mkdir -p /data/company-docs
# Copia PDF, Word, Excel nella directory

# 2. Ingestion
python cli.py ingest-docs \
  --dir /data/company-docs \
  --collection company_kb \
  --recursive \
  --force

# 3. Verifica
python cli.py stats --collection company_kb

# 4. Test via API
curl -X POST https://gemellidigitali.almapro.it/apirag/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "collection": "company_kb",
    "query": "Qual è la procedura per richiedere ferie?",
    "top_k": 3
  }'

# 5. Integra in Blazor
# (Usa RagService come mostrato sopra)
```

### Workflow 2: Documentazione Prodotto Multi-Versione

**Obiettivo:** Mantenere docs per versioni diverse del prodotto

```bash
# Versione 1.0
python cli.py crawl https://docs.product.com/v1.0 --max-pages 200
python cli.py ingest --domain docs.product.com --collection product_v1_0

# Versione 2.0
python cli.py crawl https://docs.product.com/v2.0 --max-pages 200
python cli.py ingest --domain docs.product.com --collection product_v2_0

# Versione 3.0 (latest)
python cli.py crawl https://docs.product.com/v3.0 --max-pages 200
python cli.py ingest --domain docs.product.com --collection product_latest

# Query specifica per versione
curl -X POST https://gemellidigitali.almapro.it/apirag/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "collection": "product_v2_0",
    "query": "Come configuro l autenticazione OAuth?",
    "top_k": 5
  }'
```

### Workflow 3: Support Chatbot

**Obiettivo:** Chatbot di supporto con RAG

```bash
# 1. Crawla FAQ e knowledge base
python cli.py crawl https://support.company.com --max-pages 500
python cli.py ingest --domain support.company.com --collection support_kb

# 2. Crea endpoint Blazor per chat
# (Vedi esempio Blazor component sopra)

# 3. Integra in widget chat sul sito
# Frontend usa l'API /api/query

# 4. Monitoring
# Controlla logs per query frequenti e qualità risposte
tail -f ~/rag_tools/datapizzarouge/logs/access.log | grep "/api/query"
```

### Workflow 4: Ricerca Semantica

**Obiettivo:** Search bar semantico su sito

```bash
# 1. Setup collection
python cli.py crawl https://mysite.com --max-pages 1000
python cli.py ingest --domain mysite.com --collection site_search

# 2. API endpoint per search
# Frontend chiama /api/retrieval per ottenere risultati rilevanti

# 3. Esempio implementazione search
curl -X POST https://gemellidigitali.almapro.it/apirag/api/retrieval \
  -H "Content-Type: application/json" \
  -d '{
    "collection": "site_search",
    "query": "pricing plans",
    "top_k": 10,
    "score_threshold": 0.7
  }' | jq '.[] | {url, title: .page_title, score}'
```

---

## Troubleshooting

### Problema: Collection non trovata

**Sintomo:**
```json
{"detail": "Collection 'my_collection' non trovata"}
```

**Soluzione:**
```bash
# Lista collection disponibili
python cli.py list-collections

# Oppure via API
curl https://gemellidigitali.almapro.it/apirag/api/collections
```

### Problema: Qdrant non connesso

**Sintomo:**
```
✗ Errore connessione Qdrant: Connection refused
```

**Soluzione:**
```bash
# Verifica che Qdrant sia in esecuzione
# Se usi Docker:
docker ps | grep qdrant

# Se usi disk mode (default):
python cli.py setup
# Controlla QDRANT_MODE in .env
```

### Problema: API Key mancante

**Sintomo:**
```
❌ API Keys non configurate!
```

**Soluzione:**
```bash
# Modifica .env
nano .env

# Aggiungi:
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Verifica
python cli.py setup
```

### Problema: Timeout su query lunghe

**Sintomo:**
```
504 Gateway Timeout
```

**Soluzione:**
```bash
# Aumenta timeout in gunicorn_config.py
timeout = 600  # 10 minuti

# E in Apache
ProxyPass /apirag http://127.0.0.1:8000 timeout=600

# Riavvia
sudo systemctl restart datapizzarouge
sudo systemctl restart apache2
```

### Problema: OCR non funziona

**Sintomo:**
```
Errore durante OCR: easyocr not found
```

**Soluzione:**
```bash
# Installa EasyOCR
pip install easyocr

# Prima esecuzione scarica modelli (richiede tempo)
# Verifica installazione
python -c "import easyocr; print('OK')"
```

### Problema: Memory error durante ingestion

**Sintomo:**
```
MemoryError: Unable to allocate array
```

**Soluzione:**
```bash
# Processa in batch più piccoli
python cli.py ingest --domain example.com --max-pages 50

# Oppure aumenta memoria worker in gunicorn_config.py
max_requests = 500  # Restart worker più frequentemente
```

### Problema: Slow retrieval

**Sintomo:** Query RAG molto lente

**Soluzione:**
```bash
# 1. Riduci top_k
curl -X POST ... -d '{"top_k": 3, ...}'  # invece di 10

# 2. Usa score_threshold per filtrare
curl -X POST ... -d '{"score_threshold": 0.75, ...}'

# 3. Ottimizza Qdrant (se usi Docker, aumenta risorse)
# 4. Considera di splittare in collection più piccole
```

### Debug Mode

```bash
# Abilita log dettagliati
export LOG_LEVEL=DEBUG

# Riavvia con logs visibili
./start_dev.sh

# Oppure
python api.py
```

### Check API Health

```bash
# Health check completo
curl https://gemellidigitali.almapro.it/apirag/health | jq

# Deve restituire:
# {
#   "status": "healthy",
#   "qdrant_connected": true,
#   "openai_configured": true,
#   "anthropic_configured": true
# }
```

---

## Quick Reference

### Comandi Comuni

```bash
# Setup
python cli.py setup

# Crawl + Ingest
python cli.py crawl https://example.com --max-pages 100
python cli.py ingest --domain example.com --collection my_docs

# Document processing
python cli.py ingest-docs --dir ./docs --collection my_docs

# Chat
python cli.py chat --collection my_docs

# Info
python cli.py list-collections
python cli.py stats --collection my_docs
```

### API Essentials

```bash
# Health
curl https://gemellidigitali.almapro.it/apirag/health

# Collections
curl https://gemellidigitali.almapro.it/apirag/api/collections

# Query
curl -X POST https://gemellidigitali.almapro.it/apirag/api/query \
  -H "Content-Type: application/json" \
  -d '{"collection":"my_docs","query":"test","top_k":5}'

# Retrieval only
curl -X POST https://gemellidigitali.almapro.it/apirag/api/retrieval \
  -H "Content-Type: application/json" \
  -d '{"collection":"my_docs","query":"test","top_k":5}'
```

### Server Management

```bash
# Start/Stop
sudo systemctl start datapizzarouge
sudo systemctl stop datapizzarouge
sudo systemctl restart datapizzarouge

# Status
sudo systemctl status datapizzarouge

# Logs
sudo journalctl -u datapizzarouge -f
tail -f ~/rag_tools/datapizzarouge/logs/access.log
```

---

## Supporto

- **Issues**: https://github.com/MarcoCordini/datapizzarouge/issues
- **Documentazione**: Vedi file nella repo
  - `README.md` - Overview
  - `DEPLOYMENT.md` - Setup produzione
  - `APACHE_CONFIG.md` - Configurazione Apache
  - `GUIDA_COMPLETA.md` - Questo documento

---

**DataPizzaRouge v1.0.0**
Sistema RAG by Almapro

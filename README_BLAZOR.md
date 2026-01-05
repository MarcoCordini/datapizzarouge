# Integrazione Blazor - DataPizzaRouge

Guida completa per integrare il sistema RAG con un'applicazione Blazor.

## Architettura

```
┌─────────────────┐
│  Blazor App     │
│  (Frontend C#)  │
└────────┬────────┘
         │ HTTP/REST
         ↓
┌─────────────────┐
│  FastAPI        │
│  (Python)       │
└────────┬────────┘
         │
    ┌────┴────┬────────┐
    ↓         ↓        ↓
┌────────┐ ┌──────┐ ┌────────┐
│ Qdrant │ │OpenAI│ │Anthropic│
└────────┘ └──────┘ └────────┘
```

---

## Setup Completo

### Parte 1: Avvio API Python

#### 1.1 Installa dependencies (se non già fatto)

```bash
cd D:\Almapro-tfs\Febo-Gemelli\datapizzarouge
pip install -r requirements.txt
```

#### 1.2 Verifica configurazione

```bash
python cli.py setup
```

Assicurati che:
- ✅ OpenAI API Key configurata
- ✅ Anthropic API Key configurata
- ✅ Qdrant connesso (localhost:6333 o cloud)
- ✅ Almeno una collection disponibile

#### 1.3 Avvia Qdrant (se locale)

```bash
docker run -p 6333:6333 -v ./data/qdrant:/qdrant/storage qdrant/qdrant
```

#### 1.4 Avvia API Server

```bash
# Sviluppo (con auto-reload)
uvicorn api:app --host 0.0.0.0 --port 8000 --reload

# Produzione
uvicorn api:app --host 0.0.0.0 --port 8000
```

L'API sarà disponibile su:
- **API Base**: http://localhost:8000
- **Documentazione Swagger**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

---

### Parte 2: Setup Progetto Blazor

#### 2.1 Crea nuovo progetto Blazor (o usa esistente)

**Blazor Server**:
```bash
dotnet new blazorserver -n MyBlazorApp
cd MyBlazorApp
```

**Blazor WebAssembly**:
```bash
dotnet new blazorwasm -n MyBlazorApp
cd MyBlazorApp
```

#### 2.2 Copia Client C#

Copia `RagApiClient.cs` nel tuo progetto Blazor:

```
MyBlazorApp/
├── Services/
│   └── RagApiClient.cs   ← Copia qui
```

Assicurati che il namespace sia corretto:
```csharp
namespace MyBlazorApp.Services  // Cambia se necessario
{
    // ...
}
```

#### 2.3 Registra HttpClient in Program.cs

```csharp
// Program.cs
using MyBlazorApp.Services;

var builder = WebApplication.CreateBuilder(args);

// ... altri servizi ...

// Registra RagApiClient
builder.Services.AddHttpClient<RagApiClient>(client =>
{
    client.BaseAddress = new Uri("http://localhost:8000");
    client.Timeout = TimeSpan.FromMinutes(2); // Query possono richiedere tempo
});

var app = builder.Build();
// ...
```

#### 2.4 (Opzionale) Copia Componente Chat

Copia `RagChat.razor` in:

```
MyBlazorApp/
├── Pages/          ← Blazor Server
│   └── RagChat.razor
└── Components/     ← Blazor WebAssembly
    └── Pages/
        └── RagChat.razor
```

Aggiusta il namespace se necessario:
```razor
@using MyBlazorApp.Services
```

#### 2.5 Aggiungi al Menu di Navigazione

In `NavMenu.razor` (o equivalente):

```razor
<div class="nav-item px-3">
    <NavLink class="nav-link" href="rag-chat">
        <span class="bi bi-chat-dots" aria-hidden="true"></span> RAG Chat
    </NavLink>
</div>
```

---

## Uso del Client

### Esempio Base: Query Semplice

```csharp
@page "/simple-query"
@inject RagApiClient RagClient

<h3>Query Semplice</h3>

<input @bind="question" placeholder="Fai una domanda..." />
<button @onclick="Ask">Chiedi</button>

@if (!string.IsNullOrEmpty(answer))
{
    <div class="alert alert-info">
        <strong>Risposta:</strong>
        <p>@answer</p>
    </div>
}

@code {
    private string question = "";
    private string answer = "";

    private async Task Ask()
    {
        try
        {
            var response = await RagClient.QueryAsync(
                collection: "ruffino_latest",  // Nome collection
                query: question
            );

            answer = response.Answer;
        }
        catch (Exception ex)
        {
            answer = $"Errore: {ex.Message}";
        }
    }
}
```

### Esempio Avanzato: Con Fonti e Controllo

```csharp
@page "/advanced-query"
@inject RagApiClient RagClient

<h3>Query Avanzata</h3>

<div class="mb-3">
    <label>Collection:</label>
    <select @bind="selectedCollection">
        @foreach (var coll in collections)
        {
            <option value="@coll">@coll</option>
        }
    </select>
</div>

<div class="mb-3">
    <label>Domanda:</label>
    <textarea @bind="question" rows="3" class="form-control"></textarea>
</div>

<div class="mb-3">
    <label>Top-K:</label>
    <input type="number" @bind="topK" min="1" max="20" />
</div>

<button @onclick="Ask" disabled="@isLoading">
    @(isLoading ? "Caricamento..." : "Chiedi")
</button>

@if (response != null)
{
    <div class="card mt-3">
        <div class="card-header">Risposta</div>
        <div class="card-body">
            @((MarkupString)response.Answer.Replace("\n", "<br />"))
        </div>
        <div class="card-footer text-muted">
            Documenti: @response.NumResults |
            Token: @response.TokensUsed
        </div>
    </div>

    @if (!string.IsNullOrEmpty(response.Sources))
    {
        <div class="card mt-2">
            <div class="card-header">Fonti</div>
            <div class="card-body">
                @((MarkupString)response.Sources.Replace("\n", "<br />"))
            </div>
        </div>
    }
}

@code {
    private List<string> collections = new();
    private string selectedCollection = "";
    private string question = "";
    private int topK = 5;
    private bool isLoading = false;
    private QueryResponse? response;

    protected override async Task OnInitializedAsync()
    {
        collections = await RagClient.GetCollectionsAsync();
        if (collections.Any())
            selectedCollection = collections[0];
    }

    private async Task Ask()
    {
        try
        {
            isLoading = true;
            response = await RagClient.QueryAsync(
                collection: selectedCollection,
                query: question,
                topK: topK,
                includeSources: true
            );
        }
        catch (Exception ex)
        {
            // Handle error
        }
        finally
        {
            isLoading = false;
        }
    }
}
```

### Esempio: Solo Retrieval (Senza Generazione)

```csharp
private async Task SearchDocuments()
{
    var results = await RagClient.RetrievalAsync(
        collection: "ruffino_latest",
        query: "ricetta pizza",
        topK: 10,
        scoreThreshold: 0.7f
    );

    foreach (var result in results)
    {
        Console.WriteLine($"Score: {result.Score}");
        Console.WriteLine($"URL: {result.Url}");
        Console.WriteLine($"Text: {result.Text}");
    }
}
```

### Esempio: Gestione Collection

```csharp
// Lista collection
var collections = await RagClient.GetCollectionsAsync();

// Info su collection specifica
var info = await RagClient.GetCollectionInfoAsync("ruffino_latest");
Console.WriteLine($"Documenti: {info.PointsCount}");

// Lista domini crawlati
var domains = await RagClient.GetDomainsAsync();

// Info dominio
var domainInfo = await RagClient.GetDomainInfoAsync("www.ruffino.it");
Console.WriteLine($"Pagine crawlate: {domainInfo.PageCount}");
```

---

## API Endpoints Disponibili

### POST /api/query
Query RAG completa (retrieval + generazione risposta)

**Request:**
```json
{
  "collection": "ruffino_latest",
  "query": "Quali sono i prodotti principali?",
  "top_k": 5,
  "include_sources": true,
  "include_history": false
}
```

**Response:**
```json
{
  "answer": "I prodotti principali sono...",
  "sources": "- Prodotti\n  https://...",
  "num_results": 5,
  "tokens_used": 1234,
  "timestamp": "2026-01-05T15:30:00"
}
```

### POST /api/retrieval
Solo retrieval documenti (no generazione)

**Request:**
```json
{
  "collection": "ruffino_latest",
  "query": "prodotti",
  "top_k": 10,
  "score_threshold": 0.5
}
```

**Response:**
```json
[
  {
    "id": 123,
    "score": 0.85,
    "text": "Testo del documento...",
    "url": "https://...",
    "page_title": "Titolo",
    "chunk_index": 0
  }
]
```

### GET /api/collections
Lista tutte le collection

**Response:**
```json
["ruffino_latest", "other_site_v1"]
```

### GET /api/collections/{name}
Info su collection specifica

**Response:**
```json
{
  "name": "ruffino_latest",
  "points_count": 1234,
  "vector_size": 1536,
  "distance": "Cosine",
  "status": "green"
}
```

### GET /health
Health check sistema

**Response:**
```json
{
  "status": "healthy",
  "qdrant_connected": true,
  "openai_configured": true,
  "anthropic_configured": true,
  "timestamp": "2026-01-05T15:30:00"
}
```

---

## Deploy in Produzione

### Opzione 1: Server Separati

**Backend Python (API)**:
- Deploy su Azure App Service (Python)
- O AWS Elastic Beanstalk
- O Docker container (Docker Compose)

**Frontend Blazor**:
- Deploy su Azure App Service (.NET)
- O IIS su Windows Server

**Configurazione**:
```csharp
// appsettings.Production.json
{
  "RagApi": {
    "BaseUrl": "https://api.tuosito.com"
  }
}

// Program.cs
var ragApiUrl = builder.Configuration["RagApi:BaseUrl"];
builder.Services.AddHttpClient<RagApiClient>(client =>
{
    client.BaseAddress = new Uri(ragApiUrl);
});
```

### Opzione 2: Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  qdrant:
    image: qdrant/qdrant
    ports:
      - "6333:6333"
    volumes:
      - ./data/qdrant:/qdrant/storage

  rag-api:
    build: ./datapizzarouge
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - QDRANT_HOST=qdrant
    depends_on:
      - qdrant

  blazor-app:
    build: ./MyBlazorApp
    ports:
      - "80:80"
    environment:
      - RAG_API_URL=http://rag-api:8000
    depends_on:
      - rag-api
```

### Opzione 3: Stesso Server (Sviluppo)

1. Avvia API Python: `uvicorn api:app --port 8000`
2. Avvia Blazor: `dotnet run --urls http://localhost:5000`
3. Blazor chiama `http://localhost:8000`

---

## Sicurezza

### CORS

In produzione, limita CORS ai tuoi domini:

```python
# api.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://tuoblazorapp.com",
        "https://www.tuoblazorapp.com"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

### Authentication

Aggiungi JWT o API Key:

```python
# api.py
from fastapi import Security, HTTPException
from fastapi.security import HTTPBearer

security = HTTPBearer()

@app.post("/api/query")
async def query_rag(
    request: QueryRequest,
    credentials = Security(security)
):
    # Verifica token
    token = credentials.credentials
    if not verify_token(token):
        raise HTTPException(status_code=401)

    # ... resto del codice
```

```csharp
// Blazor
builder.Services.AddHttpClient<RagApiClient>(client =>
{
    client.BaseAddress = new Uri("http://localhost:8000");
    client.DefaultRequestHeaders.Authorization =
        new AuthenticationHeaderValue("Bearer", "your-api-key");
});
```

---

## Troubleshooting

### API non raggiungibile
```
Errore: Failed to fetch
```

**Soluzione:**
1. Verifica API sia avviata: `curl http://localhost:8000/health`
2. Controlla firewall
3. Verifica CORS settings

### Timeout su query lunghe
```
Errore: The operation was canceled
```

**Soluzione:**
```csharp
builder.Services.AddHttpClient<RagApiClient>(client =>
{
    client.Timeout = TimeSpan.FromMinutes(5); // Aumenta timeout
});
```

### Errore 404 su collection
```
Collection 'xxx' non trovata
```

**Soluzione:**
1. Verifica collection esista: `python cli.py list-collections`
2. Usa nome esatto (case-sensitive)
3. Assicurati Qdrant sia connesso

---

## Performance Tips

1. **Cache API Responses** (per collection list, ecc.)
2. **Streaming Responses** per risposte lunghe
3. **Pagination** per retrieval con molti risultati
4. **Connection Pooling** già gestito da HttpClient
5. **Rate Limiting** se API è pubblica

---

## Esempi Completi

Vedi:
- `RagChat.razor` - Componente chat completo
- `RagApiClient.cs` - Client C# completo
- `api.py` - API FastAPI completa

---

## Supporto

Per problemi:
1. Controlla log API: `datapizzarouge.log`
2. Testa endpoint: http://localhost:8000/docs
3. Verifica health: http://localhost:8000/health

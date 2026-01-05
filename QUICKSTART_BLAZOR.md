# Quick Start - Blazor Integration

Inizia a usare DataPizzaRouge RAG nel tuo progetto Blazor in **5 minuti**.

## Prerequisiti

✅ Python 3.13+ installato
✅ .NET 8+ installato
✅ Docker (per Qdrant) o Qdrant Cloud

---

## Parte 1: Setup Backend (2 minuti)

### 1. Avvia Qdrant

```bash
docker run -p 6333:6333 -v ./data/qdrant:/qdrant/storage qdrant/qdrant
```

### 2. Configura API Keys

Copia `.env.example` in `.env` e aggiungi le tue chiavi:

```bash
OPENAI_API_KEY=sk-proj-your-key-here
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

### 3. Crea una collection

```bash
# Crawl sito (esempio)
python cli.py crawl https://www.tuosito.com --max-pages 50

# Crea collection con nome fisso
python cli.py ingest --domain www.tuosito.com --collection tuosito_latest
```

### 4. Avvia API

**Windows**:
```bash
start_api.bat
```

**Linux/Mac**:
```bash
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

✅ API pronta su http://localhost:8000/docs

---

## Parte 2: Setup Blazor (3 minuti)

### 1. Copia Client nel tuo progetto

```bash
# Copia RagApiClient.cs nella tua app Blazor
cp RagApiClient.cs /path/to/YourBlazorApp/Services/
```

### 2. Registra HttpClient

In `Program.cs`:

```csharp
using YourBlazorApp.Services;

var builder = WebApplication.CreateBuilder(args);

// ... altri servizi ...

// Registra RAG API Client
builder.Services.AddHttpClient<RagApiClient>(client =>
{
    client.BaseAddress = new Uri("http://localhost:8000");
    client.Timeout = TimeSpan.FromMinutes(2);
});

var app = builder.Build();
```

### 3. Usa nei componenti

**Esempio minimo** (`Pages/RagDemo.razor`):

```razor
@page "/rag-demo"
@inject RagApiClient RagClient

<h3>RAG Demo</h3>

<input @bind="question" placeholder="Fai una domanda..." />
<button @onclick="Ask">Chiedi</button>

@if (!string.IsNullOrEmpty(answer))
{
    <div class="alert alert-info mt-3">
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
                collection: "tuosito_latest",  // ← Nome tua collection
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

### 4. (Opzionale) Usa componente completo

Per una chat UI completa pronta all'uso:

```bash
# Copia componente chat
cp RagChat.razor /path/to/YourBlazorApp/Pages/
```

Aggiungi al menu di navigazione (`NavMenu.razor`):

```razor
<div class="nav-item px-3">
    <NavLink class="nav-link" href="rag-chat">
        <span class="bi bi-chat-dots"></span> RAG Chat
    </NavLink>
</div>
```

---

## Test

### Test Backend

```bash
# Test API
python test_api.py

# O manualmente
curl http://localhost:8000/health
```

### Test Frontend

1. Avvia Blazor: `dotnet run`
2. Vai a `/rag-demo` o `/rag-chat`
3. Fai una domanda

---

## Workflow Completo

```
1. Crawl sito → 2. Ingest (collection fissa) → 3. API sempre attiva
                                                           ↓
                                           4. Blazor chiama API
                                                           ↓
                                           5. User fa domanda
                                                           ↓
                                           6. Risposta con RAG
```

---

## Aggiornamento Settimanale

### Setup automatico (Windows)

```powershell
# Modifica update_rag.ps1 con i tuoi parametri
$SITE_URL = "https://www.tuosito.com"
$COLLECTION_NAME = "tuosito_latest"

# Esegui manualmente o automatizza con Task Scheduler
.\update_rag.ps1
```

### Setup automatico (Linux)

```bash
# Crontab: ogni domenica alle 3 AM
0 3 * * 0 /path/to/datapizzarouge/update_rag.sh
```

---

## File Struttura

```
datapizzarouge/              ← Backend Python
├── api.py                   ← Server FastAPI
├── cli.py                   ← CLI tool
├── start_api.bat            ← Avvio rapido (Windows)
├── update_rag.ps1           ← Script aggiornamento
├── RagApiClient.cs          ← Client C# per Blazor
├── RagChat.razor            ← Componente chat completo
└── README_BLAZOR.md         ← Guida completa

YourBlazorApp/               ← Frontend Blazor
├── Program.cs               ← Registra HttpClient
├── Services/
│   └── RagApiClient.cs      ← Copia qui
└── Pages/
    ├── RagDemo.razor        ← Tuo componente custom
    └── RagChat.razor        ← (Opzionale) Chat completa
```

---

## Endpoint API Essenziali

### Query RAG (quello che usi di più)

```http
POST /api/query
Content-Type: application/json

{
  "collection": "tuosito_latest",
  "query": "Quali sono i prodotti?",
  "top_k": 5,
  "include_sources": true
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

### Lista Collection

```http
GET /api/collections
```

**Response:**
```json
["tuosito_latest", "altro_sito"]
```

### Health Check

```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "qdrant_connected": true,
  "openai_configured": true,
  "anthropic_configured": true
}
```

---

## Troubleshooting

### "Connection refused" su API

```bash
# Verifica API sia avviata
curl http://localhost:8000/health

# Se non risponde, avvia API
uvicorn api:app --reload
```

### "Collection not found"

```bash
# Verifica collection esistano
python cli.py list-collections

# Se vuota, crea collection
python cli.py ingest --domain tuosito.com --collection tuosito_latest
```

### Timeout su query lunghe

```csharp
// Aumenta timeout in Program.cs
builder.Services.AddHttpClient<RagApiClient>(client =>
{
    client.Timeout = TimeSpan.FromMinutes(5); // ← Aumenta
});
```

---

## Prossimi Passi

1. ✅ **Funziona?** Vai su http://localhost:8000/docs e prova l'API
2. 📚 **Approfondisci**: Leggi `README_BLAZOR.md` per dettagli completi
3. 🔄 **Automatizza**: Configura `update_rag.ps1` per aggiornamenti settimanali
4. 🎨 **Personalizza**: Modifica `RagChat.razor` con il tuo stile
5. 🚀 **Deploy**: Vedi `README_BLAZOR.md` sezione "Deploy in Produzione"

---

## Supporto

- **Documentazione API**: http://localhost:8000/docs
- **Guide complete**: `README_BLAZOR.md`, `README_AUTOMATION.md`
- **Test**: `python test_api.py`

Buon coding! 🚀

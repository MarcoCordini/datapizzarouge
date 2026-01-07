# Implementazione API FastAPI per Blazor

Documentazione completa per implementare layer API REST che permetta a Blazor di interagire con DataPizzaRouge.

## 📋 Indice

1. [Panoramica Architettura](#panoramica-architettura)
2. [Database MySQL](#database-mysql)
3. [API Endpoints](#api-endpoints)
4. [Implementazione Backend](#implementazione-backend)
5. [Integrazione Blazor](#integrazione-blazor)
6. [Deployment](#deployment)
7. [Sicurezza](#sicurezza)
8. [Testing](#testing)

---

## 🏗️ Panoramica Architettura

### Stack Tecnologico

```
┌─────────────────────────────────────────┐
│         Blazor Frontend (C#)            │
│   - UI per utenti non tecnici           │
│   - Dashboard e monitoraggio            │
│   - Upload documenti                    │
└─────────────┬───────────────────────────┘
              │ HTTP REST API
              │ (JSON)
┌─────────────▼───────────────────────────┐
│         FastAPI Backend (Python)        │
│   - Gestione job async                  │
│   - Wrapper per CLI esistente           │
│   - WebSocket per log realtime          │
└─────────────┬───────────────────────────┘
              │
      ┌───────┴────────┐
      │                │
┌─────▼─────┐   ┌──────▼──────┐
│   MySQL   │   │  Python CLI │
│  (Jobs)   │   │  (esistente)│
└───────────┘   └──────┬───────┘
                       │
                ┌──────┴───────┐
                │              │
         ┌──────▼─────┐  ┌─────▼─────┐
         │   Qdrant   │  │   Data/   │
         │  (Vector)  │  │ Documents │
         └────────────┘  └───────────┘
```

### Principi di Design

1. **CLI Indipendente**: La CLI esistente continua a funzionare senza API
2. **Zero Breaking Changes**: Nessuna modifica al codice esistente
3. **API come Wrapper**: FastAPI chiama subprocess della CLI
4. **MySQL per Tracking**: Job tracking e management in MySQL
5. **WebSocket per Logs**: Stream realtime dei log ai client

---

## 🗄️ Database MySQL

### Setup Database

```sql
-- Creazione database
CREATE DATABASE datapizzarouge
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE datapizzarouge;
```

### Schema Completo

#### Tabella: jobs

```sql
CREATE TABLE jobs (
    -- Identificazione
    id VARCHAR(36) PRIMARY KEY,  -- UUID
    type ENUM('crawl', 'ingest', 'multi_crawl', 'query') NOT NULL,
    status ENUM('queued', 'running', 'completed', 'failed', 'cancelled') DEFAULT 'queued',

    -- Utente
    user_id VARCHAR(100),

    -- Dati job (JSON)
    parameters JSON NOT NULL COMMENT 'Parametri input job',
    progress JSON COMMENT 'Stato avanzamento corrente',
    results JSON COMMENT 'Risultati finali job',

    -- Timing
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    started_at DATETIME,
    completed_at DATETIME,

    -- Error handling
    error_message TEXT,
    error_stacktrace TEXT,

    -- Management
    priority INT DEFAULT 0 COMMENT 'Priorità esecuzione (più alto = prima)',
    retry_count INT DEFAULT 0 COMMENT 'Numero retry effettuati',
    max_retries INT DEFAULT 3 COMMENT 'Max retry consentiti',
    parent_job_id VARCHAR(36) COMMENT 'Job parent per job compositi',

    -- Indices
    INDEX idx_status (status),
    INDEX idx_user (user_id),
    INDEX idx_created (created_at),
    INDEX idx_type (type),
    INDEX idx_priority (priority DESC, created_at ASC),

    FOREIGN KEY (parent_job_id) REFERENCES jobs(id) ON DELETE SET NULL
) ENGINE=InnoDB;
```

#### Tabella: job_logs

```sql
CREATE TABLE job_logs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    job_id VARCHAR(36) NOT NULL,
    timestamp DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3),  -- Milliseconds precision
    level ENUM('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL') DEFAULT 'INFO',
    message TEXT NOT NULL,
    details JSON COMMENT 'Dati aggiuntivi strutturati',
    source VARCHAR(100) COMMENT 'Modulo/funzione sorgente log',

    INDEX idx_job_id (job_id),
    INDEX idx_timestamp (timestamp),
    INDEX idx_level (level),

    FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
) ENGINE=InnoDB;
```

#### Tabella: collections

```sql
CREATE TABLE collections (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,

    -- Ownership
    created_by VARCHAR(100),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- Statistiche
    total_chunks INT DEFAULT 0,
    total_documents INT DEFAULT 0,
    total_size_bytes BIGINT DEFAULT 0,

    -- Metadata JSON
    metadata JSON COMMENT 'Configurazioni, tags, etc',

    -- Qdrant sync
    qdrant_collection_name VARCHAR(255) COMMENT 'Nome in Qdrant se diverso',
    is_synced BOOLEAN DEFAULT TRUE,
    last_sync_at DATETIME,

    INDEX idx_name (name),
    INDEX idx_created_by (created_by),
    INDEX idx_updated (updated_at)
) ENGINE=InnoDB;
```

#### Tabella: documents

```sql
CREATE TABLE documents (
    id INT AUTO_INCREMENT PRIMARY KEY,
    collection_name VARCHAR(255) NOT NULL,

    -- File info
    file_name VARCHAR(500) NOT NULL,
    file_path TEXT,
    file_hash VARCHAR(64) COMMENT 'SHA256 per deduplicazione',
    file_type VARCHAR(50),
    file_size_kb DECIMAL(10, 2),

    -- Source info
    source_url TEXT COMMENT 'URL originale se da crawl',
    domain VARCHAR(255) COMMENT 'Dominio di provenienza',
    crawled_at DATETIME,
    processed_at DATETIME,

    -- Content stats
    pages_count INT,
    chunks_count INT,
    word_count INT,

    -- Processing flags
    is_ocr BOOLEAN DEFAULT FALSE,
    extraction_method VARCHAR(50) COMMENT 'native_text, easyocr, etc',

    -- Metadata JSON
    metadata JSON,

    INDEX idx_collection (collection_name),
    INDEX idx_hash (file_hash),
    INDEX idx_type (file_type),
    INDEX idx_domain (domain),

    FOREIGN KEY (collection_name) REFERENCES collections(name) ON DELETE CASCADE
) ENGINE=InnoDB;
```

#### Tabella: users (opzionale)

```sql
CREATE TABLE users (
    id VARCHAR(100) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    role ENUM('admin', 'user', 'viewer') DEFAULT 'user',

    -- Quota management
    max_collections INT DEFAULT 10,
    max_crawl_pages INT DEFAULT 1000,
    max_storage_mb INT DEFAULT 10000,

    -- API access
    api_key VARCHAR(255) UNIQUE,
    api_key_created_at DATETIME,

    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login DATETIME,

    INDEX idx_email (email),
    INDEX idx_api_key (api_key),
    INDEX idx_active (is_active)
) ENGINE=InnoDB;
```

#### Tabella: job_queue

```sql
CREATE TABLE job_queue (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    job_id VARCHAR(36) UNIQUE NOT NULL,
    priority INT DEFAULT 0,
    queued_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    assigned_worker VARCHAR(100) COMMENT 'ID worker che sta processando',
    assigned_at DATETIME,

    INDEX idx_priority (priority DESC, queued_at ASC),
    INDEX idx_assigned (assigned_worker),
    INDEX idx_queued (queued_at),

    FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
) ENGINE=InnoDB;
```

---

## 📡 API Endpoints

### 1. Crawl Endpoints

#### POST /api/crawl/start

Avvia crawl di un singolo sito.

**Request:**
```json
{
  "url": "https://www.example.com/",
  "max_pages": 100,
  "collection_name": "example_docs",
  "options": {
    "auto_ingest": true,
    "process_documents": true,
    "recursive": true
  },
  "user_id": "user@example.com"
}
```

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "message": "Crawl job created for www.example.com",
  "estimated_duration_minutes": 5,
  "created_at": "2026-01-07T16:30:00Z"
}
```

**Status Codes:**
- `201`: Job creato con successo
- `400`: Parametri non validi
- `401`: Non autenticato
- `429`: Rate limit superato

---

#### POST /api/crawl/multi-site

Crawl multipli siti in una collection unificata.

**Request:**
```json
{
  "collection_name": "enti_pubblici",
  "sites": [
    {
      "url": "https://www.aranagenzia.it/",
      "max_pages": 200
    },
    {
      "url": "https://www.governo.it/",
      "max_pages": 50
    }
  ],
  "max_pages_per_site": 100,
  "auto_ingest": true,
  "user_id": "user@example.com"
}
```

**Response:**
```json
{
  "job_id": "650e8400-e29b-41d4-a716-446655440001",
  "status": "queued",
  "sites_count": 2,
  "message": "Multi-site crawl job created",
  "child_jobs": [
    "750e8400-e29b-41d4-a716-446655440002",
    "750e8400-e29b-41d4-a716-446655440003"
  ]
}
```

---

### 2. Ingestion Endpoints

#### POST /api/ingest/documents

Ingestion documenti da cartella locale o path remoto.

**Request:**
```json
{
  "documents_path": "C:\\Users\\Documents\\Contratti",
  "collection_name": "contratti_2024",
  "recursive": true,
  "extensions": [".pdf", ".docx", ".xlsx"],
  "ocr_enabled": true,
  "force_recreate": false,
  "user_id": "user@example.com"
}
```

**Response:**
```json
{
  "job_id": "850e8400-e29b-41d4-a716-446655440004",
  "status": "queued",
  "message": "Document ingestion job created",
  "documents_found": 45,
  "estimated_duration_minutes": 15
}
```

---

#### POST /api/ingest/domain

Ingestion HTML da dominio già crawlato.

**Request:**
```json
{
  "domain": "www.aranagenzia.it",
  "collection_name": "aran_docs",
  "max_pages": 500,
  "force_recreate": false,
  "user_id": "user@example.com"
}
```

**Response:**
```json
{
  "job_id": "950e8400-e29b-41d4-a716-446655440005",
  "status": "queued",
  "message": "HTML ingestion job created for www.aranagenzia.it",
  "pages_found": 1245
}
```

---

### 3. Job Management Endpoints

#### GET /api/jobs/{job_id}

Ottieni status di un job specifico.

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "type": "crawl",
  "status": "running",
  "progress": {
    "phase": "crawling",
    "current_page": 45,
    "total_pages": 100,
    "percentage": 45,
    "documents_found": 12,
    "current_url": "https://www.example.com/page45"
  },
  "created_at": "2026-01-07T16:30:00Z",
  "started_at": "2026-01-07T16:30:15Z",
  "estimated_completion": "2026-01-07T16:35:00Z",
  "elapsed_seconds": 120
}
```

---

#### GET /api/jobs

Lista job con filtri.

**Query Parameters:**
- `user_id`: Filtra per utente
- `status`: Filtra per status (queued, running, completed, failed)
- `type`: Filtra per tipo (crawl, ingest, etc)
- `limit`: Numero massimo risultati (default: 50)
- `offset`: Paginazione

**Response:**
```json
{
  "total": 150,
  "limit": 50,
  "offset": 0,
  "jobs": [
    {
      "job_id": "...",
      "type": "crawl",
      "status": "completed",
      "created_at": "2026-01-07T16:00:00Z",
      "completed_at": "2026-01-07T16:05:00Z",
      "duration_seconds": 300
    }
  ]
}
```

---

#### DELETE /api/jobs/{job_id}

Cancella un job in esecuzione.

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "cancelled",
  "message": "Job cancelled successfully"
}
```

---

#### GET /api/jobs/{job_id}/logs

Ottieni log di un job (con streaming opzionale).

**Query Parameters:**
- `limit`: Numero log da recuperare (default: 100)
- `level`: Filtra per livello (INFO, WARNING, ERROR)
- `since`: Timestamp ISO per log più recenti

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "total_logs": 250,
  "logs": [
    {
      "timestamp": "2026-01-07T16:30:15.123Z",
      "level": "INFO",
      "message": "Crawling page 45/100",
      "source": "crawler.spiders.domain_spider"
    },
    {
      "timestamp": "2026-01-07T16:30:16.456Z",
      "level": "INFO",
      "message": "Document found: report.pdf",
      "details": {
        "url": "https://example.com/report.pdf",
        "size_kb": 1024
      }
    }
  ]
}
```

---

### 4. Query RAG Endpoints

#### POST /api/query

Esegui query RAG su una collection.

**Request:**
```json
{
  "collection_name": "aran_docs",
  "query": "Cosa dice l'articolo 3 del CCNL?",
  "top_k": 200,
  "filters": {
    "file_name": "CCNL_2022-2024.pdf"
  },
  "user_id": "user@example.com"
}
```

**Response:**
```json
{
  "query_id": "q_550e8400",
  "answer": "L'articolo 3 del CCNL prevede...",
  "sources": [
    {
      "file_name": "CCNL_2022-2024.pdf",
      "chunk_id": 45,
      "page": 8,
      "score": 0.92,
      "text_snippet": "Articolo 3 - Permessi retribuiti..."
    }
  ],
  "chunks_retrieved": 200,
  "processing_time_ms": 1200,
  "timestamp": "2026-01-07T16:35:00Z"
}
```

---

### 5. Collections Management

#### GET /api/collections

Lista tutte le collection disponibili.

**Query Parameters:**
- `user_id`: Filtra per owner
- `limit`: Max risultati
- `search`: Ricerca per nome/descrizione

**Response:**
```json
{
  "total": 15,
  "collections": [
    {
      "name": "aran_docs",
      "description": "Documenti ARAN",
      "total_chunks": 1245,
      "total_documents": 50,
      "created_by": "user@example.com",
      "created_at": "2026-01-01T10:00:00Z",
      "updated_at": "2026-01-07T16:00:00Z"
    }
  ]
}
```

---

#### GET /api/collections/{name}

Info dettagliate su una collection.

**Response:**
```json
{
  "name": "aran_docs",
  "description": "Documenti ARAN",
  "total_chunks": 1245,
  "total_documents": 50,
  "total_size_mb": 125.5,
  "created_by": "user@example.com",
  "created_at": "2026-01-01T10:00:00Z",
  "updated_at": "2026-01-07T16:00:00Z",
  "metadata": {
    "embedding_model": "text-embedding-3-small",
    "chunk_size": 1000,
    "top_k_default": 200
  },
  "documents": [
    {
      "file_name": "CCNL_2022-2024.pdf",
      "chunks": 150,
      "pages": 50,
      "size_kb": 2048,
      "is_ocr": false
    }
  ]
}
```

---

#### DELETE /api/collections/{name}

Elimina una collection (da Qdrant e MySQL).

**Response:**
```json
{
  "name": "aran_docs",
  "status": "deleted",
  "chunks_deleted": 1245,
  "documents_deleted": 50
}
```

---

#### GET /api/collections/{name}/documents

Lista documenti in una collection.

**Response:**
```json
{
  "collection_name": "aran_docs",
  "total_documents": 50,
  "documents": [
    {
      "id": 1,
      "file_name": "CCNL_2022-2024.pdf",
      "file_type": "pdf",
      "pages": 50,
      "chunks": 150,
      "size_kb": 2048,
      "is_ocr": false,
      "source_url": "https://www.aranagenzia.it/...",
      "processed_at": "2026-01-01T10:00:00Z"
    }
  ]
}
```

---

### 6. WebSocket Endpoints

#### WS /api/jobs/{job_id}/stream

Stream realtime dei log di un job.

**Client (JavaScript):**
```javascript
const ws = new WebSocket('ws://localhost:8000/api/jobs/{job_id}/stream');

ws.onmessage = (event) => {
  const log = JSON.parse(event.data);
  console.log(`[${log.level}] ${log.message}`);
};
```

**Server Message Format:**
```json
{
  "timestamp": "2026-01-07T16:30:15.123Z",
  "level": "INFO",
  "message": "Crawling page 45/100",
  "progress": {
    "percentage": 45,
    "current_page": 45,
    "total_pages": 100
  }
}
```

---

## 🛠️ Implementazione Backend

### Struttura Progetto

```
datapizzarouge/
├── api/
│   ├── __init__.py
│   ├── main.py                      # FastAPI app
│   ├── dependencies.py              # Dependency injection
│   ├── config.py                    # API config
│   │
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── crawl.py                 # Crawl endpoints
│   │   ├── ingest.py                # Ingestion endpoints
│   │   ├── jobs.py                  # Job management
│   │   ├── query.py                 # RAG query
│   │   ├── collections.py           # Collections management
│   │   └── websocket.py             # WebSocket handlers
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── requests.py              # Pydantic request models
│   │   ├── responses.py             # Pydantic response models
│   │   └── database.py              # SQLAlchemy models
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── job_manager.py           # Job orchestration
│   │   ├── process_runner.py        # Subprocess execution
│   │   ├── log_streamer.py          # Log streaming
│   │   └── queue_manager.py         # Job queue management
│   │
│   ├── database/
│   │   ├── __init__.py
│   │   ├── mysql_connection.py      # MySQL connection pool
│   │   ├── repository.py            # Repository pattern
│   │   └── migrations/              # Alembic migrations
│   │
│   └── utils/
│       ├── __init__.py
│       ├── validators.py            # Input validation
│       ├── security.py              # Auth helpers
│       └── logging.py               # Logging config
│
├── cli.py                           # CLI esistente (invariato)
├── multi_crawl.py                   # Multi-crawl (invariato)
├── config.py                        # Config condivisa
├── requirements_api.txt             # Dipendenze API
└── .env                             # Config condivisa
```

### Dependencies (requirements_api.txt)

```txt
# FastAPI
fastapi==0.109.0
uvicorn[standard]==0.27.0
python-multipart==0.0.6

# Database
sqlalchemy==2.0.25
pymysql==1.1.0
alembic==1.13.1

# Async
celery==5.3.4  # Opzionale per job queue avanzata
redis==5.0.1   # Opzionale per caching

# Auth
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4

# Utils
pydantic==2.5.3
python-dotenv==1.0.0
```

### main.py - FastAPI App

```python
"""
FastAPI app per DataPizzaRouge.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from api.routers import crawl, ingest, jobs, query, collections, websocket
from api.database.mysql_connection import engine
from api.models.database import Base
from api import config

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create tables
Base.metadata.create_all(bind=engine)

# FastAPI app
app = FastAPI(
    title="DataPizzaRouge API",
    description="API REST per crawling, ingestion e RAG",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(crawl.router, prefix="/api/crawl", tags=["Crawl"])
app.include_router(ingest.router, prefix="/api/ingest", tags=["Ingestion"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["Jobs"])
app.include_router(query.router, prefix="/api/query", tags=["Query"])
app.include_router(collections.router, prefix="/api/collections", tags=["Collections"])
app.include_router(websocket.router, prefix="/api", tags=["WebSocket"])

@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "service": "DataPizzaRouge API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/api/docs"
    }

@app.get("/api/health")
async def health_check():
    """Detailed health check."""
    # TODO: Check MySQL connection, Qdrant, etc.
    return {
        "status": "healthy",
        "mysql": "connected",
        "qdrant": "connected"
    }

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host=config.API_HOST,
        port=config.API_PORT,
        reload=config.DEBUG
    )
```

### api/config.py

```python
"""
Configurazione API.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# API Settings
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", 8000))
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# CORS
CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5000,http://localhost:3000"
).split(",")

# MySQL
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3306))
MYSQL_USER = os.getenv("MYSQL_USER", "datapizza_user")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "datapizzarouge")
MYSQL_POOL_SIZE = int(os.getenv("MYSQL_POOL_SIZE", 10))
MYSQL_MAX_OVERFLOW = int(os.getenv("MYSQL_MAX_OVERFLOW", 20))

# Job Management
MAX_CONCURRENT_JOBS = int(os.getenv("MAX_CONCURRENT_JOBS", 5))
JOB_TIMEOUT_SECONDS = int(os.getenv("JOB_TIMEOUT_SECONDS", 3600))

# Security
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
```

### api/services/process_runner.py

```python
"""
Service per eseguire subprocess Python CLI.
"""
import subprocess
import sys
import logging
from typing import Optional, Callable
from pathlib import Path

logger = logging.getLogger(__name__)

class ProcessRunner:
    """Esegue comandi CLI come subprocess."""

    def __init__(self, working_dir: Optional[Path] = None):
        self.working_dir = working_dir or Path.cwd()

    def run_crawl(
        self,
        url: str,
        max_pages: int,
        on_output: Optional[Callable[[str], None]] = None
    ) -> subprocess.Popen:
        """
        Avvia crawl via CLI.

        Args:
            url: URL da crawlare
            max_pages: Max pagine
            on_output: Callback per output realtime

        Returns:
            Processo subprocess
        """
        cmd = [
            sys.executable,
            "cli.py",
            "crawl",
            url,
            "--max-pages", str(max_pages)
        ]

        logger.info(f"Starting crawl process: {' '.join(cmd)}")

        process = subprocess.Popen(
            cmd,
            cwd=str(self.working_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )

        # Stream output se callback fornito
        if on_output:
            for line in iter(process.stdout.readline, ''):
                if line:
                    on_output(line.strip())

        return process

    def run_ingest_domain(
        self,
        domain: str,
        collection_name: str,
        max_pages: Optional[int] = None,
        on_output: Optional[Callable[[str], None]] = None
    ) -> subprocess.Popen:
        """Avvia ingestion HTML via CLI."""
        cmd = [
            sys.executable,
            "cli.py",
            "ingest",
            "--domain", domain,
            "--collection", collection_name
        ]

        if max_pages:
            cmd.extend(["--max-pages", str(max_pages)])

        logger.info(f"Starting ingest process: {' '.join(cmd)}")

        # Invia 'y' automaticamente per conferma
        process = subprocess.Popen(
            cmd,
            cwd=str(self.working_dir),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        # Conferma automatica
        process.stdin.write("y\n")
        process.stdin.flush()

        # Stream output
        if on_output:
            for line in iter(process.stdout.readline, ''):
                if line:
                    on_output(line.strip())

        return process

    def run_ingest_documents(
        self,
        documents_dir: str,
        collection_name: str,
        extensions: Optional[list] = None,
        on_output: Optional[Callable[[str], None]] = None
    ) -> subprocess.Popen:
        """Avvia ingestion documenti via CLI."""
        cmd = [
            sys.executable,
            "cli.py",
            "ingest-docs",
            "--dir", documents_dir,
            "--collection", collection_name
        ]

        if extensions:
            for ext in extensions:
                cmd.extend(["-e", ext])

        logger.info(f"Starting ingest-docs process: {' '.join(cmd)}")

        process = subprocess.Popen(
            cmd,
            cwd=str(self.working_dir),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        # Conferma automatica
        process.stdin.write("y\n")
        process.stdin.flush()

        # Stream output
        if on_output:
            for line in iter(process.stdout.readline, ''):
                if line:
                    on_output(line.strip())

        return process
```

---

## 🎨 Integrazione Blazor

### Setup Blazor

**appsettings.json:**
```json
{
  "DataPizzaRougeApi": {
    "BaseUrl": "http://localhost:8000",
    "ApiKey": "your-api-key-here",
    "Timeout": 300
  },
  "ConnectionStrings": {
    "DataPizzaRouge": "Server=localhost;Database=datapizzarouge;User=blazor_user;Password=***;"
  }
}
```

### API Client (C#)

```csharp
// Services/DataPizzaRougeApiClient.cs
using System.Net.Http.Json;

public class DataPizzaRougeApiClient
{
    private readonly HttpClient _httpClient;
    private readonly string _baseUrl;

    public DataPizzaRougeApiClient(HttpClient httpClient, IConfiguration config)
    {
        _httpClient = httpClient;
        _baseUrl = config["DataPizzaRougeApi:BaseUrl"];

        var apiKey = config["DataPizzaRougeApi:ApiKey"];
        _httpClient.DefaultRequestHeaders.Add("X-API-Key", apiKey);
    }

    // Crawl
    public async Task<JobResponse> StartCrawlAsync(CrawlRequest request)
    {
        var response = await _httpClient.PostAsJsonAsync(
            $"{_baseUrl}/api/crawl/start",
            request
        );
        response.EnsureSuccessStatusCode();
        return await response.Content.ReadFromJsonAsync<JobResponse>();
    }

    // Job Status
    public async Task<JobStatusResponse> GetJobStatusAsync(string jobId)
    {
        var response = await _httpClient.GetAsync(
            $"{_baseUrl}/api/jobs/{jobId}"
        );
        response.EnsureSuccessStatusCode();
        return await response.Content.ReadFromJsonAsync<JobStatusResponse>();
    }

    // Query
    public async Task<QueryResponse> QueryAsync(QueryRequest request)
    {
        var response = await _httpClient.PostAsJsonAsync(
            $"{_baseUrl}/api/query",
            request
        );
        response.EnsureSuccessStatusCode();
        return await response.Content.ReadFromJsonAsync<QueryResponse>();
    }

    // Collections
    public async Task<List<CollectionInfo>> GetCollectionsAsync()
    {
        var response = await _httpClient.GetAsync(
            $"{_baseUrl}/api/collections"
        );
        response.EnsureSuccessStatusCode();
        var result = await response.Content.ReadFromJsonAsync<CollectionsResponse>();
        return result.Collections;
    }
}

// Models
public record CrawlRequest(
    string Url,
    int MaxPages,
    string CollectionName,
    string UserId
);

public record JobResponse(
    string JobId,
    string Status,
    string Message
);

public record JobStatusResponse(
    string JobId,
    string Type,
    string Status,
    JobProgress Progress,
    DateTime CreatedAt,
    DateTime? StartedAt,
    DateTime? EstimatedCompletion
);

public record JobProgress(
    string Phase,
    int CurrentPage,
    int TotalPages,
    int Percentage,
    int DocumentsFound
);
```

### Blazor Component Example

```razor
@* Pages/Crawl.razor *@
@page "/crawl"
@inject DataPizzaRougeApiClient ApiClient
@inject NavigationManager Navigation

<h3>Crawl Website</h3>

<EditForm Model="@crawlModel" OnValidSubmit="StartCrawl">
    <DataAnnotationsValidator />

    <div class="mb-3">
        <label>URL Website</label>
        <InputText @bind-Value="crawlModel.Url" class="form-control" />
        <ValidationMessage For="@(() => crawlModel.Url)" />
    </div>

    <div class="mb-3">
        <label>Max Pages</label>
        <InputNumber @bind-Value="crawlModel.MaxPages" class="form-control" />
    </div>

    <div class="mb-3">
        <label>Collection Name</label>
        <InputText @bind-Value="crawlModel.CollectionName" class="form-control" />
    </div>

    <button type="submit" class="btn btn-primary" disabled="@isSubmitting">
        @if (isSubmitting)
        {
            <span class="spinner-border spinner-border-sm me-2"></span>
        }
        Avvia Crawl
    </button>
</EditForm>

@if (!string.IsNullOrEmpty(jobId))
{
    <div class="alert alert-success mt-3">
        <h5>Job Creato!</h5>
        <p>Job ID: <code>@jobId</code></p>
        <button class="btn btn-link" @onclick="NavigateToJob">
            Monitora Progresso →
        </button>
    </div>
}

@code {
    private CrawlModel crawlModel = new();
    private bool isSubmitting = false;
    private string? jobId;

    private async Task StartCrawl()
    {
        isSubmitting = true;

        try
        {
            var request = new CrawlRequest(
                crawlModel.Url,
                crawlModel.MaxPages,
                crawlModel.CollectionName,
                "current-user@example.com"  // TODO: Get from auth
            );

            var response = await ApiClient.StartCrawlAsync(request);
            jobId = response.JobId;
        }
        finally
        {
            isSubmitting = false;
        }
    }

    private void NavigateToJob()
    {
        Navigation.NavigateTo($"/jobs/{jobId}");
    }

    public class CrawlModel
    {
        [Required]
        [Url]
        public string Url { get; set; } = "";

        [Range(1, 10000)]
        public int MaxPages { get; set; } = 100;

        [Required]
        public string CollectionName { get; set; } = "";
    }
}
```

---

## 🚀 Deployment

### Docker Compose Setup

```yaml
# docker-compose.yml
version: '3.8'

services:
  # MySQL
  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: rootpassword
      MYSQL_DATABASE: datapizzarouge
      MYSQL_USER: datapizza_user
      MYSQL_PASSWORD: secure_password
    volumes:
      - mysql_data:/var/lib/mysql
      - ./database/init.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "3306:3306"
    networks:
      - datapizza_net

  # Qdrant
  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant_data:/qdrant/storage
    networks:
      - datapizza_net

  # FastAPI
  api:
    build:
      context: .
      dockerfile: Dockerfile.api
    environment:
      MYSQL_HOST: mysql
      MYSQL_USER: datapizza_user
      MYSQL_PASSWORD: secure_password
      QDRANT_HOST: qdrant
      QDRANT_PORT: 6333
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
      - ./.env:/app/.env
    depends_on:
      - mysql
      - qdrant
    networks:
      - datapizza_net

  # Blazor (opzionale)
  blazor:
    build:
      context: ./blazor-app
      dockerfile: Dockerfile
    environment:
      DataPizzaRougeApi__BaseUrl: http://api:8000
    ports:
      - "5000:80"
    depends_on:
      - api
    networks:
      - datapizza_net

volumes:
  mysql_data:
  qdrant_data:

networks:
  datapizza_net:
```

### Dockerfile.api

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt requirements_api.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements_api.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8000

# Run FastAPI
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 🔐 Sicurezza

### 1. Autenticazione JWT

```python
# api/utils/security.py
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_access_token(data: dict, expires_delta: timedelta = None):
    """Crea JWT token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode,
        config.SECRET_KEY,
        algorithm=config.ALGORITHM
    )
    return encoded_jwt

def verify_token(token: str):
    """Verifica JWT token."""
    try:
        payload = jwt.decode(
            token,
            config.SECRET_KEY,
            algorithms=[config.ALGORITHM]
        )
        return payload
    except JWTError:
        return None
```

### 2. Rate Limiting

```python
# api/dependencies.py
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

# In endpoint
@app.post("/api/crawl/start")
@limiter.limit("5/minute")  # Max 5 crawl al minuto
async def start_crawl(request: Request, ...):
    ...
```

### 3. Input Validation

```python
# api/models/requests.py
from pydantic import BaseModel, validator, HttpUrl

class CrawlRequest(BaseModel):
    url: HttpUrl
    max_pages: int
    collection_name: str

    @validator('max_pages')
    def validate_max_pages(cls, v):
        if v < 1 or v > 10000:
            raise ValueError('max_pages must be between 1 and 10000')
        return v

    @validator('url')
    def validate_url_domain(cls, v):
        # Whitelist/blacklist domains
        blocked_domains = ['localhost', '127.0.0.1', '0.0.0.0']
        if any(domain in str(v) for domain in blocked_domains):
            raise ValueError('Domain not allowed')
        return v
```

---

## 🧪 Testing

### Unit Tests

```python
# tests/test_api.py
import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_create_crawl_job():
    """Test creazione job crawl."""
    response = client.post(
        "/api/crawl/start",
        json={
            "url": "https://example.com",
            "max_pages": 10,
            "collection_name": "test_coll",
            "user_id": "test@example.com"
        }
    )

    assert response.status_code == 201
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "queued"

def test_get_job_status():
    """Test recupero status job."""
    # Create job first
    create_response = client.post("/api/crawl/start", json={...})
    job_id = create_response.json()["job_id"]

    # Get status
    response = client.get(f"/api/jobs/{job_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == job_id
```

### Integration Tests

```python
# tests/test_integration.py
import pytest
from api.services.process_runner import ProcessRunner

@pytest.mark.integration
def test_full_crawl_workflow():
    """Test workflow completo crawl."""
    runner = ProcessRunner()

    # Start crawl
    process = runner.run_crawl(
        url="https://example.com",
        max_pages=5
    )

    # Wait for completion
    returncode = process.wait(timeout=300)
    assert returncode == 0

    # Verify data exists
    # Check Qdrant, MySQL, file system
```

---

## 📚 Prossimi Passi

### Fase 1: Setup Base (Week 1-2)
1. Setup MySQL database e schema
2. Implementare FastAPI base con endpoint principali
3. Implementare ProcessRunner e job management
4. Testing base endpoint

### Fase 2: Job Management (Week 3)
1. Implementare job queue avanzata
2. WebSocket per log streaming
3. Job cancellation e retry logic
4. Monitoring e health checks

### Fase 3: Integrazione Blazor (Week 4-5)
1. Creare API client C#
2. Implementare UI Blazor pages
3. Realtime updates con SignalR/WebSocket
4. Dashboard e monitoring

### Fase 4: Production Ready (Week 6)
1. Security hardening (JWT, rate limiting)
2. Docker containerization
3. CI/CD pipeline
4. Documentation e API docs

---

## 📞 Note Implementative

### Priorità

1. **Alta**: Crawl e ingestion endpoints (core functionality)
2. **Media**: Job management e monitoring
3. **Bassa**: Query RAG endpoint (può usare CLI direttamente per ora)

### Considerazioni

- **La CLI rimane funzionale**: Zero breaking changes
- **API è opzionale**: Sistema funziona anche senza
- **MySQL per tracking**: Non sostituisce Qdrant, lo affianca
- **Subprocess non thread**: Ogni job è processo separato per isolamento

### Performance

- **Max concurrent jobs**: 5 (configurabile)
- **Connection pooling**: MySQL pool size 10
- **Timeout job**: 1 ora default (configurabile)
- **Log retention**: 30 giorni (configurabile)

---

## ✅ Checklist Implementazione

- [ ] Setup MySQL database e schema
- [ ] Implementare FastAPI base app
- [ ] Implementare crawl endpoints
- [ ] Implementare ingest endpoints
- [ ] Implementare job management
- [ ] Implementare WebSocket streaming
- [ ] Implementare query endpoints
- [ ] Implementare collections management
- [ ] Setup autenticazione JWT
- [ ] Implementare rate limiting
- [ ] Creare Blazor API client
- [ ] Creare Blazor UI components
- [ ] Docker containerization
- [ ] Testing suite
- [ ] Documentation finale

---

**Documento creato**: 2026-01-07
**Versione**: 1.0
**Status**: Ready for Implementation

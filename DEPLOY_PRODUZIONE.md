# Deploy Produzione - DataPizzaRouge API

Guida completa per deploy in produzione dell'API FastAPI con configurazioni robuste e sicure.

---

## 🎯 Differenze Dev vs Produzione

| Aspetto | Sviluppo | Produzione |
|---------|----------|------------|
| **Server** | `uvicorn --reload` | Gunicorn + Uvicorn workers |
| **Workers** | 1 | 4-16 (multi-processo) |
| **Reload** | Auto-reload attivo | Disabilitato |
| **Logs** | Console colorati | File strutturati + syslog |
| **Reverse Proxy** | Nessuno | Nginx/Caddy |
| **SSL/TLS** | HTTP | HTTPS (certificati) |
| **Environment** | `.env` locale | Variabili sistema/secrets |
| **CORS** | `allow_origins=["*"]` | Domini specifici |
| **Error Details** | Stack trace completi | Messaggi generici |

---

## 🚀 Opzione 1: Gunicorn + Uvicorn (CONSIGLIATO)

### Installazione

```bash
pip install gunicorn
```

Aggiorna `requirements.txt`:
```txt
gunicorn==21.2.0
```

### Configurazione

**Crea file `gunicorn_config.py`**:

```python
"""
Configurazione Gunicorn per produzione
"""
import multiprocessing
import os

# Binding
bind = "0.0.0.0:8000"

# Workers
workers = int(os.getenv("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1))
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 1000  # Restart worker dopo N richieste (previene memory leak)
max_requests_jitter = 50

# Timeout
timeout = 120  # 2 minuti per query RAG lunghe
graceful_timeout = 30
keepalive = 5

# Logging
accesslog = "logs/access.log"
errorlog = "logs/error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "datapizzarouge_api"

# Server mechanics
daemon = False
pidfile = "/tmp/gunicorn.pid"
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (se gestisci SSL qui invece che in Nginx)
# keyfile = "/path/to/key.pem"
# certfile = "/path/to/cert.pem"

# Preload app (carica prima di forking workers)
preload_app = True

# Worker lifecycle hooks
def on_starting(server):
    """Chiamato quando master process parte"""
    print("🚀 Gunicorn master process starting")

def on_reload(server):
    """Chiamato al reload"""
    print("🔄 Gunicorn reloading")

def when_ready(server):
    """Chiamato quando server è pronto"""
    print("✅ Gunicorn ready to serve requests")

def on_exit(server):
    """Chiamato alla chiusura"""
    print("👋 Gunicorn shutting down")

def worker_int(worker):
    """Chiamato quando worker riceve SIGINT"""
    print(f"⚠️  Worker {worker.pid} received SIGINT")

def worker_abort(worker):
    """Chiamato quando worker viene abortito"""
    print(f"❌ Worker {worker.pid} aborted")
```

### Avvio Produzione

```bash
# Crea directory logs
mkdir -p logs

# Avvia con config file
gunicorn api:app -c gunicorn_config.py

# O con parametri CLI
gunicorn api:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 120 \
  --access-logfile logs/access.log \
  --error-logfile logs/error.log \
  --log-level info
```

### Script di Avvio

**Crea `start_production.sh` (Linux/Mac)**:

```bash
#!/bin/bash
set -e

echo "🚀 Avvio DataPizzaRouge API - Produzione"

# Verifica environment
if [ ! -f ".env" ]; then
    echo "❌ File .env non trovato!"
    exit 1
fi

# Load environment
export $(cat .env | grep -v '^#' | xargs)

# Verifica API keys
if [ -z "$OPENAI_API_KEY" ] || [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "❌ API Keys non configurate!"
    exit 1
fi

# Crea logs directory
mkdir -p logs

# Avvia Gunicorn
exec gunicorn api:app \
  -c gunicorn_config.py \
  --log-file=-
```

**Crea `start_production.bat` (Windows)**:

```batch
@echo off
echo Starting DataPizzaRouge API - Production

REM Verifica .env
if not exist ".env" (
    echo ERROR: .env file not found!
    exit /b 1
)

REM Crea logs directory
if not exist "logs" mkdir logs

REM Avvia Gunicorn
gunicorn api:app -c gunicorn_config.py

pause
```

Rendi eseguibili:
```bash
chmod +x start_production.sh
```

---

## 🚀 Opzione 2: Uvicorn Standalone Multi-Workers

Se non vuoi Gunicorn, Uvicorn supporta workers nativamente:

```bash
uvicorn api:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --timeout-keep-alive 120 \
  --no-access-log \
  --log-level warning
```

**Pro**: Setup più semplice
**Contro**: Meno features di Gunicorn (no graceful reload, meno controllo)

---

## 🔒 Reverse Proxy: Nginx

### Perché Nginx?

- ✅ Gestione SSL/TLS (HTTPS)
- ✅ Load balancing
- ✅ Caching statico
- ✅ Rate limiting
- ✅ Compressione gzip
- ✅ Security headers

### Installazione

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install nginx

# CentOS/RHEL
sudo yum install nginx

# macOS
brew install nginx
```

### Configurazione Nginx

**Crea `/etc/nginx/sites-available/datapizzarouge`**:

```nginx
# Upstream FastAPI (Gunicorn)
upstream fastapi_backend {
    server 127.0.0.1:8000 fail_timeout=0;
}

# Redirect HTTP → HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name api.tuodominio.com;

    return 301 https://$server_name$request_uri;
}

# HTTPS Server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name api.tuodominio.com;

    # SSL Certificates (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/api.tuodominio.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.tuodominio.com/privkey.pem;

    # SSL Configuration (Mozilla Modern)
    ssl_protocols TLSv1.3 TLSv1.2;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256';
    ssl_prefer_server_ciphers off;
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:10m;
    ssl_session_tickets off;

    # HSTS (preload optional)
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;

    # Security Headers
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Logging
    access_log /var/log/nginx/datapizzarouge_access.log;
    error_log /var/log/nginx/datapizzarouge_error.log warn;

    # Client max body size (per upload grandi)
    client_max_body_size 10M;

    # Timeouts (per query RAG lunghe)
    proxy_connect_timeout 120s;
    proxy_send_timeout 120s;
    proxy_read_timeout 120s;

    # Proxy to FastAPI
    location / {
        proxy_pass http://fastapi_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support (se usi streaming)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # Buffering off per streaming
        proxy_buffering off;
    }

    # Health check (no logging)
    location /health {
        proxy_pass http://fastapi_backend/health;
        access_log off;
    }

    # Block hidden files
    location ~ /\. {
        deny all;
    }
}
```

### Attivazione Nginx

```bash
# Symlink config
sudo ln -s /etc/nginx/sites-available/datapizzarouge /etc/nginx/sites-enabled/

# Test configurazione
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx

# Enable autostart
sudo systemctl enable nginx
```

### SSL con Let's Encrypt (Gratis)

```bash
# Installa Certbot
sudo apt install certbot python3-certbot-nginx

# Ottieni certificato (automatico, modifica Nginx config)
sudo certbot --nginx -d api.tuodominio.com

# Auto-renewal (aggiunge cron job automaticamente)
sudo certbot renew --dry-run
```

---

## 🔒 Reverse Proxy: Caddy (Alternativa Semplice)

**Caddy** gestisce SSL automaticamente (più facile di Nginx).

### Installazione

```bash
# Ubuntu/Debian
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/caddy-stable-archive-keyring.gpg] https://dl.cloudsmith.io/public/caddy/stable/deb/debian any-version main" | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update
sudo apt install caddy
```

### Configurazione Caddy

**Crea `/etc/caddy/Caddyfile`**:

```caddy
api.tuodominio.com {
    # SSL automatico con Let's Encrypt

    # Security headers
    header {
        Strict-Transport-Security "max-age=63072000; includeSubDomains; preload"
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        X-XSS-Protection "1; mode=block"
        Referrer-Policy "strict-origin-when-cross-origin"
    }

    # Logging
    log {
        output file /var/log/caddy/datapizzarouge.log
        format json
    }

    # Reverse proxy to FastAPI
    reverse_proxy localhost:8000 {
        # Timeouts
        transport http {
            read_timeout 120s
            write_timeout 120s
        }
    }
}
```

**Riavvia Caddy**:

```bash
sudo systemctl reload caddy
sudo systemctl enable caddy
```

**Caddy gestisce SSL automaticamente** - zero configurazione! 🎉

---

## 🐳 Docker (Containerizzazione)

### Dockerfile

**Crea `Dockerfile`**:

```dockerfile
FROM python:3.13-slim

# Metadata
LABEL maintainer="tuo@email.com"
LABEL version="1.0"

# Working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir gunicorn

# Copy application
COPY . .

# Create logs directory
RUN mkdir -p logs

# Non-root user (security)
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Start command
CMD ["gunicorn", "api:app", "-c", "gunicorn_config.py"]
```

### Docker Compose

**Crea `docker-compose.yml`**:

```yaml
version: '3.8'

services:
  api:
    build: .
    container_name: datapizzarouge_api
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - QDRANT_MODE=${QDRANT_MODE}
      - QDRANT_URL=${QDRANT_URL}
      - QDRANT_API_KEY=${QDRANT_API_KEY}
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    restart: unless-stopped
    networks:
      - datapizzarouge_network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

networks:
  datapizzarouge_network:
    driver: bridge
```

### Build e Run

```bash
# Build image
docker-compose build

# Avvia in background
docker-compose up -d

# Logs
docker-compose logs -f api

# Stop
docker-compose down

# Rebuild e restart
docker-compose up -d --build
```

---

## 🌐 Deploy Cloud

### Opzione 1: Azure App Service

```bash
# Install Azure CLI
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Login
az login

# Create resource group
az group create --name datapizzarouge-rg --location westeurope

# Create App Service Plan (Linux)
az appservice plan create \
  --name datapizzarouge-plan \
  --resource-group datapizzarouge-rg \
  --sku B1 \
  --is-linux

# Create Web App (Python 3.13)
az webapp create \
  --resource-group datapizzarouge-rg \
  --plan datapizzarouge-plan \
  --name datapizzarouge-api \
  --runtime "PYTHON:3.13"

# Configure environment variables
az webapp config appsettings set \
  --resource-group datapizzarouge-rg \
  --name datapizzarouge-api \
  --settings \
    OPENAI_API_KEY="your-key" \
    ANTHROPIC_API_KEY="your-key" \
    QDRANT_MODE="cloud" \
    QDRANT_URL="your-url" \
    QDRANT_API_KEY="your-key"

# Configure startup command
az webapp config set \
  --resource-group datapizzarouge-rg \
  --name datapizzarouge-api \
  --startup-file "gunicorn api:app -c gunicorn_config.py"

# Deploy from local Git
az webapp deployment source config-local-git \
  --name datapizzarouge-api \
  --resource-group datapizzarouge-rg

# Git push
git remote add azure <deployment-url>
git push azure main
```

### Opzione 2: AWS Elastic Beanstalk

**Crea `.ebextensions/01_python.config`**:

```yaml
option_settings:
  aws:elasticbeanstalk:container:python:
    WSGIPath: api:app
  aws:elasticbeanstalk:application:environment:
    PYTHONPATH: "/var/app/current:$PYTHONPATH"

container_commands:
  01_install_gunicorn:
    command: "pip install gunicorn"
```

**Deploy**:

```bash
# Install EB CLI
pip install awsebcli

# Initialize
eb init -p python-3.13 datapizzarouge

# Create environment
eb create datapizzarouge-prod

# Set environment variables
eb setenv OPENAI_API_KEY=xxx ANTHROPIC_API_KEY=xxx

# Deploy
eb deploy

# Open in browser
eb open
```

### Opzione 3: Google Cloud Run

```bash
# Build container
gcloud builds submit --tag gcr.io/PROJECT-ID/datapizzarouge

# Deploy
gcloud run deploy datapizzarouge \
  --image gcr.io/PROJECT-ID/datapizzarouge \
  --platform managed \
  --region europe-west1 \
  --allow-unauthenticated \
  --set-env-vars OPENAI_API_KEY=xxx,ANTHROPIC_API_KEY=xxx
```

---

## 📊 Monitoring e Logs

### Structured Logging

**Modifica `api.py` per logging JSON**:

```python
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
        }
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_data)

# Configure
handler = logging.FileHandler("logs/app.json")
handler.setFormatter(JSONFormatter())
logger = logging.getLogger("uvicorn")
logger.addHandler(handler)
```

### Prometheus Metrics (Opzionale)

```bash
pip install prometheus-fastapi-instrumentator
```

```python
# api.py
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI()
Instrumentator().instrument(app).expose(app)
```

Metrics disponibili su: `http://localhost:8000/metrics`

---

## 🔐 Security Checklist

### Applicazione

- [ ] **Environment variables** da sistema (non `.env` committato)
- [ ] **CORS limitato** a domini specifici
- [ ] **Rate limiting** implementato
- [ ] **API Key validation** (se API pubblica)
- [ ] **Input validation** (Pydantic models)
- [ ] **Error handling** (no stack trace in produzione)
- [ ] **Security headers** (Nginx/Caddy)

### Infrastruttura

- [ ] **HTTPS obbligatorio** (SSL/TLS)
- [ ] **Firewall** configurato (solo porte 80, 443, 22)
- [ ] **SSH Key-only** (no password login)
- [ ] **Automatic updates** abilitati
- [ ] **Backup database** (Qdrant snapshot)
- [ ] **Monitoring** attivo (uptime, errors)
- [ ] **Log rotation** configurato

---

## 🚦 Systemd Service (Linux)

Per far partire l'API automaticamente al boot.

**Crea `/etc/systemd/system/datapizzarouge.service`**:

```ini
[Unit]
Description=DataPizzaRouge FastAPI Service
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/opt/datapizzarouge
Environment="PATH=/opt/datapizzarouge/venv/bin"
EnvironmentFile=/opt/datapizzarouge/.env
ExecStart=/opt/datapizzarouge/venv/bin/gunicorn api:app -c gunicorn_config.py
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=on-failure
RestartSec=10s

[Install]
WantedBy=multi-user.target
```

**Attiva service**:

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable autostart
sudo systemctl enable datapizzarouge

# Start service
sudo systemctl start datapizzarouge

# Check status
sudo systemctl status datapizzarouge

# View logs
sudo journalctl -u datapizzarouge -f
```

**Gestione**:

```bash
# Restart
sudo systemctl restart datapizzarouge

# Stop
sudo systemctl stop datapizzarouge

# Reload (graceful)
sudo systemctl reload datapizzarouge
```

---

## 📈 Performance Tuning

### Gunicorn Workers

```python
# Calcolo ottimale
import multiprocessing

# CPU-bound tasks
workers = multiprocessing.cpu_count() * 2 + 1

# I/O-bound tasks (RAG queries)
workers = multiprocessing.cpu_count() * 4
```

### Connection Pooling

Per Qdrant e altri servizi esterni:

```python
# storage/vector_store_manager.py
class VectorStoreManager:
    _client_pool = None

    @classmethod
    def get_client(cls):
        if cls._client_pool is None:
            cls._client_pool = QdrantClient(
                url=config.QDRANT_URL,
                api_key=config.QDRANT_API_KEY,
                timeout=30,
                # Connection pooling
                prefer_grpc=True,
                grpc_port=6334,
            )
        return cls._client_pool
```

### Caching

```bash
pip install fastapi-cache2[redis]
```

```python
# api.py
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from redis import asyncio as aioredis

@app.on_event("startup")
async def startup():
    redis = aioredis.from_url("redis://localhost", encoding="utf8")
    FastAPICache.init(RedisBackend(redis), prefix="datapizzarouge-cache")

# Cache collection list (cambia raramente)
from fastapi_cache.decorator import cache

@app.get("/api/collections")
@cache(expire=300)  # 5 minuti
async def get_collections():
    ...
```

---

## 🧪 Testing Produzione

### Load Testing con Locust

```bash
pip install locust
```

**Crea `locustfile.py`**:

```python
from locust import HttpUser, task, between

class RagUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def health_check(self):
        self.client.get("/health")

    @task(3)
    def query_rag(self):
        self.client.post("/api/query", json={
            "collection": "tuosito_latest",
            "query": "test query",
            "top_k": 5
        })

# Run: locust --host=http://localhost:8000
```

### Smoke Test

```bash
# Test connectivity
curl -v http://localhost:8000/health

# Test query
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"collection":"test","query":"test"}'

# Load test (Apache Bench)
ab -n 1000 -c 10 http://localhost:8000/health
```

---

## 📊 Confronto Soluzioni

| Soluzione | Complessità | Performance | Costo | Use Case |
|-----------|-------------|-------------|-------|----------|
| **Uvicorn solo** | ⭐ | ⭐⭐ | Gratis | Dev/testing |
| **Gunicorn + Uvicorn** | ⭐⭐ | ⭐⭐⭐⭐ | Gratis | Piccola prod |
| **+ Nginx** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Gratis | Prod seria |
| **+ Caddy** | ⭐⭐ | ⭐⭐⭐⭐ | Gratis | Prod facile |
| **Docker** | ⭐⭐⭐ | ⭐⭐⭐⭐ | Gratis | Portabilità |
| **Azure App Service** | ⭐ | ⭐⭐⭐⭐ | €€ | Managed cloud |
| **AWS EB** | ⭐⭐ | ⭐⭐⭐⭐⭐ | €€€ | Scalabilità |
| **Google Cloud Run** | ⭐ | ⭐⭐⭐⭐ | €/pay-per-use | Serverless |

---

## 🎯 Raccomandazioni Finali

### Setup Minimo Produzione
```bash
Gunicorn (4 workers) + Nginx + SSL (Let's Encrypt)
```

### Setup Robusto
```bash
Docker + Gunicorn + Nginx + Monitoring + Backup automatici
```

### Setup Enterprise
```bash
Kubernetes + Docker + Load Balancer + Auto-scaling + Prometheus/Grafana
```

---

## 📝 Quick Commands

```bash
# Dev
uvicorn api:app --reload

# Produzione semplice
gunicorn api:app -w 4 --worker-class uvicorn.workers.UvicornWorker -b 0.0.0.0:8000

# Produzione completa
./start_production.sh

# Con Docker
docker-compose up -d

# Check health
curl http://localhost:8000/health

# Check processes
ps aux | grep gunicorn

# Check logs
tail -f logs/error.log
```

---

**Pronto per la produzione!** 🚀

Per domande specifiche sul tuo setup, fammi sapere! 💪

# Configurazione Apache - DataPizzaRouge API

Guida per usare Apache come reverse proxy per l'API FastAPI.

---

## 🎯 Architettura

```
Internet
   ↓
Apache (porta 80/443) - Reverse Proxy + SSL
   ↓
Gunicorn (porta 8000) - Process Manager
   ↓
Uvicorn Workers (4-16) - FastAPI App
```

---

## 🔧 Prerequisiti Apache

### Moduli Richiesti

Apache deve avere questi moduli attivi:

```bash
# Linux (Ubuntu/Debian)
sudo a2enmod proxy
sudo a2enmod proxy_http
sudo a2enmod proxy_wstunnel  # Per WebSocket/streaming
sudo a2enmod ssl
sudo a2enmod headers
sudo a2enmod rewrite

# Restart Apache
sudo systemctl restart apache2
```

```bash
# Windows (XAMPP/Apache)
# Modifica httpd.conf, decommmenta queste righe:
LoadModule proxy_module modules/mod_proxy.so
LoadModule proxy_http_module modules/mod_proxy_http.so
LoadModule proxy_wstunnel_module modules/mod_proxy_wstunnel.so
LoadModule ssl_module modules/mod_ssl.so
LoadModule headers_module modules/mod_headers.so
LoadModule rewrite_module modules/mod_rewrite.so

# Restart Apache
# Da XAMPP Control Panel → Stop/Start Apache
```

### Verifica Moduli Attivi

```bash
# Linux
apache2ctl -M | grep proxy

# Output atteso:
# proxy_module (shared)
# proxy_http_module (shared)
# proxy_wstunnel_module (shared)
```

```bash
# Windows
httpd.exe -M | findstr proxy
```

---

## 🌐 Configurazione Apache - VirtualHost

### Opzione 1: Subdomain API (api.tuodominio.com)

**Linux: `/etc/apache2/sites-available/datapizzarouge-api.conf`**
**Windows: `C:\xampp\apache\conf\extra\httpd-vhosts.conf`** (aggiungi alla fine)

```apache
# HTTP → HTTPS Redirect
<VirtualHost *:80>
    ServerName api.tuodominio.com
    ServerAdmin admin@tuodominio.com

    # Redirect a HTTPS
    RewriteEngine On
    RewriteCond %{HTTPS} off
    RewriteRule ^(.*)$ https://%{HTTP_HOST}$1 [R=301,L]

    ErrorLog ${APACHE_LOG_DIR}/datapizzarouge_error.log
    CustomLog ${APACHE_LOG_DIR}/datapizzarouge_access.log combined
</VirtualHost>

# HTTPS VirtualHost
<VirtualHost *:443>
    ServerName api.tuodominio.com
    ServerAdmin admin@tuodominio.com

    # SSL Configuration
    SSLEngine on
    SSLCertificateFile /etc/letsencrypt/live/api.tuodominio.com/fullchain.pem
    SSLCertificateKeyFile /etc/letsencrypt/live/api.tuodominio.com/privkey.pem

    # SSL Security (Mozilla Modern)
    SSLProtocol all -SSLv3 -TLSv1 -TLSv1.1
    SSLCipherSuite ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384
    SSLHonorCipherOrder off
    SSLSessionTickets off

    # HSTS Header
    Header always set Strict-Transport-Security "max-age=63072000; includeSubDomains; preload"

    # Security Headers
    Header always set X-Content-Type-Options "nosniff"
    Header always set X-Frame-Options "DENY"
    Header always set X-XSS-Protection "1; mode=block"
    Header always set Referrer-Policy "strict-origin-when-cross-origin"

    # Remove server signature
    ServerSignature Off
    Header unset Server

    # Logging
    ErrorLog ${APACHE_LOG_DIR}/datapizzarouge_error.log
    CustomLog ${APACHE_LOG_DIR}/datapizzarouge_access.log combined

    # Proxy Configuration
    ProxyPreserveHost On
    ProxyRequests Off
    ProxyTimeout 120

    # Reverse Proxy to Gunicorn (localhost:8000)
    ProxyPass / http://127.0.0.1:8000/
    ProxyPassReverse / http://127.0.0.1:8000/

    # WebSocket Support (per streaming se implementato)
    RewriteEngine On
    RewriteCond %{HTTP:Upgrade} =websocket [NC]
    RewriteRule /(.*)           ws://127.0.0.1:8000/$1 [P,L]
    RewriteCond %{HTTP:Upgrade} !=websocket [NC]
    RewriteRule /(.*)           http://127.0.0.1:8000/$1 [P,L]

    # Headers forwarding
    RequestHeader set X-Forwarded-Proto "https"
    RequestHeader set X-Forwarded-Port "443"
    RequestHeader set X-Real-IP %{REMOTE_ADDR}s

    # Timeout per query RAG lunghe
    ProxyTimeout 120

    # Disable buffering per streaming
    SetEnv proxy-nokeepalive 1
    SetEnv proxy-sendchunked 1

    # Health check (no logging)
    <Location /health>
        SetEnv no-log 1
    </Location>
</VirtualHost>
```

### Opzione 2: Subdirectory (tuodominio.com/api)

Se vuoi l'API sotto `/api` invece di subdomain:

```apache
<VirtualHost *:443>
    ServerName tuodominio.com
    DocumentRoot /var/www/tuodominio

    SSLEngine on
    SSLCertificateFile /path/to/cert.pem
    SSLCertificateKeyFile /path/to/key.pem

    # ... altri contenuti del sito ...

    # API FastAPI su /api
    <Location /api>
        ProxyPreserveHost On
        ProxyPass http://127.0.0.1:8000
        ProxyPassReverse http://127.0.0.1:8000

        # Timeout
        ProxyTimeout 120

        # Headers
        RequestHeader set X-Forwarded-Proto "https"
        RequestHeader set X-Forwarded-Prefix "/api"
    </Location>

    # Health check
    <Location /api/health>
        ProxyPass http://127.0.0.1:8000/health
        ProxyPassReverse http://127.0.0.1:8000/health
        SetEnv no-log 1
    </Location>
</VirtualHost>
```

**IMPORTANTE**: Se uso `/api`, devi modificare FastAPI:

```python
# api.py
app = FastAPI(
    title="DataPizzaRouge API",
    root_path="/api"  # ← Aggiungi questo
)
```

---

## 🔒 SSL/TLS con Let's Encrypt

### Linux (Certbot)

```bash
# Installa Certbot per Apache
sudo apt install certbot python3-certbot-apache

# Ottieni certificato (automatico)
sudo certbot --apache -d api.tuodominio.com

# Certbot modifica automaticamente la config Apache!

# Test auto-renewal
sudo certbot renew --dry-run

# Auto-renewal è già configurato in cron
```

### Windows (Manuale)

**Opzione 1: Win-ACME** (Let's Encrypt automatico per Windows)

```powershell
# Download Win-ACME
# https://www.win-acme.com/

# Esegui wacs.exe
# Segui wizard interattivo per ottenere certificato
```

**Opzione 2: Certificato Self-Signed** (solo sviluppo/test)

```bash
# Genera certificato self-signed
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout api.key \
  -out api.crt \
  -subj "/CN=api.tuodominio.com"

# Usa in Apache config:
SSLCertificateFile "C:/path/to/api.crt"
SSLCertificateKeyFile "C:/path/to/api.key"
```

---

## 🚀 Avvio Backend (Gunicorn)

### Linux

**Crea systemd service** (come in DEPLOY_PRODUZIONE.md):

```bash
sudo systemctl start datapizzarouge
sudo systemctl enable datapizzarouge
```

### Windows

**Opzione 1: NSSM** (Non-Sucking Service Manager)

```powershell
# Download NSSM
# https://nssm.cc/download

# Install as Windows Service
nssm install DataPizzaRouge "C:\Python313\python.exe" ^
  "-m" "gunicorn" "api:app" ^
  "-c" "gunicorn_config.py"

# Set working directory
nssm set DataPizzaRouge AppDirectory "D:\Almapro-tfs\Febo-Gemelli\datapizzarouge"

# Set environment file
nssm set DataPizzaRouge AppEnvironmentExtra :EnvironmentFile=.env

# Start service
nssm start DataPizzaRouge

# Stop service
nssm stop DataPizzaRouge

# Remove service
nssm remove DataPizzaRouge confirm
```

**Opzione 2: Script BAT con Task Scheduler**

**Crea `start_backend.bat`**:

```batch
@echo off
cd /d D:\Almapro-tfs\Febo-Gemelli\datapizzarouge

REM Verifica Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Python not found!
    exit /b 1
)

REM Avvia Gunicorn
python -m gunicorn api:app ^
  --workers 4 ^
  --worker-class uvicorn.workers.UvicornWorker ^
  --bind 127.0.0.1:8000 ^
  --timeout 120 ^
  --access-logfile logs\access.log ^
  --error-logfile logs\error.log
```

**Crea Task Scheduler**:
1. Apri "Task Scheduler"
2. Create Task → General:
   - Nome: "DataPizzaRouge API"
   - "Run whether user is logged on or not"
   - "Run with highest privileges"
3. Triggers → New:
   - Begin: "At startup"
4. Actions → New:
   - Action: "Start a program"
   - Program: `C:\Windows\System32\cmd.exe`
   - Arguments: `/c D:\Almapro-tfs\Febo-Gemelli\datapizzarouge\start_backend.bat`
5. Settings:
   - "Allow task to be run on demand"
   - "If task fails, restart every: 1 minute"

---

## ✅ Attivazione Configurazione

### Linux

```bash
# Abilita sito
sudo a2ensite datapizzarouge-api.conf

# Test configurazione
sudo apache2ctl configtest

# Restart Apache
sudo systemctl restart apache2

# Verifica status
sudo systemctl status apache2

# Verifica logs
sudo tail -f /var/log/apache2/datapizzarouge_error.log
```

### Windows

```bash
# Test configurazione
httpd.exe -t

# Restart Apache
# Da XAMPP Control Panel → Stop/Start Apache

# Verifica logs
notepad C:\xampp\apache\logs\error.log
```

---

## 🧪 Test Configurazione

### 1. Test Backend (Gunicorn)

```bash
# Verifica che Gunicorn sia in ascolto su porta 8000
curl http://127.0.0.1:8000/health

# Windows PowerShell
Invoke-WebRequest -Uri http://127.0.0.1:8000/health
```

**Output atteso**:
```json
{
  "status": "healthy",
  "qdrant_connected": true,
  "openai_configured": true,
  "anthropic_configured": true
}
```

### 2. Test Apache Proxy (HTTP)

```bash
curl http://api.tuodominio.com/health

# O se locale senza dominio
curl -H "Host: api.tuodominio.com" http://localhost/health
```

### 3. Test HTTPS

```bash
curl https://api.tuodominio.com/health

# Windows PowerShell
Invoke-RestMethod -Uri https://api.tuodominio.com/health
```

### 4. Test Query Completa

```bash
curl -X POST https://api.tuodominio.com/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "collection": "test_latest",
    "query": "test query",
    "top_k": 5
  }'
```

---

## 🔥 Firewall Configuration

### Linux (UFW)

```bash
# Abilita firewall
sudo ufw enable

# Permetti Apache
sudo ufw allow 'Apache Full'

# O manualmente
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# SSH (se remoto)
sudo ufw allow 22/tcp

# Verifica
sudo ufw status
```

### Windows (Firewall)

```powershell
# Permetti Apache in entrata
New-NetFirewallRule -DisplayName "Apache HTTP" -Direction Inbound -LocalPort 80 -Protocol TCP -Action Allow
New-NetFirewallRule -DisplayName "Apache HTTPS" -Direction Inbound -LocalPort 443 -Protocol TCP -Action Allow

# Verifica regole
Get-NetFirewallRule | Where-Object {$_.DisplayName -like "*Apache*"}
```

---

## ⚡ Performance Tuning Apache

### Moduli Performance

```bash
# Linux - Abilita MPM Event (più performante)
sudo a2dismod mpm_prefork
sudo a2enmod mpm_event

# Restart
sudo systemctl restart apache2
```

### Apache MPM Event Configuration

**Modifica `/etc/apache2/mods-available/mpm_event.conf`**:

```apache
<IfModule mpm_event_module>
    StartServers             2
    MinSpareThreads          25
    MaxSpareThreads          75
    ThreadLimit              64
    ThreadsPerChild          25
    MaxRequestWorkers        150
    MaxConnectionsPerChild   10000
    KeepAlive On
    KeepAliveTimeout 5
    MaxKeepAliveRequests 100
</IfModule>
```

### Compression (gzip)

```bash
# Abilita mod_deflate
sudo a2enmod deflate
```

**Aggiungi a VirtualHost**:

```apache
<IfModule mod_deflate.c>
    AddOutputFilterByType DEFLATE text/plain
    AddOutputFilterByType DEFLATE text/html
    AddOutputFilterByType DEFLATE text/xml
    AddOutputFilterByType DEFLATE text/css
    AddOutputFilterByType DEFLATE application/xml
    AddOutputFilterByType DEFLATE application/json
    AddOutputFilterByType DEFLATE application/javascript
</IfModule>
```

### Caching Headers

```apache
<IfModule mod_headers.c>
    # Cache statico (se hai file statici)
    <FilesMatch "\.(ico|jpg|jpeg|png|gif|css|js|woff|woff2)$">
        Header set Cache-Control "max-age=2592000, public"
    </FilesMatch>

    # No cache per API
    <Location /api>
        Header set Cache-Control "no-cache, no-store, must-revalidate"
        Header set Pragma "no-cache"
        Header set Expires 0
    </Location>
</IfModule>
```

---

## 📊 Monitoring e Logs

### Apache Logs

**Linux**:
```bash
# Access log
sudo tail -f /var/log/apache2/datapizzarouge_access.log

# Error log
sudo tail -f /var/log/apache2/datapizzarouge_error.log

# Tutte le richieste Apache
sudo tail -f /var/log/apache2/access.log
```

**Windows XAMPP**:
```bash
# Logs location
C:\xampp\apache\logs\access.log
C:\xampp\apache\logs\error.log

# View in real-time (PowerShell)
Get-Content C:\xampp\apache\logs\error.log -Wait -Tail 50
```

### Apache Status Module

```bash
# Abilita mod_status
sudo a2enmod status
```

**Aggiungi a config**:

```apache
<Location /server-status>
    SetHandler server-status
    Require ip 127.0.0.1
    # O per rete interna
    # Require ip 192.168.1.0/24
</Location>
```

**Accedi**:
```
http://localhost/server-status
```

---

## 🐛 Troubleshooting

### Errore: "503 Service Unavailable"

**Causa**: Apache non riesce a connettersi a Gunicorn (porta 8000)

**Soluzioni**:

```bash
# 1. Verifica Gunicorn sia in esecuzione
netstat -tlnp | grep 8000  # Linux
netstat -an | findstr 8000  # Windows

# 2. Test connessione diretta
curl http://127.0.0.1:8000/health

# 3. Verifica SELinux (Linux)
sudo setsebool -P httpd_can_network_connect 1

# 4. Verifica firewall locale non blocchi porta 8000
```

### Errore: "AH00959: ap_proxy_connect_backend disabling worker"

**Causa**: Timeout connessione

**Soluzione**:

```apache
# Aumenta timeout in VirtualHost
ProxyTimeout 300
Timeout 300
```

### Errore: "Invalid command 'ProxyPass'"

**Causa**: Modulo proxy non abilitato

**Soluzione**:

```bash
# Linux
sudo a2enmod proxy proxy_http
sudo systemctl restart apache2

# Windows - Verifica in httpd.conf
LoadModule proxy_module modules/mod_proxy.so
LoadModule proxy_http_module modules/mod_proxy_http.so
```

### Gunicorn non parte su Windows

**Causa**: Gunicorn usa fork() non supportato su Windows

**Soluzione**: Usa Waitress (alternativa Windows-friendly)

```bash
pip install waitress
```

**Crea `start_waitress.py`**:

```python
from waitress import serve
from api import app

if __name__ == "__main__":
    print("🚀 Starting Waitress server on http://127.0.0.1:8000")
    serve(
        app,
        host="127.0.0.1",
        port=8000,
        threads=8,  # Thread pool size
        channel_timeout=120,
        connection_limit=1000,
        cleanup_interval=30,
    )
```

**Avvia**:

```bash
python start_waitress.py
```

### CORS Issues

Se Blazor frontend ha errori CORS anche con Apache:

**Aggiungi a VirtualHost**:

```apache
# CORS Headers
Header always set Access-Control-Allow-Origin "https://tuo-blazor-app.com"
Header always set Access-Control-Allow-Methods "GET, POST, OPTIONS"
Header always set Access-Control-Allow-Headers "Content-Type, Authorization"
Header always set Access-Control-Max-Age "3600"

# Handle preflight OPTIONS
RewriteEngine On
RewriteCond %{REQUEST_METHOD} OPTIONS
RewriteRule ^(.*)$ $1 [R=200,L]
```

---

## 🔐 Security Hardening Apache

### Hide Apache Version

**Modifica `/etc/apache2/conf-enabled/security.conf` (Linux)**:

```apache
ServerTokens Prod
ServerSignature Off
```

**Windows `httpd.conf`**:

```apache
ServerTokens Prod
ServerSignature Off
```

### Disable Unnecessary Methods

```apache
<Location />
    <LimitExcept GET POST OPTIONS>
        Require all denied
    </LimitExcept>
</Location>
```

### Rate Limiting

```bash
# Abilita mod_evasive (DDoS protection)
sudo apt install libapache2-mod-evasive
sudo a2enmod evasive
```

**Config `/etc/apache2/mods-enabled/evasive.conf`**:

```apache
<IfModule mod_evasive20.c>
    DOSHashTableSize 3097
    DOSPageCount 10
    DOSSiteCount 100
    DOSPageInterval 1
    DOSSiteInterval 1
    DOSBlockingPeriod 60
</IfModule>
```

---

## 📋 Checklist Deploy Apache

- [ ] **Moduli proxy attivi** (proxy, proxy_http, ssl, headers)
- [ ] **VirtualHost configurato** (porta 80 e 443)
- [ ] **SSL/TLS attivo** (Let's Encrypt o certificato)
- [ ] **Gunicorn/Waitress in esecuzione** (porta 8000)
- [ ] **Firewall configurato** (80, 443 aperti)
- [ ] **Security headers** attivi
- [ ] **CORS configurato** (se serve per Blazor)
- [ ] **Logs funzionanti** (access + error)
- [ ] **Health check raggiungibile** (https://api.tuodominio.com/health)
- [ ] **Test query completo** (POST /api/query)

---

## 🎯 Setup Rapido Windows + Apache + XAMPP

### 1. Backend

```bash
# Installa Waitress
pip install waitress

# Crea start_waitress.py (vedi sopra)

# Test locale
python start_waitress.py
```

### 2. Apache Config

Aggiungi a `C:\xampp\apache\conf\extra\httpd-vhosts.conf`:

```apache
<VirtualHost *:80>
    ServerName localhost
    DocumentRoot "C:/xampp/htdocs"

    # API Proxy
    ProxyPreserveHost On
    ProxyPass /api http://127.0.0.1:8000
    ProxyPassReverse /api http://127.0.0.1:8000

    ErrorLog "logs/datapizzarouge_error.log"
    CustomLog "logs/datapizzarouge_access.log" common
</VirtualHost>
```

### 3. Test

```bash
# Avvia Waitress
python start_waitress.py

# Avvia Apache (XAMPP Control Panel)

# Test
curl http://localhost/api/health
```

**Fatto!** API raggiungibile su `http://localhost/api/` 🎉

---

## 📚 Risorse

- **Apache Docs**: https://httpd.apache.org/docs/
- **mod_proxy**: https://httpd.apache.org/docs/2.4/mod/mod_proxy.html
- **Let's Encrypt**: https://letsencrypt.org/
- **Win-ACME**: https://www.win-acme.com/
- **NSSM**: https://nssm.cc/
- **Waitress**: https://docs.pylonsproject.org/projects/waitress/

---

Ora Apache è configurato perfettamente per DataPizzaRouge! 🚀

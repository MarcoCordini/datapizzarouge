# Configurazione Apache per DataPizzaRouge API

Questa guida spiega come configurare Apache come reverse proxy per pubblicare l'API su:
**https://gemellidigitali.almapro.it/apirag**

## 📋 Prerequisiti

- Apache2 installato
- Sito `gemellidigitali.almapro.it` già configurato con HTTPS
- DataPizzaRouge service attivo su porta 8000

## 🔧 Step 1: Abilita moduli Apache necessari

```bash
sudo a2enmod proxy
sudo a2enmod proxy_http
sudo a2enmod proxy_wstunnel
sudo a2enmod headers
sudo a2enmod rewrite
```

## 🔧 Step 2: Trova il file di configurazione del VirtualHost

Individua il file di configurazione per `gemellidigitali.almapro.it`:

```bash
# Cerca il file
sudo grep -r "gemellidigitali.almapro.it" /etc/apache2/sites-enabled/
sudo grep -r "gemellidigitali.almapro.it" /etc/apache2/sites-available/
```

Probabilmente sarà in uno di questi:
- `/etc/apache2/sites-enabled/gemellidigitali.conf`
- `/etc/apache2/sites-enabled/000-default-le-ssl.conf` (se Let's Encrypt)
- `/etc/apache2/sites-available/gemellidigitali-ssl.conf`

## 🔧 Step 3: Modifica il VirtualHost

Apri il file del VirtualHost HTTPS (porta 443):

```bash
sudo nano /etc/apache2/sites-enabled/[nome-file].conf
```

**All'interno del blocco `<VirtualHost *:443>`**, aggiungi la configurazione per `/apirag`:

```apache
<VirtualHost *:443>
    ServerName gemellidigitali.almapro.it

    # ... altre configurazioni esistenti ...

    # === DataPizzaRouge API Reverse Proxy ===
    <Location /apirag>
        # Reverse proxy verso Gunicorn con timeout di 300 secondi
        ProxyPass http://127.0.0.1:8000 timeout=300
        ProxyPassReverse http://127.0.0.1:8000

        # Preserva headers per FastAPI
        ProxyPreserveHost On
        RequestHeader set X-Forwarded-Proto "https"
        RequestHeader set X-Forwarded-Prefix "/apirag"
    </Location>

    # ... resto della configurazione esistente ...
</VirtualHost>
```

### Opzione Alternativa: Include file esterno

Se preferisci mantenere la configurazione separata:

```apache
<VirtualHost *:443>
    ServerName gemellidigitali.almapro.it

    # ... altre configurazioni ...

    # Include DataPizzaRouge API config
    Include /home/administrator/rag_tools/datapizzarouge/apache-apirag.conf

    # ... resto della configurazione ...
</VirtualHost>
```

## 🔧 Step 4: Verifica la configurazione

```bash
# Test syntax
sudo apache2ctl configtest

# Dovrebbe restituire: Syntax OK
```

Se ci sono errori, correggili prima di procedere.

## 🔧 Step 5: Riavvia Apache

```bash
sudo systemctl restart apache2

# Verifica status
sudo systemctl status apache2
```

## 🔧 Step 6: Verifica il servizio DataPizzaRouge

Assicurati che il servizio sia attivo:

```bash
sudo systemctl status datapizzarouge

# Dovrebbe mostrare: Active: active (running)
```

## 🧪 Step 7: Test dell'API

### Test da riga di comando:

```bash
# Health check
curl https://gemellidigitali.almapro.it/apirag/health

# Root endpoint
curl https://gemellidigitali.almapro.it/apirag/

# Lista collections
curl https://gemellidigitali.almapro.it/apirag/api/collections
```

### Test dal browser:

Apri in un browser:
- **API Root**: https://gemellidigitali.almapro.it/apirag/
- **Documentazione interattiva**: https://gemellidigitali.almapro.it/apirag/docs
- **Health check**: https://gemellidigitali.almapro.it/apirag/health

## 📊 Monitoring e Log

### Log Apache:

```bash
# Access log
sudo tail -f /var/log/apache2/access.log

# Error log
sudo tail -f /var/log/apache2/error.log

# Filtra solo apirag
sudo tail -f /var/log/apache2/access.log | grep apirag
```

### Log Gunicorn (DataPizzaRouge):

```bash
# Via systemd
sudo journalctl -u datapizzarouge -f

# File log diretti
tail -f ~/rag_tools/datapizzarouge/logs/access.log
tail -f ~/rag_tools/datapizzarouge/logs/error.log
```

## 🔒 Security Considerations

### Rate Limiting (opzionale ma raccomandato):

Installa mod_evasive o mod_security per proteggere da abuse:

```bash
sudo apt-get install libapache2-mod-evasive
sudo a2enmod evasive
```

Configura in `/etc/apache2/mods-available/evasive.conf`:

```apache
<IfModule mod_evasive20.c>
    DOSHashTableSize 3097
    DOSPageCount 10
    DOSSiteCount 100
    DOSPageInterval 1
    DOSSiteInterval 1
    DOSBlockingPeriod 10
</IfModule>
```

### IP Whitelisting (se necessario):

Se vuoi limitare l'accesso solo da certi IP:

```apache
<Location /apirag>
    ProxyPass http://127.0.0.1:8000 timeout=300
    ProxyPassReverse http://127.0.0.1:8000
    ProxyPreserveHost On
    RequestHeader set X-Forwarded-Proto "https"
    RequestHeader set X-Forwarded-Prefix "/apirag"

    # Limita accesso
    Require ip 192.168.1.0/24
    Require ip 10.0.0.0/8
    # oppure per permettere a tutti
    # Require all granted
</Location>
```

## 🛠️ Troubleshooting

### Problema: 502 Bad Gateway

```bash
# Verifica che Gunicorn sia in esecuzione
sudo systemctl status datapizzarouge

# Verifica che la porta 8000 sia in ascolto
sudo netstat -tlnp | grep 8000
# oppure
sudo ss -tlnp | grep 8000

# Se non in ascolto, riavvia il service
sudo systemctl restart datapizzarouge
```

### Problema: 503 Service Unavailable

```bash
# Controlla i log di Gunicorn
sudo journalctl -u datapizzarouge -n 50

# Controlla errori Python
tail -n 50 ~/rag_tools/datapizzarouge/logs/error.log
```

### Problema: 404 Not Found

```bash
# Verifica che il path sia corretto
curl -v https://gemellidigitali.almapro.it/apirag/

# Controlla configurazione Apache
sudo apache2ctl -S

# Verifica che root_path sia configurato in api.py
grep "root_path" ~/rag_tools/datapizzarouge/api.py
```

### Problema: CORS errors

Se vedi errori CORS dal frontend Blazor:

1. Verifica che FastAPI abbia CORS abilitato (già configurato)
2. Controlla gli headers nelle Developer Tools del browser
3. Verifica che Apache non stia bloccando gli headers CORS

### Problema: Timeout su richieste lunghe

Se le query RAG vanno in timeout:

```apache
<Location /apirag>
    # Aumenta timeout (default 300s = 5 minuti, qui aumentato a 10 minuti)
    ProxyPass http://127.0.0.1:8000 timeout=600
    ProxyPassReverse http://127.0.0.1:8000
    ProxyPreserveHost On
    RequestHeader set X-Forwarded-Proto "https"
    RequestHeader set X-Forwarded-Prefix "/apirag"
</Location>
```

E in `gunicorn_config.py`:

```python
timeout = 600  # 10 minuti
```

## 🔄 Aggiornamenti

Dopo aver modificato il codice dell'API:

```bash
# 1. Pull modifiche
cd ~/rag_tools/datapizzarouge
git pull

# 2. Riavvia il service
sudo systemctl restart datapizzarouge

# 3. Non serve riavviare Apache (a meno di modifiche alla configurazione)

# 4. Verifica
curl https://gemellidigitali.almapro.it/apirag/health
```

## 📝 Configurazione Completa di Riferimento

Esempio di VirtualHost completo:

```apache
<VirtualHost *:443>
    ServerName gemellidigitali.almapro.it
    ServerAdmin admin@almapro.it

    # SSL Configuration (Let's Encrypt)
    SSLEngine on
    SSLCertificateFile /etc/letsencrypt/live/gemellidigitali.almapro.it/fullchain.pem
    SSLCertificateKeyFile /etc/letsencrypt/live/gemellidigitali.almapro.it/privkey.pem
    Include /etc/letsencrypt/options-ssl-apache.conf

    # Document Root (sito principale)
    DocumentRoot /var/www/gemellidigitali

    # DataPizzaRouge API Reverse Proxy
    <Location /apirag>
        ProxyPass http://127.0.0.1:8000 timeout=300
        ProxyPassReverse http://127.0.0.1:8000
        ProxyPreserveHost On
        RequestHeader set X-Forwarded-Proto "https"
        RequestHeader set X-Forwarded-Prefix "/apirag"
    </Location>

    # Log files
    ErrorLog ${APACHE_LOG_DIR}/gemellidigitali-error.log
    CustomLog ${APACHE_LOG_DIR}/gemellidigitali-access.log combined
</VirtualHost>
```

## ✅ Checklist Finale

- [ ] Moduli Apache abilitati (proxy, proxy_http, headers)
- [ ] Configurazione aggiunta al VirtualHost HTTPS
- [ ] Apache configuration test OK
- [ ] Apache riavviato
- [ ] DataPizzaRouge service attivo
- [ ] Health check funziona: `curl https://gemellidigitali.almapro.it/apirag/health`
- [ ] Docs accessibili: https://gemellidigitali.almapro.it/apirag/docs
- [ ] Test query funziona dal Blazor app

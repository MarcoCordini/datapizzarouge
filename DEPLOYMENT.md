# DataPizzaRouge - Guida al Deployment

## Setup Iniziale sul Server

### 1. Clona il repository
```bash
cd ~/rag_tools
git clone git@github.com:MarcoCordini/datapizzarouge.git
cd datapizzarouge
```

### 2. Installa dipendenze di sistema
```bash
sudo apt-get update
sudo apt-get install python3-dev libffi-dev libssl-dev build-essential python3-pip
```

### 3. Aggiungi ~/.local/bin al PATH permanentemente
```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### 4. Installa dipendenze Python (--user)
```bash
pip3 install --user --upgrade pip
pip3 install --user -r requirements.txt
```

### 5. Configura environment
```bash
cp .env.example .env
nano .env  # Modifica con le tue API keys
```

### 6. Setup iniziale
```bash
python cli.py setup
```

## Modalità di Esecuzione

### Sviluppo (con hot-reload)
```bash
./start_dev.sh
```
- Hot reload attivo
- Log dettagliati (debug)
- Singolo worker

### Produzione (Gunicorn + Uvicorn)
```bash
chmod +x start_production.sh
./start_production.sh
```
- Multiple workers (basato su CPU cores)
- Restart automatico workers
- Log in `logs/access.log` e `logs/error.log`
- Process manager robusto

## Deployment con Systemd (RACCOMANDATO per produzione)

### 1. Copia il service file
```bash
sudo cp datapizzarouge.service /etc/systemd/system/
```

### 2. Modifica i path nel service file se necessario
```bash
sudo nano /etc/systemd/system/datapizzarouge.service
# Verifica che User, WorkingDirectory e ExecStart siano corretti
```

### 3. Abilita e avvia il service
```bash
sudo systemctl daemon-reload
sudo systemctl enable datapizzarouge
sudo systemctl start datapizzarouge
```

### 4. Comandi utili
```bash
# Stato del servizio
sudo systemctl status datapizzarouge

# Visualizza logs
sudo journalctl -u datapizzarouge -f

# Riavvia il servizio
sudo systemctl restart datapizzarouge

# Stop del servizio
sudo systemctl stop datapizzarouge
```

## Configurazione Nginx (Reverse Proxy)

### 1. Installa Nginx
```bash
sudo apt-get install nginx
```

### 2. Configura il virtual host
```bash
sudo nano /etc/nginx/sites-available/datapizzarouge
```

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeout settings
        proxy_connect_timeout 120s;
        proxy_send_timeout 120s;
        proxy_read_timeout 120s;
    }
}
```

### 3. Abilita il sito
```bash
sudo ln -s /etc/nginx/sites-available/datapizzarouge /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 4. Opzionale: SSL con Let's Encrypt
```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

## Monitoraggio e Manutenzione

### Log Files
- Access log: `logs/access.log`
- Error log: `logs/error.log`
- System log: `sudo journalctl -u datapizzarouge`

### Rotazione log
```bash
sudo nano /etc/logrotate.d/datapizzarouge
```

```
/home/administrator/rag_tools/datapizzarouge/logs/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 administrator administrator
    sharedscripts
    postrotate
        systemctl reload datapizzarouge > /dev/null 2>&1 || true
    endscript
}
```

### Backup
```bash
# Backup database e configurazione
tar -czf backup-$(date +%Y%m%d).tar.gz .env data/ logs/
```

## Troubleshooting

### Problema: ModuleNotFoundError
```bash
export PATH="$HOME/.local/bin:$PATH"
pip3 install --user -r requirements.txt
```

### Problema: API Keys non configurate
```bash
nano .env
# Verifica che OPENAI_API_KEY e ANTHROPIC_API_KEY siano impostati
```

### Problema: Porta 8000 già in uso
```bash
# Trova il processo
sudo lsof -i :8000
# Termina il processo o cambia porta in gunicorn_config.py
```

### Problema: Permission denied su script .sh
```bash
chmod +x start_production.sh start_dev.sh
```

## Performance Tuning

### Workers ottimali
```python
# In gunicorn_config.py
workers = (2 * CPU_CORES) + 1
```

### Timeout per richieste lunghe
```python
# In gunicorn_config.py
timeout = 300  # 5 minuti per operazioni lunghe
```

### Memory limits
```bash
# Nel systemd service file
MemoryLimit=4G
```

## Aggiornamenti

```bash
cd ~/rag_tools/datapizzarouge
git pull origin main
pip3 install --user -r requirements.txt --upgrade
sudo systemctl restart datapizzarouge
```

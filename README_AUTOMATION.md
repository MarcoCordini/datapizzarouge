# Automazione Aggiornamenti RAG

Guida per configurare aggiornamenti automatici periodici del RAG.

## Windows - Task Scheduler

### 1. Configura lo script

Modifica `update_rag.ps1` con i tuoi parametri:

```powershell
$SITE_URL = "https://www.tuosito.com"          # URL da crawlare
$DOMAIN = "www.tuosito.com"                     # Dominio
$COLLECTION_NAME = "tuosito_latest"             # Nome collection fisso
$MAX_PAGES = 1000                               # Numero max pagine
```

### 2. Testa lo script manualmente

```powershell
cd D:\Almapro-tfs\Febo-Gemelli\datapizzarouge
.\update_rag.ps1
```

Verifica che funzioni senza errori.

### 3. Crea Task Scheduler

**Opzione A - GUI**:

1. Apri **Task Scheduler** (cerca "Utilità di pianificazione")
2. Click destro su "Libreria Utilità di pianificazione" → **Crea attività...**
3. **Generale**:
   - Nome: `Aggiorna RAG Settimanale`
   - Descrizione: `Aggiorna RAG crawling sito web`
   - Esegui indipendentemente dall'accesso dell'utente: ✓
   - Esegui con i privilegi più elevati: ✓

4. **Trigger**:
   - Click **Nuovo...**
   - Settimanale, ogni domenica alle 03:00
   - Ripeti ogni: 1 settimana

5. **Azioni**:
   - Click **Nuovo...**
   - Azione: `Avvio programma`
   - Programma: `powershell.exe`
   - Argomenti:
     ```
     -ExecutionPolicy Bypass -File "D:\Almapro-tfs\Febo-Gemelli\datapizzarouge\update_rag.ps1"
     ```
   - Inizio da: `D:\Almapro-tfs\Febo-Gemelli\datapizzarouge`

6. **Condizioni**:
   - Deseleziona "Avvia solo se il computer è alimentato da rete elettrica"
   - Seleziona "Riattiva il computer per eseguire l'attività" (se vuoi)

7. **Impostazioni**:
   - Seleziona "Consenti esecuzione attività su richiesta"
   - Se l'attività non riesce, riprova ogni: 10 minuti, per 3 volte

**Opzione B - PowerShell**:

```powershell
# Crea task automaticamente
$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-ExecutionPolicy Bypass -File `"D:\Almapro-tfs\Febo-Gemelli\datapizzarouge\update_rag.ps1`"" `
    -WorkingDirectory "D:\Almapro-tfs\Febo-Gemelli\datapizzarouge"

$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At 3am

$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

Register-ScheduledTask -TaskName "Aggiorna RAG Settimanale" `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "Aggiorna RAG crawling sito web settimanalmente" `
    -RunLevel Highest
```

### 4. Test esecuzione manuale

Nel Task Scheduler:
- Trova l'attività appena creata
- Click destro → **Esegui**
- Verifica che funzioni guardando i log in `update_rag.log`

### 5. Verifica automatica

Dopo la prima esecuzione automatica:
- Controlla `update_rag.log` per errori
- Verifica collection aggiornata: `python cli.py stats --collection tuosito_latest`

---

## Linux/macOS - Cron

### 1. Crea script bash

```bash
#!/bin/bash
# update_rag.sh

SITE_URL="https://www.tuosito.com"
DOMAIN="www.tuosito.com"
COLLECTION_NAME="tuosito_latest"
MAX_PAGES=1000

# Directory progetto
cd /path/to/datapizzarouge

# Log
LOG_FILE="update_rag.log"
echo "[$(date)] Inizio aggiornamento RAG" >> $LOG_FILE

# Crawl
echo "[$(date)] Crawling..." >> $LOG_FILE
python cli.py crawl $SITE_URL --max-pages $MAX_PAGES >> $LOG_FILE 2>&1

if [ $? -ne 0 ]; then
    echo "[$(date)] ERRORE durante crawling!" >> $LOG_FILE
    exit 1
fi

# Ingestion
echo "[$(date)] Ingestion..." >> $LOG_FILE
python cli.py ingest --domain $DOMAIN --collection $COLLECTION_NAME --force >> $LOG_FILE 2>&1

if [ $? -ne 0 ]; then
    echo "[$(date)] ERRORE durante ingestion!" >> $LOG_FILE
    exit 1
fi

echo "[$(date)] Completato!" >> $LOG_FILE
```

### 2. Rendi eseguibile

```bash
chmod +x update_rag.sh
```

### 3. Configura crontab

```bash
crontab -e
```

Aggiungi:
```bash
# Ogni domenica alle 3 AM
0 3 * * 0 /path/to/datapizzarouge/update_rag.sh

# Oppure ogni giorno alle 2 AM
0 2 * * * /path/to/datapizzarouge/update_rag.sh

# Ogni lunedì e venerdì alle 3 AM
0 3 * * 1,5 /path/to/datapizzarouge/update_rag.sh
```

### 4. Test

```bash
# Esegui manualmente
./update_rag.sh

# Controlla log
tail -f update_rag.log
```

---

## Docker (Avanzato)

Se vuoi eseguire tutto in Docker:

### 1. Dockerfile

```dockerfile
FROM python:3.13-slim

WORKDIR /app

# Installa dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia progetto
COPY . .

# Script di aggiornamento
CMD ["python", "cli.py", "crawl", "${SITE_URL}", "--max-pages", "${MAX_PAGES}"]
```

### 2. docker-compose.yml

```yaml
version: '3.8'

services:
  qdrant:
    image: qdrant/qdrant
    ports:
      - "6333:6333"
    volumes:
      - ./data/qdrant:/qdrant/storage

  rag-update:
    build: .
    environment:
      - SITE_URL=https://www.tuosito.com
      - DOMAIN=www.tuosito.com
      - COLLECTION_NAME=tuosito_latest
      - MAX_PAGES=1000
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - QDRANT_HOST=qdrant
    depends_on:
      - qdrant
    volumes:
      - ./data:/app/data
```

### 3. Esegui

```bash
docker-compose up rag-update
```

---

## Monitoraggio

### Log Files

Lo script crea `update_rag.log` con tutte le operazioni:

```bash
# Visualizza ultimi errori
grep "ERRORE" update_rag.log

# Visualizza ultime esecuzioni
grep "Completato" update_rag.log | tail -5
```

### Email Notifiche (Windows)

Aggiungi a `update_rag.ps1`:

```powershell
# Alla fine dello script
if ($LASTEXITCODE -eq 0) {
    Send-MailMessage -From "rag@tuosito.com" -To "admin@tuosito.com" `
        -Subject "RAG Update Success" -Body "Aggiornamento completato con successo" `
        -SmtpServer "smtp.gmail.com" -Port 587 -UseSsl `
        -Credential (Get-Credential)
}
```

---

## FAQ

**Q: Quanto tempo ci vuole?**
A: Dipende dalla dimensione del sito:
- Sito piccolo (10-50 pagine): 2-5 minuti
- Sito medio (100-500 pagine): 10-30 minuti
- Sito grande (1000+ pagine): 30-60 minuti

**Q: Quanto spazio occupa?**
A: Dipende dal contenuto:
- Raw data: ~100-500 KB per pagina
- Vector store: ~50-200 KB per pagina
- Esempio: 500 pagine = ~100-300 MB totali

**Q: Posso eseguire durante il giorno?**
A: Sì, ma considera:
- Usa orari di basso traffico (notte/mattina presto)
- Non impatta il sito crawlato (Scrapy è educato)
- Consuma risorse CPU durante ingestion

**Q: Cosa succede se fallisce?**
A: Lo script:
- Registra errore nel log
- Mantiene la collection precedente (con --force)
- Riprova alla prossima esecuzione pianificata

**Q: Come cancello collection vecchie?**
A:
```bash
# Lista tutte le collection
python cli.py list-collections

# Elimina collection specifica (manualmente)
# Dovrai usare Qdrant client direttamente
```

---

## Best Practices

1. **Test prima**: Esegui manualmente prima di automatizzare
2. **Backup**: Fai backup periodici della directory `data/`
3. **Monitoring**: Controlla i log regolarmente
4. **Notifiche**: Configura email/alerting per errori
5. **Frequenza**: Settimanale è spesso sufficiente per la maggior parte dei siti
6. **Orario**: Esegui in orari di basso traffico (2-4 AM)
7. **Risorse**: Assicurati che il PC sia acceso o usa cloud/server

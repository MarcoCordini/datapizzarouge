# Script PowerShell per aggiornamento periodico RAG
# Configura Task Scheduler per eseguirlo settimanalmente

# === CONFIGURAZIONE ===
$SITE_URL = "https://www.ruffino.it"
$DOMAIN = "www.ruffino.it"
$COLLECTION_NAME = "ruffino_latest"
$MAX_PAGES = 1000

# Directory del progetto (modifica se necessario)
$PROJECT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $PROJECT_DIR

# === LOG ===
$LOG_FILE = "update_rag.log"
$TIMESTAMP = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

Write-Host "[$TIMESTAMP] Inizio aggiornamento RAG per $SITE_URL" | Tee-Object -FilePath $LOG_FILE -Append

# === CRAWL ===
Write-Host "[$TIMESTAMP] 1. Crawling sito..." | Tee-Object -FilePath $LOG_FILE -Append
python cli.py crawl $SITE_URL --max-pages $MAX_PAGES

if ($LASTEXITCODE -ne 0) {
    Write-Host "[$TIMESTAMP] ERRORE durante crawling!" -ForegroundColor Red | Tee-Object -FilePath $LOG_FILE -Append
    exit 1
}

Write-Host "[$TIMESTAMP] Crawling completato!" -ForegroundColor Green | Tee-Object -FilePath $LOG_FILE -Append

# === INGESTION ===
Write-Host "[$TIMESTAMP] 2. Ingestion e creazione vector store..." | Tee-Object -FilePath $LOG_FILE -Append
python cli.py ingest --domain $DOMAIN --collection $COLLECTION_NAME --force

if ($LASTEXITCODE -ne 0) {
    Write-Host "[$TIMESTAMP] ERRORE durante ingestion!" -ForegroundColor Red | Tee-Object -FilePath $LOG_FILE -Append
    exit 1
}

Write-Host "[$TIMESTAMP] Ingestion completata!" -ForegroundColor Green | Tee-Object -FilePath $LOG_FILE -Append

# === CLEANUP (opzionale) ===
# Elimina file crawl raw più vecchi di 30 giorni per risparmiare spazio
Write-Host "[$TIMESTAMP] 3. Cleanup file vecchi..." | Tee-Object -FilePath $LOG_FILE -Append
$DAYS_TO_KEEP = 30
$RAW_DATA_PATH = Join-Path $PROJECT_DIR "data\raw\$DOMAIN"

if (Test-Path $RAW_DATA_PATH) {
    Get-ChildItem -Path $RAW_DATA_PATH -Recurse -File |
        Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-$DAYS_TO_KEEP) } |
        Remove-Item -Force
    Write-Host "[$TIMESTAMP] Cleanup completato!" -ForegroundColor Green | Tee-Object -FilePath $LOG_FILE -Append
}

# === FINE ===
$TIMESTAMP_END = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Write-Host "[$TIMESTAMP_END] Aggiornamento RAG completato con successo!" -ForegroundColor Green | Tee-Object -FilePath $LOG_FILE -Append
Write-Host ""
Write-Host "Collection aggiornata: $COLLECTION_NAME" -ForegroundColor Cyan
Write-Host "Usa questa collection nell'API o nella chat CLI." -ForegroundColor Cyan

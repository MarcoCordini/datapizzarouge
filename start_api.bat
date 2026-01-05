@echo off
REM Script per avviare l'API FastAPI su Windows

echo ========================================
echo DataPizzaRouge - Avvio API Server
echo ========================================
echo.

REM Verifica che Python sia disponibile
python --version >nul 2>&1
if errorlevel 1 (
    echo ERRORE: Python non trovato!
    echo Installa Python da https://www.python.org/
    pause
    exit /b 1
)

REM Verifica che siamo nella directory corretta
if not exist "api.py" (
    echo ERRORE: File api.py non trovato!
    echo Esegui questo script dalla directory datapizzarouge
    pause
    exit /b 1
)

REM Verifica che uvicorn sia installato
python -c "import uvicorn" >nul 2>&1
if errorlevel 1 (
    echo ERRORE: uvicorn non installato!
    echo Installa dependencies: pip install -r requirements.txt
    pause
    exit /b 1
)

echo Avvio server su http://localhost:8000
echo.
echo Documentazione API: http://localhost:8000/docs
echo Health Check: http://localhost:8000/health
echo.
echo Premi CTRL+C per fermare il server
echo ========================================
echo.

REM Avvia API con uvicorn
python -m uvicorn api:app --host 0.0.0.0 --port 8000 --reload

pause

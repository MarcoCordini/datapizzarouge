"""
Configurazione centralizzata per DataPizzaRouge.
Carica variabili d'ambiente da .env e fornisce valori di default.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Carica variabili d'ambiente da .env
load_dotenv()

# Directory base del progetto
BASE_DIR = Path(__file__).resolve().parent

# === API KEYS ===
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# === QDRANT CONFIGURATION ===
QDRANT_MODE = os.getenv("QDRANT_MODE", "local")  # "local" o "cloud"
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_URL = os.getenv("QDRANT_URL", None)  # Per modalità cloud
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", None)  # Per modalità cloud

# === CRAWLER SETTINGS ===
MAX_PAGES = int(os.getenv("MAX_PAGES", "1000"))
CONCURRENT_REQUESTS = int(os.getenv("CONCURRENT_REQUESTS", "16"))
DOWNLOAD_DELAY = float(os.getenv("DOWNLOAD_DELAY", "0.5"))
USER_AGENT = os.getenv("USER_AGENT", "DataPizzaRouge-Bot/1.0 (+https://github.com/datapizza-labs)")
DEPTH_LIMIT = int(os.getenv("DEPTH_LIMIT", "10"))

# === RAG SETTINGS ===
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))
TOP_K_RETRIEVAL = int(os.getenv("TOP_K_RETRIEVAL", "5"))

# === EMBEDDING SETTINGS ===
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_DIMENSIONS = int(os.getenv("EMBEDDING_DIMENSIONS", "1536"))
EMBEDDING_BATCH_SIZE = int(os.getenv("EMBEDDING_BATCH_SIZE", "100"))

# === LLM SETTINGS ===
LLM_MODEL = os.getenv("LLM_MODEL", "claude-sonnet-4-5-20250929")
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "4096"))
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))

# === STORAGE PATHS ===
RAW_DATA_PATH = Path(os.getenv("RAW_DATA_PATH", BASE_DIR / "data" / "raw"))
QDRANT_DATA_PATH = Path(os.getenv("QDRANT_DATA_PATH", BASE_DIR / "data" / "qdrant"))

# Crea le directory se non esistono
RAW_DATA_PATH.mkdir(parents=True, exist_ok=True)
QDRANT_DATA_PATH.mkdir(parents=True, exist_ok=True)

# === LOGGING SETTINGS ===
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "datapizzarouge.log")


def validate_config():
    """Valida che le configurazioni critiche siano presenti."""
    errors = []

    if not OPENAI_API_KEY:
        errors.append("OPENAI_API_KEY non configurata")

    if not ANTHROPIC_API_KEY:
        errors.append("ANTHROPIC_API_KEY non configurata")

    if QDRANT_MODE == "cloud":
        if not QDRANT_URL:
            errors.append("QDRANT_URL richiesto per modalità cloud")
        if not QDRANT_API_KEY:
            errors.append("QDRANT_API_KEY richiesto per modalità cloud")

    if errors:
        raise ValueError(
            "Configurazione non valida:\n" + "\n".join(f"  - {e}" for e in errors)
        )

    return True


if __name__ == "__main__":
    # Test configurazione
    print("=== Configurazione DataPizzaRouge ===")
    print(f"OPENAI_API_KEY: {'✓' if OPENAI_API_KEY else '✗'}")
    print(f"ANTHROPIC_API_KEY: {'✓' if ANTHROPIC_API_KEY else '✗'}")
    print(f"QDRANT_MODE: {QDRANT_MODE}")
    print(f"QDRANT_HOST: {QDRANT_HOST}:{QDRANT_PORT}")
    print(f"MAX_PAGES: {MAX_PAGES}")
    print(f"CHUNK_SIZE: {CHUNK_SIZE}")
    print(f"EMBEDDING_MODEL: {EMBEDDING_MODEL}")
    print(f"LLM_MODEL: {LLM_MODEL}")
    print(f"RAW_DATA_PATH: {RAW_DATA_PATH}")
    print(f"QDRANT_DATA_PATH: {QDRANT_DATA_PATH}")

    try:
        validate_config()
        print("\n✓ Configurazione valida!")
    except ValueError as e:
        print(f"\n✗ {e}")

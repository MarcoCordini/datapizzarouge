"""
API REST FastAPI per DataPizzaRouge RAG.
Espone endpoint per query, gestione collection e statistiche.

Avvio:
    uvicorn api:app --host 0.0.0.0 --port 8000 --reload

Documentazione automatica:
    http://localhost:8000/docs
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import config
from storage.vector_store_manager import VectorStoreManager
from storage.raw_data_store import RawDataStore
from rag.retrieval_pipeline import RetrievalPipeline
from rag.chat_interface import ChatInterface

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="DataPizzaRouge API",
    description="API REST per RAG (Retrieval-Augmented Generation) su contenuti web crawlati",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS - permetti chiamate da Blazor
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In produzione: specifica domini Blazor
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# === MODELS (Request/Response) ===


class QueryRequest(BaseModel):
    """Richiesta di query RAG."""

    collection: str = Field(..., description="Nome della collection Qdrant")
    query: str = Field(..., description="Domanda dell'utente", min_length=1)
    top_k: int = Field(5, description="Numero di risultati da recuperare", ge=1, le=20)
    include_sources: bool = Field(True, description="Include fonti nella risposta")
    include_history: bool = Field(
        False, description="Include cronologia conversazione"
    )


class QueryResponse(BaseModel):
    """Risposta a query RAG."""

    answer: str = Field(..., description="Risposta generata da Claude")
    sources: Optional[str] = Field(None, description="Fonti formattate")
    num_results: int = Field(..., description="Numero documenti recuperati")
    tokens_used: Optional[int] = Field(None, description="Token utilizzati")
    timestamp: str = Field(..., description="Timestamp della risposta")


class RetrievalResult(BaseModel):
    """Risultato singolo di retrieval."""

    id: Any = Field(..., description="ID del chunk")
    score: float = Field(..., description="Score di similarità")
    text: str = Field(..., description="Testo del chunk")
    url: str = Field(..., description="URL della pagina sorgente")
    page_title: str = Field(..., description="Titolo della pagina")
    chunk_index: int = Field(..., description="Indice chunk nella pagina")


class RetrievalRequest(BaseModel):
    """Richiesta di retrieval (solo documenti, senza generazione)."""

    collection: str = Field(..., description="Nome della collection")
    query: str = Field(..., description="Query di ricerca")
    top_k: int = Field(5, description="Numero di risultati", ge=1, le=20)
    score_threshold: Optional[float] = Field(
        None, description="Soglia minima di score", ge=0.0, le=1.0
    )


class CollectionInfo(BaseModel):
    """Informazioni su una collection."""

    name: str
    points_count: int
    vector_size: int
    distance: str
    status: str


class CollectionStats(BaseModel):
    """Statistiche dettagliate collection."""

    name: str
    points_count: int
    vector_size: int
    distance: str
    status: str
    created_at: Optional[str] = None


class DomainInfo(BaseModel):
    """Informazioni su un dominio crawlato."""

    domain: str
    page_count: int
    total_size_mb: float
    first_crawl: Optional[str]
    last_crawl: Optional[str]


class HealthResponse(BaseModel):
    """Risposta health check."""

    status: str
    qdrant_connected: bool
    openai_configured: bool
    anthropic_configured: bool
    timestamp: str


# === ENDPOINTS ===


@app.get("/", tags=["General"])
async def root():
    """Root endpoint - Info API."""
    return {
        "name": "DataPizzaRouge API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", response_model=HealthResponse, tags=["General"])
async def health_check():
    """Health check - verifica stato servizi."""
    try:
        # Test Qdrant connection
        vector_store = VectorStoreManager()
        collections = vector_store.list_collections()
        qdrant_ok = True
    except Exception as e:
        logger.error(f"Qdrant connection failed: {e}")
        qdrant_ok = False

    return HealthResponse(
        status="healthy" if qdrant_ok else "degraded",
        qdrant_connected=qdrant_ok,
        openai_configured=bool(config.OPENAI_API_KEY),
        anthropic_configured=bool(config.ANTHROPIC_API_KEY),
        timestamp=datetime.utcnow().isoformat(),
    )


@app.post("/api/query", response_model=QueryResponse, tags=["RAG"])
async def query_rag(request: QueryRequest):
    """
    Esegue query RAG: retrieval + generazione risposta con Claude.

    Questo è l'endpoint principale per chat/Q&A.
    """
    try:
        logger.info(f"Query RAG: collection={request.collection}, query={request.query[:50]}...")

        # Verifica collection esiste
        vector_store = VectorStoreManager()
        if request.collection not in vector_store.list_collections():
            raise HTTPException(
                status_code=404, detail=f"Collection '{request.collection}' non trovata"
            )

        # Crea chat interface
        chat = ChatInterface(
            collection_name=request.collection,
            top_k_retrieval=request.top_k,
        )

        # Esegui query
        result = chat.chat(
            user_message=request.query, include_history=request.include_history
        )

        return QueryResponse(
            answer=result["response"],
            sources=result["sources"] if request.include_sources else None,
            num_results=result["num_results"],
            tokens_used=result.get("tokens_used"),
            timestamp=datetime.utcnow().isoformat(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Errore durante query: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Errore interno: {str(e)}")


@app.post("/api/retrieval", response_model=List[RetrievalResult], tags=["RAG"])
async def retrieval_only(request: RetrievalRequest):
    """
    Esegue solo retrieval documenti (senza generazione risposta).

    Utile per:
    - Preview documenti rilevanti
    - Debug retrieval
    - Implementazioni custom
    """
    try:
        logger.info(
            f"Retrieval: collection={request.collection}, query={request.query[:50]}..."
        )

        # Verifica collection
        vector_store = VectorStoreManager()
        if request.collection not in vector_store.list_collections():
            raise HTTPException(
                status_code=404, detail=f"Collection '{request.collection}' non trovata"
            )

        # Retrieval
        pipeline = RetrievalPipeline(
            collection_name=request.collection, top_k=request.top_k
        )

        results = pipeline.retrieve(
            query=request.query, score_threshold=request.score_threshold
        )

        return [
            RetrievalResult(
                id=r["id"],
                score=r["score"],
                text=r["text"],
                url=r["url"],
                page_title=r["page_title"],
                chunk_index=r["chunk_index"],
            )
            for r in results
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Errore durante retrieval: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Errore interno: {str(e)}")


@app.get("/api/collections", response_model=List[str], tags=["Collections"])
async def list_collections():
    """Lista tutte le collection disponibili."""
    try:
        vector_store = VectorStoreManager()
        collections = vector_store.list_collections()
        return collections
    except Exception as e:
        logger.error(f"Errore listando collection: {e}")
        raise HTTPException(status_code=500, detail=f"Errore interno: {str(e)}")


@app.get(
    "/api/collections/{collection_name}",
    response_model=CollectionInfo,
    tags=["Collections"],
)
async def get_collection_info(collection_name: str):
    """Ottiene informazioni su una collection specifica."""
    try:
        vector_store = VectorStoreManager()

        if collection_name not in vector_store.list_collections():
            raise HTTPException(
                status_code=404, detail=f"Collection '{collection_name}' non trovata"
            )

        info = vector_store.get_collection_info(collection_name)

        if not info:
            raise HTTPException(
                status_code=500, detail="Errore recuperando info collection"
            )

        return CollectionInfo(**info)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Errore ottenendo info collection: {e}")
        raise HTTPException(status_code=500, detail=f"Errore interno: {str(e)}")


@app.get("/api/domains", response_model=List[str], tags=["Domains"])
async def list_domains():
    """Lista tutti i domini crawlati disponibili."""
    try:
        raw_store = RawDataStore()
        domains = raw_store.list_domains()
        return domains
    except Exception as e:
        logger.error(f"Errore listando domini: {e}")
        raise HTTPException(status_code=500, detail=f"Errore interno: {str(e)}")


@app.get("/api/domains/{domain}", response_model=DomainInfo, tags=["Domains"])
async def get_domain_info(domain: str):
    """Ottiene informazioni su un dominio crawlato."""
    try:
        raw_store = RawDataStore()

        if domain not in raw_store.list_domains():
            raise HTTPException(status_code=404, detail=f"Dominio '{domain}' non trovato")

        stats = raw_store.get_domain_stats(domain)
        return DomainInfo(**stats)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Errore ottenendo info dominio: {e}")
        raise HTTPException(status_code=500, detail=f"Errore interno: {str(e)}")


# === STARTUP/SHUTDOWN ===


@app.on_event("startup")
async def startup_event():
    """Eseguito all'avvio del server."""
    logger.info("=" * 60)
    logger.info("DataPizzaRouge API - Avvio")
    logger.info("=" * 60)
    logger.info(f"OpenAI API Key: {'✓' if config.OPENAI_API_KEY else '✗'}")
    logger.info(f"Anthropic API Key: {'✓' if config.ANTHROPIC_API_KEY else '✗'}")
    logger.info(f"Qdrant: {config.QDRANT_HOST}:{config.QDRANT_PORT}")

    # Test Qdrant connection
    try:
        vector_store = VectorStoreManager()
        collections = vector_store.list_collections()
        logger.info(f"✓ Connesso a Qdrant - {len(collections)} collection disponibili")
    except Exception as e:
        logger.error(f"✗ Errore connessione Qdrant: {e}")

    logger.info("=" * 60)
    logger.info("API pronta su http://localhost:8000")
    logger.info("Documentazione: http://localhost:8000/docs")
    logger.info("=" * 60)


@app.on_event("shutdown")
async def shutdown_event():
    """Eseguito allo shutdown del server."""
    logger.info("DataPizzaRouge API - Shutdown")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )

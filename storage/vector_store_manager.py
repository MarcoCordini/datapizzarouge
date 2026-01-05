"""
Modulo per gestione del vector store Qdrant.
Usa datapizza-ai-vectorstores-qdrant per operazioni su Qdrant.
"""
import logging
from typing import List, Dict, Optional
from datetime import datetime

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from qdrant_client.models import Filter, FieldCondition, MatchValue

import config

logger = logging.getLogger(__name__)


class VectorStoreManager:
    """
    Gestisce operazioni sul vector store Qdrant.
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        url: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        """
        Inizializza VectorStoreManager.

        Args:
            host: Host Qdrant (default: config.QDRANT_HOST)
            port: Port Qdrant (default: config.QDRANT_PORT)
            url: URL Qdrant cloud (opzionale)
            api_key: API key Qdrant cloud (opzionale)
        """
        self.host = host or config.QDRANT_HOST
        self.port = port or config.QDRANT_PORT
        self.url = url or config.QDRANT_URL
        self.api_key = api_key or config.QDRANT_API_KEY

        # Crea client Qdrant
        if config.QDRANT_MODE == "cloud" and self.url:
            logger.info(f"Connessione a Qdrant cloud: {self.url}")
            self.client = QdrantClient(url=self.url, api_key=self.api_key)
        else:
            logger.info(f"Connessione a Qdrant locale: {self.host}:{self.port}")
            self.client = QdrantClient(host=self.host, port=self.port)

        # Test connessione
        try:
            self.client.get_collections()
            logger.info("Connessione a Qdrant riuscita")
        except Exception as e:
            logger.error(f"Errore connessione a Qdrant: {e}")
            raise

    def create_collection(
        self,
        collection_name: str,
        vector_size: int = 1536,
        distance: Distance = Distance.COSINE,
        force_recreate: bool = False,
    ) -> bool:
        """
        Crea una collection Qdrant.

        Args:
            collection_name: Nome della collection
            vector_size: Dimensione dei vettori
            distance: Metrica di distanza
            force_recreate: Se True, elimina collection esistente

        Returns:
            True se creato con successo
        """
        try:
            # Controlla se collection esiste
            collections = self.client.get_collections().collections
            exists = any(c.name == collection_name for c in collections)

            if exists:
                if force_recreate:
                    logger.info(f"Eliminazione collection esistente: {collection_name}")
                    self.client.delete_collection(collection_name)
                else:
                    logger.info(f"Collection già esistente: {collection_name}")
                    return True

            # Crea collection
            logger.info(f"Creazione collection: {collection_name}")
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=vector_size, distance=distance),
            )

            logger.info(f"Collection creata: {collection_name}")
            return True

        except Exception as e:
            logger.error(f"Errore creando collection {collection_name}: {e}")
            return False

    def insert_chunks(
        self,
        collection_name: str,
        chunks: List[Dict],
        embeddings: List[List[float]],
        batch_size: int = 100,
    ) -> int:
        """
        Inserisce chunk con embeddings in Qdrant.

        Args:
            collection_name: Nome della collection
            chunks: Lista di chunk (dict con text e metadata)
            embeddings: Lista di embedding vectors
            batch_size: Dimensione batch per insert

        Returns:
            Numero di chunk inseriti
        """
        if len(chunks) != len(embeddings):
            raise ValueError("chunks e embeddings devono avere stessa lunghezza")

        try:
            total_inserted = 0

            # Inserisci in batch
            for i in range(0, len(chunks), batch_size):
                batch_chunks = chunks[i : i + batch_size]
                batch_embeddings = embeddings[i : i + batch_size]

                # Crea points per Qdrant
                points = []
                for j, (chunk, embedding) in enumerate(
                    zip(batch_chunks, batch_embeddings)
                ):
                    point_id = i + j

                    # Prepara payload (metadata)
                    payload = {
                        "text": chunk.get("text", ""),
                        "url": chunk.get("url", ""),
                        "page_title": chunk.get("page_title", ""),
                        "chunk_index": chunk.get("chunk_index", 0),
                        "total_chunks": chunk.get("total_chunks", 0),
                        "char_count": chunk.get("char_count", 0),
                        "word_count": chunk.get("word_count", 0),
                    }

                    # Aggiungi metadata extra se presenti
                    if "crawled_at" in chunk:
                        payload["crawled_at"] = chunk["crawled_at"]
                    if "domain" in chunk:
                        payload["domain"] = chunk["domain"]

                    point = PointStruct(id=point_id, vector=embedding, payload=payload)
                    points.append(point)

                # Inserisci batch
                self.client.upsert(collection_name=collection_name, points=points)

                total_inserted += len(points)

                if total_inserted % 500 == 0:
                    logger.info(f"Inseriti {total_inserted}/{len(chunks)} chunk")

            logger.info(
                f"Inserimento completato: {total_inserted} chunk in {collection_name}"
            )
            return total_inserted

        except Exception as e:
            logger.error(f"Errore inserendo chunk: {e}")
            raise

    def search(
        self,
        collection_name: str,
        query_vector: List[float],
        limit: int = 5,
        score_threshold: Optional[float] = None,
        filter_dict: Optional[Dict] = None,
    ) -> List[Dict]:
        """
        Cerca chunk simili usando vector similarity.

        Args:
            collection_name: Nome della collection
            query_vector: Vector della query
            limit: Numero massimo di risultati
            score_threshold: Soglia minima di score (opzionale)
            filter_dict: Filtri sui metadata (opzionale)

        Returns:
            Lista di risultati con score e payload
        """
        try:
            # Prepara filter se presente
            query_filter = None
            if filter_dict:
                # Esempio: {"domain": "example.com"}
                conditions = []
                for key, value in filter_dict.items():
                    conditions.append(
                        FieldCondition(key=key, match=MatchValue(value=value))
                    )
                if conditions:
                    query_filter = Filter(must=conditions)

            # Esegui search usando l'API corretta di Qdrant
            results = self.client.query_points(
                collection_name=collection_name,
                query=query_vector,
                limit=limit,
                score_threshold=score_threshold,
                query_filter=query_filter,
            ).points

            # Formatta risultati
            formatted_results = []
            for result in results:
                # result è un ScoredPoint
                formatted_results.append(
                    {
                        "id": result.id,
                        "score": result.score,
                        "text": result.payload.get("text", ""),
                        "url": result.payload.get("url", ""),
                        "page_title": result.payload.get("page_title", ""),
                        "chunk_index": result.payload.get("chunk_index", 0),
                        "metadata": result.payload,
                    }
                )

            return formatted_results

        except Exception as e:
            logger.error(f"Errore durante search: {e}")
            raise

    def list_collections(self) -> List[str]:
        """
        Lista tutte le collection.

        Returns:
            Lista di nomi collection
        """
        try:
            collections = self.client.get_collections().collections
            return [c.name for c in collections]
        except Exception as e:
            logger.error(f"Errore listando collection: {e}")
            return []

    def get_collection_info(self, collection_name: str) -> Optional[Dict]:
        """
        Ottiene informazioni su una collection.

        Args:
            collection_name: Nome della collection

        Returns:
            Dict con info, o None se non trovata
        """
        try:
            info = self.client.get_collection(collection_name)

            return {
                "name": collection_name,
                "points_count": info.points_count,
                "status": info.status,
                "vector_size": info.config.params.vectors.size,
                "distance": info.config.params.vectors.distance.name,
            }

        except Exception as e:
            logger.error(f"Errore ottenendo info collection {collection_name}: {e}")
            return None

    def delete_collection(self, collection_name: str) -> bool:
        """
        Elimina una collection.

        Args:
            collection_name: Nome della collection

        Returns:
            True se eliminato con successo
        """
        try:
            self.client.delete_collection(collection_name)
            logger.info(f"Collection eliminata: {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Errore eliminando collection {collection_name}: {e}")
            return False

    def generate_collection_name(self, domain: str) -> str:
        """
        Genera un nome univoco per collection basato su dominio e timestamp.

        Args:
            domain: Nome del dominio

        Returns:
            Nome collection
        """
        # Pulisci domain per nome collection valido
        clean_domain = domain.replace(".", "_").replace("-", "_")

        # Aggiungi timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        return f"crawl_{clean_domain}_{timestamp}"


def get_manager(
    host: Optional[str] = None,
    port: Optional[int] = None,
    url: Optional[str] = None,
    api_key: Optional[str] = None,
) -> VectorStoreManager:
    """
    Factory function per creare VectorStoreManager.

    Args:
        host: Host Qdrant
        port: Port Qdrant
        url: URL Qdrant cloud
        api_key: API key Qdrant cloud

    Returns:
        VectorStoreManager instance
    """
    return VectorStoreManager(host=host, port=port, url=url, api_key=api_key)


if __name__ == "__main__":
    # Test VectorStoreManager
    import sys

    logging.basicConfig(level=logging.INFO)

    try:
        manager = get_manager()

        print("=== Test Vector Store Manager ===")
        print(f"Modalità: {config.QDRANT_MODE}")
        print(f"Host: {manager.host}:{manager.port}")

        # Lista collection
        collections = manager.list_collections()
        print(f"\nCollection esistenti: {len(collections)}")
        for coll in collections:
            info = manager.get_collection_info(coll)
            if info:
                print(f"  - {coll}: {info['points_count']} points")

    except Exception as e:
        print(f"Errore: {e}")
        print("\nAssicurati che Qdrant sia in esecuzione:")
        print("  docker run -p 6333:6333 qdrant/qdrant")

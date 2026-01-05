"""
Pipeline di retrieval per query su vector store.
Gestisce: query → embedding → vector search → context formatting.
"""
import logging
from typing import List, Dict, Optional

from openai import OpenAI

import config
from storage.vector_store_manager import VectorStoreManager

logger = logging.getLogger(__name__)


class RetrievalPipeline:
    """
    Pipeline per retrieval di context rilevante da vector store.
    """

    def __init__(
        self,
        collection_name: str,
        openai_api_key: Optional[str] = None,
        embedding_model: Optional[str] = None,
        top_k: Optional[int] = None,
    ):
        """
        Inizializza RetrievalPipeline.

        Args:
            collection_name: Nome della collection Qdrant
            openai_api_key: API key OpenAI (default: config)
            embedding_model: Modello embedding (default: config)
            top_k: Numero di risultati da recuperare (default: config)
        """
        self.collection_name = collection_name
        self.openai_api_key = openai_api_key or config.OPENAI_API_KEY
        self.embedding_model = embedding_model or config.EMBEDDING_MODEL
        self.top_k = top_k or config.TOP_K_RETRIEVAL

        # Inizializza componenti
        self.vector_store = VectorStoreManager()
        self.openai_client = OpenAI(api_key=self.openai_api_key)

        # Verifica collection esiste
        if collection_name not in self.vector_store.list_collections():
            raise ValueError(f"Collection non trovata: {collection_name}")

        logger.info(f"RetrievalPipeline inizializzata per collection: {collection_name}")
        logger.info(f"  Top-K: {self.top_k}")
        logger.info(f"  Embedding model: {self.embedding_model}")

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        score_threshold: Optional[float] = None,
        filter_dict: Optional[Dict] = None,
    ) -> List[Dict]:
        """
        Recupera chunk rilevanti per una query.

        Args:
            query: Query dell'utente
            top_k: Numero di risultati (default: self.top_k)
            score_threshold: Soglia minima di similarità (opzionale)
            filter_dict: Filtri sui metadata (opzionale)

        Returns:
            Lista di chunk rilevanti con score
        """
        if not query or not query.strip():
            logger.warning("Query vuota")
            return []

        top_k = top_k or self.top_k

        try:
            # Genera embedding per query
            query_embedding = self._generate_query_embedding(query)

            # Search nel vector store
            results = self.vector_store.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=top_k,
                score_threshold=score_threshold,
                filter_dict=filter_dict,
            )

            logger.info(f"Trovati {len(results)} risultati per query: {query[:50]}...")

            return results

        except Exception as e:
            logger.error(f"Errore durante retrieval: {e}")
            raise

    def _generate_query_embedding(self, query: str) -> List[float]:
        """
        Genera embedding per query.

        Args:
            query: Testo della query

        Returns:
            Embedding vector
        """
        try:
            response = self.openai_client.embeddings.create(
                model=self.embedding_model, input=[query]
            )

            embedding = response.data[0].embedding
            return embedding

        except Exception as e:
            logger.error(f"Errore generando embedding per query: {e}")
            raise

    def format_context(
        self,
        results: List[Dict],
        include_metadata: bool = True,
        max_context_length: Optional[int] = None,
    ) -> str:
        """
        Formatta risultati di retrieval come context per LLM.

        Args:
            results: Risultati di retrieval
            include_metadata: Se True, include metadata (URL, titolo)
            max_context_length: Lunghezza massima context (opzionale)

        Returns:
            Context formattato come stringa
        """
        if not results:
            return "Nessun contesto rilevante trovato."

        context_parts = []

        for i, result in enumerate(results, 1):
            part = f"[Documento {i}]"

            if include_metadata:
                url = result.get("url", "")
                title = result.get("page_title", "")

                if title:
                    part += f"\nTitolo: {title}"
                if url:
                    part += f"\nURL: {url}"

                score = result.get("score", 0)
                part += f"\nRilevanza: {score:.3f}"

            part += f"\n\n{result['text']}\n"
            context_parts.append(part)

        context = "\n---\n".join(context_parts)

        # Limita lunghezza se richiesto
        if max_context_length and len(context) > max_context_length:
            context = context[:max_context_length] + "\n\n[Context troncato...]"

        return context

    def format_sources(self, results: List[Dict]) -> str:
        """
        Formatta fonti per citazioni.

        Args:
            results: Risultati di retrieval

        Returns:
            Stringa con fonti formattate
        """
        if not results:
            return "Nessuna fonte disponibile."

        sources = []
        seen_urls = set()

        for result in results:
            url = result.get("url", "")
            if url and url not in seen_urls:
                title = result.get("page_title", url)
                sources.append(f"- {title}\n  {url}")
                seen_urls.add(url)

        return "\n".join(sources)

    def get_collection_info(self) -> Dict:
        """
        Ottiene informazioni sulla collection.

        Returns:
            Dict con info collection
        """
        return self.vector_store.get_collection_info(self.collection_name)


def create_retrieval_pipeline(
    collection_name: str,
    openai_api_key: Optional[str] = None,
    top_k: Optional[int] = None,
) -> RetrievalPipeline:
    """
    Factory function per creare RetrievalPipeline.

    Args:
        collection_name: Nome collection
        openai_api_key: API key OpenAI
        top_k: Top-K risultati

    Returns:
        RetrievalPipeline instance
    """
    return RetrievalPipeline(
        collection_name=collection_name,
        openai_api_key=openai_api_key,
        top_k=top_k,
    )


if __name__ == "__main__":
    # Test RetrievalPipeline
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Lista collection disponibili
    vector_store = VectorStoreManager()
    collections = vector_store.list_collections()

    print("=== Test Retrieval Pipeline ===")
    print(f"\nCollection disponibili:")
    for i, coll in enumerate(collections, 1):
        info = vector_store.get_collection_info(coll)
        if info:
            print(f"{i}. {coll} ({info['points_count']} punti)")

    if not collections:
        print("Nessuna collection trovata. Esegui prima l'ingestion.")
        sys.exit(1)

    # Seleziona collection
    try:
        choice = input("\nSeleziona collection (numero o nome): ")
        if choice.isdigit():
            collection_name = collections[int(choice) - 1]
        else:
            collection_name = choice

        # Crea pipeline
        pipeline = create_retrieval_pipeline(collection_name)

        print(f"\nPipeline creata per: {collection_name}")

        # Info collection
        info = pipeline.get_collection_info()
        print(f"Punti nella collection: {info['points_count']}")

        # Test query
        while True:
            query = input("\nQuery (o 'quit'): ")
            if query.lower() in ["quit", "exit", "q"]:
                break

            results = pipeline.retrieve(query)

            print(f"\n=== Risultati ({len(results)}) ===")
            for i, result in enumerate(results, 1):
                print(f"\n{i}. Score: {result['score']:.3f}")
                print(f"   URL: {result['url']}")
                print(f"   Text: {result['text'][:200]}...")

            print("\n=== Context Formattato ===")
            context = pipeline.format_context(results, max_context_length=1000)
            print(context)

            print("\n=== Fonti ===")
            sources = pipeline.format_sources(results)
            print(sources)

    except Exception as e:
        print(f"Errore: {e}")
        import traceback

        traceback.print_exc()

"""
Pipeline di ingestion per processare dati crawlati e popolare vector store.
Orchestra: raw data → cleaning → chunking → embedding → vector store.
"""
import logging
from typing import List, Dict, Optional
from tqdm import tqdm

from openai import OpenAI

import config
from storage.raw_data_store import RawDataStore
from storage.vector_store_manager import VectorStoreManager
from processors.html_cleaner import HTMLCleaner
from processors.content_chunker import ContentChunker

logger = logging.getLogger(__name__)


class IngestionPipeline:
    """
    Pipeline completa per ingestion di dati crawlati nel vector store.
    """

    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        embedding_model: Optional[str] = None,
    ):
        """
        Inizializza IngestionPipeline.

        Args:
            openai_api_key: API key OpenAI (default: config)
            chunk_size: Dimensione chunk (default: config)
            chunk_overlap: Overlap chunk (default: config)
            embedding_model: Modello embedding (default: config)
        """
        self.openai_api_key = openai_api_key or config.OPENAI_API_KEY
        self.chunk_size = chunk_size or config.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or config.CHUNK_OVERLAP
        self.embedding_model = embedding_model or config.EMBEDDING_MODEL

        # Inizializza componenti
        self.raw_store = RawDataStore()
        self.vector_store = VectorStoreManager()
        self.html_cleaner = HTMLCleaner(preserve_structure=True)
        self.chunker = ContentChunker(
            chunk_size=self.chunk_size, overlap=self.chunk_overlap
        )

        # Client OpenAI per embeddings
        self.openai_client = OpenAI(api_key=self.openai_api_key)

        logger.info("IngestionPipeline inizializzata")
        logger.info(f"  Chunk size: {self.chunk_size}")
        logger.info(f"  Chunk overlap: {self.chunk_overlap}")
        logger.info(f"  Embedding model: {self.embedding_model}")

    def process_domain(
        self,
        domain: str,
        collection_name: Optional[str] = None,
        force_recreate: bool = False,
        max_pages: Optional[int] = None,
    ) -> Dict:
        """
        Processa tutte le pagine di un dominio e le inserisce nel vector store.

        Args:
            domain: Nome del dominio da processare
            collection_name: Nome collection (default: auto-generato)
            force_recreate: Se True, ricrea collection esistente
            max_pages: Numero massimo di pagine da processare (opzionale)

        Returns:
            Dict con statistiche del processo
        """
        logger.info(f"Inizio processing dominio: {domain}")

        # Verifica dominio esiste
        if domain not in self.raw_store.list_domains():
            raise ValueError(f"Dominio non trovato: {domain}")

        # Genera nome collection se non fornito
        if not collection_name:
            collection_name = self.vector_store.generate_collection_name(domain)

        logger.info(f"Collection: {collection_name}")

        # Crea collection
        self.vector_store.create_collection(
            collection_name=collection_name,
            vector_size=config.EMBEDDING_DIMENSIONS,
            force_recreate=force_recreate,
        )

        # Statistiche
        stats = {
            "domain": domain,
            "collection_name": collection_name,
            "pages_processed": 0,
            "pages_failed": 0,
            "chunks_created": 0,
            "chunks_inserted": 0,
        }

        # Processa pagine
        all_chunks = []
        page_count = 0

        logger.info("Processing pagine...")

        for page_data in tqdm(
            self.raw_store.iter_pages(domain), desc="Processing pagine"
        ):
            if max_pages and page_count >= max_pages:
                logger.info(f"Raggiunto limite di {max_pages} pagine")
                break

            page_count += 1

            try:
                # Processa pagina
                chunks = self._process_page(page_data)

                if chunks:
                    all_chunks.extend(chunks)
                    stats["pages_processed"] += 1
                    stats["chunks_created"] += len(chunks)
                else:
                    stats["pages_failed"] += 1

            except Exception as e:
                logger.error(f"Errore processando {page_data.get('url')}: {e}")
                stats["pages_failed"] += 1
                continue

        logger.info(
            f"Processing completato: {stats['pages_processed']} pagine, {stats['chunks_created']} chunk"
        )

        # Genera embeddings e inserisci
        if all_chunks:
            logger.info("Generazione embeddings...")
            embeddings = self._generate_embeddings(all_chunks)

            logger.info("Inserimento in vector store...")
            inserted = self.vector_store.insert_chunks(
                collection_name=collection_name,
                chunks=all_chunks,
                embeddings=embeddings,
            )

            stats["chunks_inserted"] = inserted

        logger.info("Ingestion completata!")
        logger.info(f"Statistiche: {stats}")

        return stats

    def _process_page(self, page_data: Dict) -> List[Dict]:
        """
        Processa una singola pagina: cleaning + chunking.

        Args:
            page_data: Dati raw della pagina

        Returns:
            Lista di chunk
        """
        url = page_data.get("url", "")
        html = page_data.get("html", "")
        title = page_data.get("title", "")

        if not html:
            logger.warning(f"HTML vuoto per {url}")
            return []

        # Clean HTML
        cleaned = self.html_cleaner.clean(html, url)

        if not cleaned["text"] or cleaned["word_count"] < 50:
            logger.debug(f"Contenuto insufficiente per {url} ({cleaned['word_count']} parole)")
            return []

        # Chunk text
        page_metadata = {
            "url": url,
            "page_title": title,
            "crawled_at": page_data.get("crawled_at", ""),
            "domain": page_data.get("metadata", {}).get("domain", ""),
        }

        chunks = self.chunker.chunk_document(
            text=cleaned["text"],
            url=url,
            title=title,
            page_metadata=page_metadata,
        )

        return chunks

    def _generate_embeddings(self, chunks: List[Dict]) -> List[List[float]]:
        """
        Genera embeddings per i chunk usando OpenAI.

        Args:
            chunks: Lista di chunk

        Returns:
            Lista di embedding vectors
        """
        # Estrai testi
        texts = [chunk["text"] for chunk in chunks]

        # Genera embeddings in batch
        batch_size = config.EMBEDDING_BATCH_SIZE
        all_embeddings = []

        for i in tqdm(
            range(0, len(texts), batch_size), desc="Generazione embeddings"
        ):
            batch_texts = texts[i : i + batch_size]

            try:
                response = self.openai_client.embeddings.create(
                    model=self.embedding_model, input=batch_texts
                )

                # Estrai embeddings dalla risposta
                batch_embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(batch_embeddings)

            except Exception as e:
                logger.error(f"Errore generando embeddings per batch {i}: {e}")
                # Usa embeddings zero come fallback
                zero_embedding = [0.0] * config.EMBEDDING_DIMENSIONS
                all_embeddings.extend([zero_embedding] * len(batch_texts))

        return all_embeddings

    def list_available_domains(self) -> List[str]:
        """
        Lista domini disponibili per ingestion.

        Returns:
            Lista di nomi dominio
        """
        return self.raw_store.list_domains()

    def get_domain_stats(self, domain: str) -> Dict:
        """
        Ottiene statistiche per un dominio.

        Args:
            domain: Nome del dominio

        Returns:
            Dict con statistiche
        """
        return self.raw_store.get_domain_stats(domain)


def create_pipeline(
    openai_api_key: Optional[str] = None,
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None,
) -> IngestionPipeline:
    """
    Factory function per creare IngestionPipeline.

    Args:
        openai_api_key: API key OpenAI
        chunk_size: Dimensione chunk
        chunk_overlap: Overlap chunk

    Returns:
        IngestionPipeline instance
    """
    return IngestionPipeline(
        openai_api_key=openai_api_key,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )


if __name__ == "__main__":
    # Test IngestionPipeline
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    try:
        pipeline = create_pipeline()

        print("=== Test Ingestion Pipeline ===")

        # Lista domini
        domains = pipeline.list_available_domains()
        print(f"\nDomini disponibili: {len(domains)}")

        for domain in domains:
            stats = pipeline.get_domain_stats(domain)
            print(f"\n{domain}:")
            print(f"  Pagine: {stats['page_count']}")
            print(f"  Dimensione: {stats['total_size_mb']} MB")

            # Chiedi se processare
            response = input(f"\nProcessare {domain}? (y/n): ")
            if response.lower() == "y":
                max_pages = input("Max pagine (invio per tutte): ")
                max_pages = int(max_pages) if max_pages else None

                result = pipeline.process_domain(domain, max_pages=max_pages)
                print(f"\nRisultato:")
                print(f"  Collection: {result['collection_name']}")
                print(f"  Pagine processate: {result['pages_processed']}")
                print(f"  Chunk inseriti: {result['chunks_inserted']}")

    except Exception as e:
        print(f"Errore: {e}")
        import traceback

        traceback.print_exc()

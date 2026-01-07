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
from storage.image_manager import ImageManager
from processors.html_cleaner import HTMLCleaner
from processors.content_chunker import ContentChunker
from processors.document_loaders import DocumentBatchLoader

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
        self.image_manager = ImageManager()
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
        Salta documenti (PDF, DOCX, ecc.) che verranno processati separatamente.

        Args:
            page_data: Dati raw della pagina

        Returns:
            Lista di chunk
        """
        # Salta documenti - verranno processati da ingest-docs
        is_document = page_data.get("metadata", {}).get("is_document", False)
        if is_document:
            logger.debug(f"Skipping documento (verrà processato da ingest-docs): {page_data.get('url', '')}")
            return []

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

    def process_documents(
        self,
        documents_dir: str,
        collection_name: str,
        force_recreate: bool = False,
        recursive: bool = True,
        extensions: Optional[List[str]] = None
    ) -> Dict:
        """
        Processa documenti locali (PDF, Word, etc.) e crea vector store.

        Args:
            documents_dir: Directory con documenti
            collection_name: Nome collection Qdrant
            force_recreate: Se True, ricrea collection se esiste
            recursive: Cerca documenti in subdirectory
            extensions: Lista estensioni da processare

        Returns:
            Dict con statistiche del processo
        """
        logger.info(f"Ingestion documenti da: {documents_dir}")

        # 1. Carica documenti
        batch_loader = DocumentBatchLoader(ocr_language="it+en")
        documents = batch_loader.load_directory(
            documents_dir,
            recursive=recursive,
            extensions=extensions
        )

        if not documents:
            logger.warning("Nessun documento trovato!")
            return {
                "documents_dir": documents_dir,
                "collection_name": collection_name,
                "documents_processed": 0,
                "documents_failed": 0,
                "chunks_created": 0,
                "chunks_inserted": 0,
            }

        logger.info(f"Caricati {len(documents)} documenti")

        # 2. Prepara collection
        logger.info(f"Creazione collection: {collection_name}")
        self.vector_store.create_collection(
            collection_name=collection_name,
            vector_size=config.EMBEDDING_DIMENSIONS,
            force_recreate=force_recreate
        )

        # Statistiche
        stats = {
            "documents_dir": documents_dir,
            "collection_name": collection_name,
            "documents_processed": 0,
            "documents_failed": 0,
            "chunks_created": 0,
            "chunks_inserted": 0,
        }

        # 3. Process e chunking
        all_chunks = []
        for doc in tqdm(documents, desc="Processing documenti"):
            try:
                # Pulisci testo (rimuovi whitespace multipli, etc.)
                cleaned_text = self._clean_text(doc["text"])

                if not cleaned_text or len(cleaned_text.split()) < 50:
                    logger.debug(f"Contenuto insufficiente per {doc['metadata']['file_name']}")
                    stats["documents_failed"] += 1
                    continue

                # Salva immagini se presenti
                saved_images = []
                if "images" in doc["metadata"] and doc["metadata"]["images"]:
                    logger.info(f"Salvataggio {len(doc['metadata']['images'])} immagini da {doc['metadata']['file_name']}")
                    saved_images = self.image_manager.save_document_images(
                        collection_name=collection_name,
                        document_name=doc['metadata']['file_name'],
                        images=doc['metadata']['images']
                    )

                # Chunking
                chunks = self.chunker.chunk_text(
                    text=cleaned_text,
                    metadata={
                        **doc["metadata"],
                        "chunk_strategy": "semantic"
                    }
                )

                # Associa immagini ai chunk (se presenti)
                if saved_images:
                    chunks = self._associate_images_to_chunks(chunks, saved_images)

                all_chunks.extend(chunks)
                stats["documents_processed"] += 1
                stats["chunks_created"] += len(chunks)

            except Exception as e:
                logger.error(f"Errore processando {doc['metadata'].get('file_name')}: {e}")
                stats["documents_failed"] += 1
                continue

        logger.info(f"Totale chunks: {len(all_chunks)}")

        # 4. Genera embeddings e inserisci
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

        logger.info(f"Ingestion completata: {collection_name}")
        logger.info(f"Statistiche: {stats}")

        return stats

    def _associate_images_to_chunks(self, chunks: List[Dict], saved_images: List[Dict]) -> List[Dict]:
        """
        Associa immagini salvate ai chunk corretti.

        Per ora, tutte le immagini del documento sono aggiunte a tutti i chunk
        dello stesso documento. In futuro si può raffinare per associare immagini
        specifiche a chunk specifici basandosi sul paragraph_index.

        Args:
            chunks: Lista di chunk dal documento
            saved_images: Lista di immagini salvate con informazioni

        Returns:
            Lista di chunk con immagini aggiunte nei metadata
        """
        if not saved_images:
            return chunks

        # Prepara lista semplificata di immagini per metadata
        image_refs = []
        for img in saved_images:
            image_refs.append({
                "path": img["relative_path"],
                "paragraph_index": img.get("paragraph_index", -1),
                "text_before": img.get("text_before", "")[:100]  # Primi 100 caratteri
            })

        # Aggiungi riferimenti immagini a tutti i chunk del documento
        # (in futuro: logica più sofisticata per associare immagini specifiche a chunk specifici)
        for chunk in chunks:
            if "metadata" not in chunk:
                chunk["metadata"] = {}
            chunk["metadata"]["document_images"] = image_refs

        logger.debug(f"Associate {len(image_refs)} immagini a {len(chunks)} chunks")
        return chunks

    def _clean_text(self, text: str) -> str:
        """Pulizia testo da documenti."""
        import re

        # Rimuovi whitespace multipli
        text = re.sub(r'\s+', ' ', text)

        # Rimuovi righe vuote multiple
        text = re.sub(r'\n\s*\n', '\n\n', text)

        return text.strip()


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

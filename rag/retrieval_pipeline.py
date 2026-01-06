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
        filter_by_file: Optional[str] = None,
    ) -> List[Dict]:
        """
        Recupera chunk rilevanti per una query.

        Args:
            query: Query dell'utente
            top_k: Numero di risultati (default: self.top_k)
            score_threshold: Soglia minima di similarità (opzionale)
            filter_dict: Filtri sui metadata (opzionale)
            filter_by_file: Nome file per filtrare i risultati (es: "Disciplinari_A_B.pdf")

        Returns:
            Lista di chunk rilevanti con score
        """
        if not query or not query.strip():
            logger.warning("Query vuota")
            return []

        top_k = top_k or self.top_k

        try:
            # Aggiungi filtro per file_name se specificato
            if filter_by_file:
                if filter_dict is None:
                    filter_dict = {}
                filter_dict["file_name"] = filter_by_file
                logger.info(f"Filtro per file: {filter_by_file}")

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

            # Log dei file trovati per debug
            if results:
                files_found = set(r.get("metadata", {}).get("file_name", "N/A") for r in results)
                logger.info(f"File nei risultati: {files_found}")

            return results

        except Exception as e:
            logger.error(f"Errore durante retrieval: {e}")
            raise

    def retrieve_diverse(
        self,
        query: str,
        top_k: Optional[int] = None,
        diversity_threshold: float = 0.7,
    ) -> List[Dict]:
        """
        Recupera risultati diversificati (evita duplicati semantici).

        Args:
            query: Query dell'utente
            top_k: Numero di risultati finali
            diversity_threshold: Soglia di similarità per considerare duplicati

        Returns:
            Lista di chunk diversificati
        """
        # Recupera più risultati del necessario
        top_k = top_k or self.top_k
        initial_results = self.retrieve(query, top_k=top_k * 3)

        if not initial_results:
            return []

        # Seleziona risultati diversificati
        diverse_results = [initial_results[0]]  # Prendi il primo (più rilevante)

        for result in initial_results[1:]:
            # Controlla se è sufficientemente diverso dai già selezionati
            is_diverse = True
            for selected in diverse_results:
                # Confronto semplice basato su overlap di testo
                overlap = self._text_similarity(result["text"], selected["text"])
                if overlap > diversity_threshold:
                    is_diverse = False
                    break

            if is_diverse:
                diverse_results.append(result)

            if len(diverse_results) >= top_k:
                break

        logger.info(f"Risultati diversificati: {len(diverse_results)}/{len(initial_results)}")
        return diverse_results

    def _text_similarity(self, text1: str, text2: str) -> float:
        """
        Calcola similarità semplice tra due testi (Jaccard).

        Args:
            text1: Primo testo
            text2: Secondo testo

        Returns:
            Score di similarità (0-1)
        """
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return intersection / union if union > 0 else 0.0

    def retrieve_with_context(
        self,
        query: str,
        top_k: Optional[int] = None,
        context_window: int = 2,
        filter_by_file: Optional[str] = None,
    ) -> List[Dict]:
        """
        Recupera risultati con chunk adiacenti per più contesto.

        Args:
            query: Query dell'utente
            top_k: Numero di risultati base
            context_window: Numero di chunk prima/dopo da includere
            filter_by_file: Filtro per file

        Returns:
            Lista di risultati con chunk adiacenti
        """
        # Recupera risultati base
        base_results = self.retrieve(
            query,
            top_k=top_k,
            filter_by_file=filter_by_file
        )

        if not base_results or context_window <= 0:
            return base_results

        # Per ogni risultato, cerca chunk adiacenti
        # Nota: questa è una implementazione semplificata
        # In produzione, dovresti recuperare chunk per chunk_index
        logger.info(f"Espansione contesto con window={context_window}")

        # Per ora ritorniamo i risultati base
        # Una implementazione completa richiederebbe:
        # 1. Salvare chunk_index nei metadata durante ingestion
        # 2. Query Qdrant per chunk con stesso file_name e chunk_index +/- N
        return base_results

    def get_file_stats(self, file_name: str) -> Dict:
        """
        Ottiene statistiche per un file specifico nella collection.

        Args:
            file_name: Nome del file

        Returns:
            Dict con statistiche: total_chunks, avg_chunk_size, etc.
        """
        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue

            # Query Qdrant per contare chunk di questo file
            # Usa scroll per ottenere tutti i chunk del file
            scroll_result = self.vector_store.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="file_name",
                            match=MatchValue(value=file_name)
                        )
                    ]
                ),
                limit=10000,  # Limite alto per file grandi
                with_payload=True,
                with_vectors=False
            )

            points = scroll_result[0]
            total_chunks = len(points)

            if total_chunks == 0:
                return {
                    "file_name": file_name,
                    "total_chunks": 0,
                    "estimated_pages": 0,
                    "recommended_topk": 20
                }

            # Calcola statistiche
            total_chars = sum(len(p.payload.get("text", "")) for p in points)
            avg_chunk_size = total_chars / total_chunks if total_chunks > 0 else 0

            # Stima pagine (assumendo ~2000 char per pagina)
            estimated_pages = total_chars / 2000

            # Raccomandazione TOP_K
            # Euristica: per recuperare ~80% del contenuto di una sezione media
            # che occupa ~10-15% del documento
            recommended_topk = max(20, min(200, int(total_chunks * 0.3)))

            return {
                "file_name": file_name,
                "total_chunks": total_chunks,
                "total_chars": total_chars,
                "avg_chunk_size": int(avg_chunk_size),
                "estimated_pages": int(estimated_pages),
                "recommended_topk": recommended_topk,
                "recommended_topk_ranges": {
                    "query_semplice": max(10, int(total_chunks * 0.1)),
                    "sezione_media": max(20, int(total_chunks * 0.2)),
                    "sezione_grande": max(50, int(total_chunks * 0.4)),
                    "documento_completo": min(200, total_chunks)
                }
            }

        except Exception as e:
            logger.error(f"Errore ottenendo stats per {file_name}: {e}")
            return {
                "file_name": file_name,
                "error": str(e),
                "recommended_topk": 20
            }

    def estimate_tokens(self, text: str) -> int:
        """
        Stima numero di token in un testo.
        Euristica: 1 token ≈ 4 caratteri (conservativa)

        Args:
            text: Testo da stimare

        Returns:
            Numero stimato di token
        """
        return len(text) // 4

    def suggest_topk(
        self,
        query: str,
        filter_by_file: Optional[str] = None,
        max_context_tokens: int = 150000  # Limite sicuro sotto i 200k
    ) -> int:
        """
        Suggerisce TOP_K ottimale basato su query, file e limite token.

        Args:
            query: Query dell'utente
            filter_by_file: File filtrato (se presente)
            max_context_tokens: Limite massimo token per contesto

        Returns:
            TOP_K suggerito
        """
        # Parole chiave che indicano richieste complete/lunghe
        complete_keywords = [
            "tutti", "completo", "intero", "elenco", "lista",
            "elenca", "per intero", "dall'inizio alla fine",
            "senza omettere", "completamente"
        ]

        query_lower = query.lower()
        is_complete_request = any(kw in query_lower for kw in complete_keywords)

        # Se c'è filtro file, usa statistiche del file
        if filter_by_file:
            stats = self.get_file_stats(filter_by_file)

            if is_complete_request:
                # Richiesta completa -> usa 40-60% dei chunk
                suggested = stats["recommended_topk_ranges"]["sezione_grande"]
            else:
                # Query normale -> usa 20-30% dei chunk
                suggested = stats["recommended_topk_ranges"]["sezione_media"]

            # NUOVO: Calcola token stimati e cap se necessario
            avg_chunk_tokens = stats["avg_chunk_size"] // 4  # ~250 token per chunk medio
            estimated_total_tokens = suggested * avg_chunk_tokens

            if estimated_total_tokens > max_context_tokens:
                # Calcola TOP_K massimo che rispetta limite token
                max_topk = max_context_tokens // avg_chunk_tokens
                original_suggested = suggested
                suggested = min(suggested, max_topk)

                logger.warning(
                    f"TOP_K limitato per token: {original_suggested} -> {suggested} "
                    f"(stimato {estimated_total_tokens:,} token > limite {max_context_tokens:,})"
                )

            logger.info(
                f"TOP_K suggerito: {suggested} (file ha {stats['total_chunks']} chunk, "
                f"~{suggested * avg_chunk_tokens:,} token)"
            )
            return suggested

        # Senza filtro file, usa euristica base
        if is_complete_request:
            return 50
        else:
            return 20

    def list_files_in_collection(self) -> List[str]:
        """
        Lista tutti i file distinti nella collection.

        Returns:
            Lista di nomi file
        """
        # Query un piccolo set di risultati per ottenere i file
        try:
            # Usa una query generica per ottenere documenti
            dummy_query = "documento"
            results = self.retrieve(dummy_query, top_k=100)

            files = set()
            for result in results:
                file_name = result.get("metadata", {}).get("file_name", "")
                if file_name:
                    files.add(file_name)

            return sorted(list(files))

        except Exception as e:
            logger.error(f"Errore listando file: {e}")
            return []

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
        max_context_tokens: Optional[int] = None,
    ) -> str:
        """
        Formatta risultati di retrieval come context per LLM.

        Args:
            results: Risultati di retrieval
            include_metadata: Se True, include metadata (URL, titolo)
            max_context_length: Lunghezza massima in caratteri (opzionale)
            max_context_tokens: Lunghezza massima in token (opzionale)

        Returns:
            Context formattato come stringa
        """
        if not results:
            return "Nessun contesto rilevante trovato."

        context_parts = []
        total_chars = 0
        total_tokens_estimate = 0
        truncated_at = None

        for i, result in enumerate(results, 1):
            part = f"[Documento {i}]"

            if include_metadata:
                metadata = result.get("metadata", {})

                # Metadata per documenti locali
                file_name = metadata.get("file_name", "")
                file_type = metadata.get("file_type", "")
                source = metadata.get("source", "")

                # Metadata per web crawling
                url = result.get("url", metadata.get("url", ""))
                title = result.get("page_title", metadata.get("page_title", ""))

                # Priorità: mostra file_name se è un documento, altrimenti URL/titolo
                if file_name:
                    part += f"\nFile: {file_name}"
                    if file_type:
                        part += f" (tipo: {file_type})"
                elif title:
                    part += f"\nTitolo: {title}"

                if url:
                    part += f"\nURL: {url}"
                elif source:
                    part += f"\nPercorso: {source}"

                score = result.get("score", 0)
                part += f"\nRilevanza: {score:.3f}"

            part += f"\n\n{result['text']}\n"

            # Check limiti PRIMA di aggiungere
            part_chars = len(part)
            part_tokens = self.estimate_tokens(part)

            # Check limite token (priorità)
            if max_context_tokens and (total_tokens_estimate + part_tokens) > max_context_tokens:
                truncated_at = i
                logger.warning(
                    f"Context troncato a {i-1}/{len(results)} documenti "
                    f"(~{total_tokens_estimate:,} token, limite {max_context_tokens:,})"
                )
                break

            # Check limite caratteri
            if max_context_length and (total_chars + part_chars) > max_context_length:
                truncated_at = i
                logger.warning(
                    f"Context troncato a {i-1}/{len(results)} documenti "
                    f"({total_chars:,} caratteri, limite {max_context_length:,})"
                )
                break

            context_parts.append(part)
            total_chars += part_chars
            total_tokens_estimate += part_tokens

        context = "\n---\n".join(context_parts)

        # Aggiungi nota se troncato
        if truncated_at:
            context += f"\n\n[NOTA: Contesto limitato a {len(context_parts)}/{len(results)} documenti per limiti di token. "
            context += f"Documenti inclusi hanno i punteggi di rilevanza più alti.]"

        logger.info(f"Context finale: {len(context_parts)} documenti, ~{total_tokens_estimate:,} token stimati")

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
        seen_sources = set()

        for result in results:
            metadata = result.get("metadata", {})

            # Per documenti locali
            file_name = metadata.get("file_name", "")
            source = metadata.get("source", "")

            # Per web crawling
            url = result.get("url", metadata.get("url", ""))
            title = result.get("page_title", metadata.get("page_title", ""))

            # Crea identificatore unico per la fonte
            if file_name:
                source_id = file_name
                if source_id not in seen_sources:
                    source_str = f"- {file_name}"
                    if source:
                        source_str += f"\n  Percorso: {source}"
                    sources.append(source_str)
                    seen_sources.add(source_id)
            elif url:
                source_id = url
                if source_id not in seen_sources:
                    display_title = title if title else url
                    sources.append(f"- {display_title}\n  {url}")
                    seen_sources.add(source_id)

        return "\n".join(sources) if sources else "Nessuna fonte disponibile."

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

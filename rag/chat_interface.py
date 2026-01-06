"""
Interfaccia chat interattiva per RAG con Anthropic Claude.
Usa datapizza-ai per integrazione con Claude.
"""
import logging
from typing import List, Dict, Optional

from anthropic import Anthropic

import config
from rag.retrieval_pipeline import RetrievalPipeline
from storage.image_manager import ImageManager

logger = logging.getLogger(__name__)


class ChatInterface:
    """
    Interfaccia chat REPL-style con RAG.
    """

    def __init__(
        self,
        collection_name: str,
        anthropic_api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_k_retrieval: Optional[int] = None,
        use_diverse_retrieval: bool = False,
    ):
        """
        Inizializza ChatInterface.

        Args:
            collection_name: Nome collection Qdrant
            anthropic_api_key: API key Anthropic (default: config)
            openai_api_key: API key OpenAI per embeddings (default: config)
            model: Modello Claude (default: config)
            max_tokens: Max tokens risposta (default: config)
            temperature: Temperature (default: config)
            top_k_retrieval: Top-K retrieval (default: config)
            use_diverse_retrieval: Se True, usa retrieval diversificato (default: False)
        """
        self.collection_name = collection_name
        self.anthropic_api_key = anthropic_api_key or config.ANTHROPIC_API_KEY
        self.openai_api_key = openai_api_key or config.OPENAI_API_KEY
        self.model = model or config.LLM_MODEL
        self.max_tokens = max_tokens or config.LLM_MAX_TOKENS
        self.temperature = temperature or config.LLM_TEMPERATURE
        self.top_k_retrieval = top_k_retrieval or config.TOP_K_RETRIEVAL
        self.use_diverse_retrieval = use_diverse_retrieval
        self.filter_by_file: Optional[str] = None  # Filtro file attivo
        self.auto_topk: bool = True  # TOP_K automatico abilitato di default

        # Inizializza retrieval pipeline
        self.retrieval = RetrievalPipeline(
            collection_name=collection_name,
            openai_api_key=self.openai_api_key,
            top_k=self.top_k_retrieval,
        )

        # Image manager
        self.image_manager = ImageManager()

        # Client Anthropic
        self.anthropic_client = Anthropic(api_key=self.anthropic_api_key)

        # Conversation history
        self.conversation_history: List[Dict] = []

        # Ultima retrieval (per comando /sources)
        self.last_retrieval_results: List[Dict] = []

        logger.info(f"ChatInterface inizializzata per collection: {collection_name}")
        logger.info(f"  Modello: {self.model}")
        logger.info(f"  Max tokens: {self.max_tokens}")
        logger.info(f"  Temperature: {self.temperature}")

    def chat(self, user_message: str, include_history: bool = True) -> Dict:
        """
        Processa un messaggio utente e genera risposta.

        Args:
            user_message: Messaggio dell'utente
            include_history: Se True, include cronologia conversazione

        Returns:
            Dict con risposta e metadata
        """
        if not user_message or not user_message.strip():
            return {"response": "Per favore inserisci una domanda.", "sources": []}

        try:
            # Determina TOP_K da usare
            topk_to_use = self.top_k_retrieval

            if self.auto_topk:
                # Suggerisci TOP_K ottimale
                suggested_topk = self.retrieval.suggest_topk(
                    user_message,
                    filter_by_file=self.filter_by_file
                )

                if suggested_topk != topk_to_use:
                    logger.info(f"TOP_K automatico: {topk_to_use} -> {suggested_topk}")
                    topk_to_use = suggested_topk

            # Retrieval context con opzioni
            if self.use_diverse_retrieval:
                retrieval_results = self.retrieval.retrieve_diverse(user_message, top_k=topk_to_use)
            else:
                retrieval_results = self.retrieval.retrieve(
                    user_message,
                    top_k=topk_to_use,
                    filter_by_file=self.filter_by_file
                )
            self.last_retrieval_results = retrieval_results

            # Formatta context con limite token
            # Limite: 150k per context + 50k per system prompt e risposta = 200k totale
            context = self.retrieval.format_context(
                retrieval_results,
                include_metadata=True,
                max_context_tokens=150000  # Limite sicuro
            )

            # Costruisci system prompt con context
            system_prompt = self._build_system_prompt(context)

            # Costruisci messaggi
            messages = []

            # Aggiungi cronologia se richiesto
            if include_history and self.conversation_history:
                messages.extend(self.conversation_history)

            # Aggiungi messaggio corrente
            messages.append({"role": "user", "content": user_message})

            # Chiama Claude
            response = self.anthropic_client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system_prompt,
                messages=messages,
            )

            # Estrai risposta
            assistant_message = response.content[0].text

            # Salva in cronologia
            self.conversation_history.append(
                {"role": "user", "content": user_message}
            )
            self.conversation_history.append(
                {"role": "assistant", "content": assistant_message}
            )

            # Formatta fonti
            sources = self.retrieval.format_sources(retrieval_results)

            # Estrai immagini dai risultati
            images = self._extract_images_from_results(retrieval_results)

            return {
                "response": assistant_message,
                "sources": sources,
                "images": images,  # Lista path immagini
                "num_results": len(retrieval_results),
                "tokens_used": response.usage.input_tokens + response.usage.output_tokens,
            }

        except Exception as e:
            logger.error(f"Errore durante chat: {e}")
            return {
                "response": f"Errore: {str(e)}",
                "sources": "",
                "num_results": 0,
            }

    def _build_system_prompt(self, context: str) -> str:
        """
        Costruisce system prompt con context.

        Args:
            context: Context da retrieval

        Returns:
            System prompt
        """
        return f"""Sei un assistente AI specializzato nell'analisi di documenti e siti web. Rispondi basandoti ESCLUSIVAMENTE sul contesto fornito.

Il contesto contiene frammenti di documenti (PDF, Word, etc.) o pagine web rilevanti per la domanda dell'utente.

REGOLE CRITICHE - SEGUI RIGOROSAMENTE:
1. **RISPONDI SOLO CON INFORMAZIONI PRESENTI NEL CONTESTO**: Se una informazione non è nel contesto fornito, devi dire esplicitamente "Il contesto fornito non contiene queste informazioni" o "Non ho trovato informazioni su questo argomento nel contesto disponibile".

2. **NON INVENTARE, NON DEDURRE, NON AGGIUNGERE**: Non fare deduzioni, non aggiungere informazioni da conoscenze pregresse, non inventare dettagli. Solo ciò che è scritto esplicitamente nel contesto.

3. **CITA SEMPRE LE FONTI**: Quando rispondi, indica da quale documento/i proviene l'informazione (es: "Secondo il documento [Documento 1] - Disciplinari_A_B.pdf...").

4. **VERIFICA LA RILEVANZA**: Prima di rispondere, verifica che i documenti nel contesto siano effettivamente rilevanti per la domanda. Se i documenti parlano di argomenti diversi da quello richiesto, dillo chiaramente.

5. **SEGNALA INFORMAZIONI INCOMPLETE**: Se il contesto contiene solo informazioni parziali sull'argomento, spiega cosa è presente e cosa manca.

6. **SEGNALA CONTRADDIZIONI**: Se ci sono informazioni contraddittorie tra i documenti, evidenzialo.

CONTESTO DISPONIBILE:
{context}

===

Ora rispondi alla domanda dell'utente basandoti ESCLUSIVAMENTE su questo contesto. Ricorda: se l'informazione non è nel contesto, dillo chiaramente invece di rispondere."""

    def _extract_images_from_results(self, retrieval_results: List[Dict]) -> List[Dict]:
        """
        Estrae immagini dai risultati del retrieval.

        Args:
            retrieval_results: Lista risultati retrieval con metadata

        Returns:
            Lista di dict con informazioni immagini: [{
                "path": "collection/doc/img_001.png",
                "absolute_path": "/full/path/to/img_001.png",
                "source_doc": "MyDocument.docx"
            }]
        """
        seen_images = set()  # Per evitare duplicati
        images = []

        for result in retrieval_results:
            metadata = result.get("metadata", {})

            # Controlla se ci sono immagini nei metadata
            document_images = metadata.get("document_images", [])

            for img_info in document_images:
                img_path = img_info.get("path")
                if img_path and img_path not in seen_images:
                    seen_images.add(img_path)

                    # Ottieni path assoluto
                    abs_path = self.image_manager.get_image_path(img_path)

                    if abs_path and abs_path.exists():
                        images.append({
                            "path": img_path,
                            "absolute_path": str(abs_path),
                            "source_doc": metadata.get("file_name", "Unknown")
                        })

        logger.info(f"Estratte {len(images)} immagini uniche dai risultati")
        return images

    def clear_history(self):
        """Pulisce la cronologia conversazione."""
        self.conversation_history = []
        logger.info("Cronologia conversazione pulita")

    def get_last_sources(self) -> str:
        """
        Ottiene le fonti dell'ultima query.

        Returns:
            Fonti formattate
        """
        if not self.last_retrieval_results:
            return "Nessuna fonte disponibile."

        return self.retrieval.format_sources(self.last_retrieval_results)

    def set_file_filter(self, file_name: Optional[str]):
        """
        Imposta filtro per file specifico.

        Args:
            file_name: Nome file da filtrare (None per rimuovere filtro)
        """
        self.filter_by_file = file_name
        if file_name:
            logger.info(f"Filtro file attivo: {file_name}")
        else:
            logger.info("Filtro file rimosso")

    def list_available_files(self) -> List[str]:
        """
        Lista file disponibili nella collection.

        Returns:
            Lista nomi file
        """
        return self.retrieval.list_files_in_collection()

    def get_collection_info(self) -> Dict:
        """
        Ottiene info sulla collection.

        Returns:
            Dict con info
        """
        return self.retrieval.get_collection_info()

    def run_interactive(self):
        """
        Avvia loop interattivo REPL.
        """
        print("=" * 60)
        print("  DataPizzaRouge - Chat Interattiva RAG")
        print("=" * 60)
        print(f"Collection: {self.collection_name}")

        # Info collection
        info = self.get_collection_info()
        print(f"Documenti disponibili: {info['points_count']}")

        print("\nComandi disponibili:")
        print("  /quit, /exit, /q  - Esci")
        print("  /clear            - Pulisci cronologia conversazione")
        print("  /sources          - Mostra fonti ultima risposta")
        print("  /info             - Info collection")
        print("  /files            - Lista file disponibili")
        print("  /fileinfo <nome>  - Statistiche dettagliate file")
        print("  /filter <nome>    - Filtra risultati per file specifico")
        print("  /nofilter         - Rimuovi filtro file")
        print("  /topk <numero>    - Cambia numero risultati")
        print("  /auto             - Abilita TOP_K automatico (consigliato)")
        print("\nDigita la tua domanda e premi Enter...")
        print("=" * 60)

        while True:
            try:
                # Input utente
                user_input = input("\n\033[1;34mTu:\033[0m ").strip()

                if not user_input:
                    continue

                # Comandi
                if user_input.lower() in ["/quit", "/exit", "/q"]:
                    print("\nArrivederci!")
                    break

                elif user_input.lower() == "/clear":
                    self.clear_history()
                    print("Cronologia pulita")
                    continue

                elif user_input.lower() == "/sources":
                    print("\n\033[1;33mFonti:\033[0m")
                    print(self.get_last_sources())
                    continue

                elif user_input.lower() == "/info":
                    info = self.get_collection_info()
                    print("\n\033[1;33mInfo Collection:\033[0m")
                    print(f"  Nome: {info['name']}")
                    print(f"  Punti: {info['points_count']}")
                    print(f"  Vector size: {info['vector_size']}")
                    print(f"  Distance: {info['distance']}")
                    if self.filter_by_file:
                        print(f"  Filtro attivo: {self.filter_by_file}")
                    continue

                elif user_input.lower() == "/files":
                    print("\n\033[1;33mFile disponibili:\033[0m")
                    files = self.list_available_files()
                    if files:
                        for i, file_name in enumerate(files, 1):
                            marker = " [FILTRATO]" if file_name == self.filter_by_file else ""
                            print(f"  {i}. {file_name}{marker}")
                    else:
                        print("  Nessun file trovato")
                    continue

                elif user_input.lower().startswith("/filter "):
                    file_name = user_input[8:].strip()
                    self.set_file_filter(file_name)
                    print(f"Filtro attivo per: {file_name}")
                    print("Le query cercheranno SOLO in questo file.")
                    continue

                elif user_input.lower() == "/nofilter":
                    self.set_file_filter(None)
                    print("Filtro file rimosso. Cerchero' in tutti i documenti.")
                    continue

                elif user_input.lower() == "/auto":
                    self.auto_topk = not self.auto_topk
                    status = "abilitato" if self.auto_topk else "disabilitato"
                    print(f"TOP_K automatico {status}")
                    if self.auto_topk:
                        print("Il sistema calcolera' automaticamente TOP_K ottimale per ogni query")
                    else:
                        print(f"Verra' usato TOP_K fisso: {self.top_k_retrieval}")
                    continue

                elif user_input.lower().startswith("/fileinfo "):
                    file_name = user_input[10:].strip()
                    print(f"\n\033[1;33mStatistiche file: {file_name}\033[0m")
                    stats = self.retrieval.get_file_stats(file_name)

                    if "error" in stats:
                        print(f"Errore: {stats['error']}")
                    else:
                        print(f"  Total chunk: {stats['total_chunks']}")
                        print(f"  Pagine stimate: {stats['estimated_pages']}")
                        print(f"  Dimensione media chunk: {stats['avg_chunk_size']} caratteri")

                        # Calcola token stimati
                        avg_tokens = stats['avg_chunk_size'] // 4
                        print(f"  Token medi per chunk: ~{avg_tokens}")

                        print(f"\n  TOP_K raccomandati (con stima token):")
                        for tipo, topk in stats['recommended_topk_ranges'].items():
                            tipo_label = {
                                "query_semplice": "Query semplice",
                                "sezione_media": "Sezione media",
                                "sezione_grande": "Sezione grande",
                                "documento_completo": "Documento completo"
                            }.get(tipo, tipo)

                            estimated_tokens = topk * avg_tokens
                            warning = ""
                            if estimated_tokens > 150000:
                                warning = " [!] SUPERA LIMITE TOKEN"
                                # Calcola topk sicuro
                                safe_topk = 150000 // avg_tokens
                                warning += f" -> usa max {safe_topk}"

                            print(f"    {tipo_label}: {topk} (~{estimated_tokens:,} token){warning}")

                        print(f"\n  Limite token contesto: 150,000")
                        print(f"  Limite totale Claude: 200,000")
                    continue

                elif user_input.lower().startswith("/topk "):
                    try:
                        new_topk = int(user_input[6:].strip())
                        if new_topk < 1 or new_topk > 200:
                            print("TOP_K deve essere tra 1 e 200")
                            continue
                        self.top_k_retrieval = new_topk
                        self.retrieval.top_k = new_topk
                        self.auto_topk = False  # Disabilita auto quando imposti manualmente
                        print(f"TOP_K impostato manualmente a {new_topk}")
                        print("(TOP_K automatico disabilitato. Usa /auto per riabilitarlo)")
                        continue
                    except ValueError:
                        print("Formato non valido. Usa: /topk <numero>")
                        continue

                # Processa query
                result = self.chat(user_input)

                # Mostra risposta
                print(f"\n\033[1;32mAssistente:\033[0m {result['response']}")

                # Mostra metadata
                print(f"\n\033[2m[{result['num_results']} documenti trovati")
                if "tokens_used" in result:
                    print(f" | {result['tokens_used']} tokens]")
                else:
                    print("]")
                print("\033[0m", end="")

                # Mostra fonti
                if result["sources"]:
                    print(f"\n\033[2;33mFonti:\033[0m")
                    print(f"\033[2m{result['sources']}\033[0m")

                # Mostra immagini se presenti
                if result.get("images"):
                    print(f"\n\033[1;35mImmagini associate:\033[0m")
                    for i, img in enumerate(result["images"], 1):
                        print(f"  {i}. {img['absolute_path']}")
                        print(f"     (da: {img['source_doc']})")

            except KeyboardInterrupt:
                print("\n\nInterrotto. Usa /quit per uscire.")
                continue
            except EOFError:
                print("\n\nArrivederci!")
                break
            except Exception as e:
                logger.error(f"Errore: {e}")
                print(f"\n\033[1;31mErrore:\033[0m {e}")
                continue


def create_chat_interface(
    collection_name: str,
    anthropic_api_key: Optional[str] = None,
    openai_api_key: Optional[str] = None,
) -> ChatInterface:
    """
    Factory function per creare ChatInterface.

    Args:
        collection_name: Nome collection
        anthropic_api_key: API key Anthropic
        openai_api_key: API key OpenAI

    Returns:
        ChatInterface instance
    """
    return ChatInterface(
        collection_name=collection_name,
        anthropic_api_key=anthropic_api_key,
        openai_api_key=openai_api_key,
    )


if __name__ == "__main__":
    # Test ChatInterface
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    from storage.vector_store_manager import VectorStoreManager

    # Lista collection
    vector_store = VectorStoreManager()
    collections = vector_store.list_collections()

    if not collections:
        print("Nessuna collection trovata. Esegui prima crawl e ingestion.")
        sys.exit(1)

    print("Collection disponibili:")
    for i, coll in enumerate(collections, 1):
        info = vector_store.get_collection_info(coll)
        if info:
            print(f"{i}. {coll} ({info['points_count']} punti)")

    # Seleziona collection
    try:
        choice = input("\nSeleziona collection (numero o nome): ")
        if choice.isdigit():
            collection_name = collections[int(choice) - 1]
        else:
            collection_name = choice

        # Crea e avvia chat
        chat = create_chat_interface(collection_name)
        chat.run_interactive()

    except Exception as e:
        print(f"Errore: {e}")
        import traceback

        traceback.print_exc()

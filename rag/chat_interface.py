"""
Interfaccia chat interattiva per RAG con Anthropic Claude.
Usa datapizza-ai per integrazione con Claude.
"""
import logging
from typing import List, Dict, Optional

from anthropic import Anthropic

import config
from rag.retrieval_pipeline import RetrievalPipeline

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
        """
        self.collection_name = collection_name
        self.anthropic_api_key = anthropic_api_key or config.ANTHROPIC_API_KEY
        self.openai_api_key = openai_api_key or config.OPENAI_API_KEY
        self.model = model or config.LLM_MODEL
        self.max_tokens = max_tokens or config.LLM_MAX_TOKENS
        self.temperature = temperature or config.LLM_TEMPERATURE
        self.top_k_retrieval = top_k_retrieval or config.TOP_K_RETRIEVAL

        # Inizializza retrieval pipeline
        self.retrieval = RetrievalPipeline(
            collection_name=collection_name,
            openai_api_key=self.openai_api_key,
            top_k=self.top_k_retrieval,
        )

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
            # Retrieval context
            retrieval_results = self.retrieval.retrieve(user_message)
            self.last_retrieval_results = retrieval_results

            # Formatta context
            context = self.retrieval.format_context(
                retrieval_results, include_metadata=True
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

            return {
                "response": assistant_message,
                "sources": sources,
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
        return f"""Sei un assistente AI che risponde a domande basandoti esclusivamente sul contesto fornito.

Il contesto proviene da un crawl di un sito web e contiene informazioni rilevanti per la domanda dell'utente.

REGOLE IMPORTANTI:
1. Rispondi SOLO basandoti sul contesto fornito
2. Se il contesto non contiene informazioni sufficienti, dillo chiaramente
3. Cita le fonti quando possibile (menziona i documenti specifici)
4. Sii conciso ma completo
5. Se ci sono informazioni contraddittorie, segnalalo

CONTESTO:
{context}

Rispondi alle domande dell'utente basandoti esclusivamente su questo contesto."""

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
                    print("✓ Cronologia pulita")
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

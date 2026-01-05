"""
CLI principale per DataPizzaRouge.
Comandi: crawl, ingest, chat, list-collections, stats.
"""
import os
import sys
import logging
import subprocess
from pathlib import Path

import click

import config
from storage.raw_data_store import RawDataStore
from storage.vector_store_manager import VectorStoreManager
from rag.ingestion_pipeline import IngestionPipeline
from rag.chat_interface import ChatInterface

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(config.LOG_FILE),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger(__name__)


@click.group()
@click.version_option(version="1.0.0", prog_name="DataPizzaRouge")
def cli():
    """
    DataPizzaRouge - Sistema RAG per Web Crawling.

    Crawla siti web, processa contenuti e fornisce chat interattiva
    usando Anthropic Claude con RAG (Retrieval-Augmented Generation).
    """
    pass


@cli.command()
@click.argument("url")
@click.option(
    "--max-pages",
    "-m",
    type=int,
    default=config.MAX_PAGES,
    help=f"Numero massimo di pagine da crawlare (default: {config.MAX_PAGES})",
)
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(),
    default=str(config.RAW_DATA_PATH),
    help="Directory output per dati raw",
)
def crawl(url, max_pages, output_dir):
    """
    Crawla un sito web.

    Esempio:
        python cli.py crawl https://example.com --max-pages 100
    """
    click.echo(f"\n{'='*60}")
    click.echo("  CRAWLING")
    click.echo(f"{'='*60}")
    click.echo(f"URL: {url}")
    click.echo(f"Max pages: {max_pages}")
    click.echo(f"Output: {output_dir}")
    click.echo(f"{'='*60}\n")

    try:
        # Verifica che Scrapy sia installato
        subprocess.run([sys.executable, "-m", "scrapy", "version"], check=True, capture_output=True)
    except Exception as e:
        click.echo(f"❌ Errore: Scrapy non trovato. Installa dependencies: pip install -r requirements.txt", err=True)
        sys.exit(1)

    # Costruisci comando Scrapy (usa python -m scrapy per compatibilità Windows)
    scrapy_cmd = [
        sys.executable,
        "-m",
        "scrapy",
        "crawl",
        "domain",
        "-a",
        f"start_url={url}",
        "-a",
        f"max_pages={max_pages}",
    ]

    # Esegui crawler
    click.echo("🕷️  Avvio crawler Scrapy...\n")

    try:
        # Esegui dalla root del progetto (non da dentro crawler/)
        project_root = Path(__file__).parent

        # Imposta SCRAPY_SETTINGS_MODULE per trovare le impostazioni
        env = os.environ.copy()
        env['SCRAPY_SETTINGS_MODULE'] = 'crawler.settings'

        result = subprocess.run(
            scrapy_cmd,
            cwd=str(project_root),
            env=env,
            check=False,
        )

        if result.returncode == 0:
            click.echo(f"\n✓ Crawling completato!")
            click.echo(f"\nProssimo passo:")
            click.echo(f"  python cli.py ingest --domain <domain>")
        else:
            click.echo(f"\n❌ Crawling fallito con codice: {result.returncode}", err=True)
            sys.exit(1)

    except Exception as e:
        click.echo(f"❌ Errore durante crawling: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    "--domain",
    "-d",
    help="Dominio da processare (es: example.com)",
)
@click.option(
    "--collection",
    "-c",
    help="Nome collection custom (default: auto-generato con timestamp). Usa nome fisso per aggiornamenti periodici.",
)
@click.option(
    "--max-pages",
    "-m",
    type=int,
    help="Numero massimo di pagine da processare",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Forza ricreazione collection se esiste. Usa per aggiornamenti settimanali.",
)
def ingest(domain, collection, max_pages, force):
    """
    Processa dati crawlati e crea vector store.

    Esempi:
        # Collection auto-generata (con timestamp)
        python cli.py ingest --domain example.com

        # Collection con nome fisso (per aggiornamenti periodici)
        python cli.py ingest --domain example.com --collection site_latest

        # Sovrascrive collection esistente (utile per refresh settimanali)
        python cli.py ingest --domain example.com --collection site_latest --force
    """
    click.echo(f"\n{'='*60}")
    click.echo("  INGESTION")
    click.echo(f"{'='*60}")

    try:
        # Inizializza pipeline
        pipeline = IngestionPipeline()

        # Se domain non specificato, mostra lista
        if not domain:
            domains = pipeline.list_available_domains()

            if not domains:
                click.echo("❌ Nessun dominio trovato. Esegui prima il crawl.", err=True)
                sys.exit(1)

            click.echo("Domini disponibili:\n")
            for i, d in enumerate(domains, 1):
                stats = pipeline.get_domain_stats(d)
                click.echo(f"{i}. {d}")
                click.echo(f"   Pagine: {stats['page_count']}")
                click.echo(f"   Dimensione: {stats['total_size_mb']} MB")
                click.echo()

            choice = click.prompt("Seleziona dominio (numero o nome)", type=str)

            if choice.isdigit():
                domain = domains[int(choice) - 1]
            else:
                domain = choice

        # Verifica dominio esiste
        if domain not in pipeline.list_available_domains():
            click.echo(f"❌ Dominio non trovato: {domain}", err=True)
            sys.exit(1)

        # Mostra info
        stats = pipeline.get_domain_stats(domain)
        click.echo(f"\nDominio: {domain}")
        click.echo(f"Pagine: {stats['page_count']}")
        click.echo(f"Dimensione: {stats['total_size_mb']} MB")

        if max_pages:
            click.echo(f"Max pages: {max_pages}")

        if collection:
            click.echo(f"Collection: {collection}")
            if force:
                click.echo(f"⚠️  ATTENZIONE: Collection esistente verrà sovrascritta!")

        click.echo(f"{'='*60}\n")

        # Conferma
        if not click.confirm("Procedere con ingestion?"):
            click.echo("Operazione annullata.")
            sys.exit(0)

        # Processa
        click.echo("\n🔄 Processing in corso...\n")

        result = pipeline.process_domain(
            domain=domain,
            collection_name=collection,
            force_recreate=force,
            max_pages=max_pages,
        )

        # Mostra risultati
        click.echo(f"\n{'='*60}")
        click.echo("  RISULTATI")
        click.echo(f"{'='*60}")
        click.echo(f"✓ Ingestion completata!")
        click.echo(f"\nCollection: {result['collection_name']}")
        click.echo(f"Pagine processate: {result['pages_processed']}")
        click.echo(f"Pagine fallite: {result['pages_failed']}")
        click.echo(f"Chunk creati: {result['chunks_created']}")
        click.echo(f"Chunk inseriti: {result['chunks_inserted']}")

        click.echo(f"\nProssimo passo:")
        click.echo(f"  python cli.py chat --collection {result['collection_name']}")

    except Exception as e:
        click.echo(f"\n❌ Errore: {e}", err=True)
        logger.exception("Errore durante ingestion")
        sys.exit(1)


@cli.command()
@click.option(
    "--collection",
    "-c",
    help="Nome collection da usare",
)
def chat(collection):
    """
    Avvia chat interattiva con RAG.

    Esempio:
        python cli.py chat --collection crawl_example_com_20260105
    """
    try:
        # Se collection non specificata, mostra lista
        if not collection:
            vector_store = VectorStoreManager()
            collections = vector_store.list_collections()

            if not collections:
                click.echo("❌ Nessuna collection trovata. Esegui prima crawl e ingest.", err=True)
                sys.exit(1)

            click.echo("\nCollection disponibili:\n")
            for i, coll in enumerate(collections, 1):
                info = vector_store.get_collection_info(coll)
                if info:
                    click.echo(f"{i}. {coll}")
                    click.echo(f"   Documenti: {info['points_count']}")
                    click.echo()

            choice = click.prompt("Seleziona collection (numero o nome)", type=str)

            if choice.isdigit():
                collection = collections[int(choice) - 1]
            else:
                collection = choice

        # Verifica collection esiste
        vector_store = VectorStoreManager()
        if collection not in vector_store.list_collections():
            click.echo(f"❌ Collection non trovata: {collection}", err=True)
            sys.exit(1)

        # Crea e avvia chat
        chat_interface = ChatInterface(collection_name=collection)
        chat_interface.run_interactive()

    except KeyboardInterrupt:
        click.echo("\n\nInterrotto.")
        sys.exit(0)
    except Exception as e:
        click.echo(f"\n❌ Errore: {e}", err=True)
        logger.exception("Errore durante chat")
        sys.exit(1)


@cli.command(name="list-collections")
def list_collections():
    """
    Lista tutte le collection disponibili.

    Esempio:
        python cli.py list-collections
    """
    try:
        vector_store = VectorStoreManager()
        collections = vector_store.list_collections()

        if not collections:
            click.echo("Nessuna collection trovata.")
            return

        click.echo(f"\n{'='*60}")
        click.echo("  COLLECTION")
        click.echo(f"{'='*60}\n")

        for coll in collections:
            info = vector_store.get_collection_info(coll)
            if info:
                click.echo(f"📦 {coll}")
                click.echo(f"   Documenti: {info['points_count']}")
                click.echo(f"   Vector size: {info['vector_size']}")
                click.echo(f"   Distance: {info['distance']}")
                click.echo()

        click.echo(f"Totale: {len(collections)} collection")

    except Exception as e:
        click.echo(f"❌ Errore: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    "--collection",
    "-c",
    help="Nome collection",
)
def stats(collection):
    """
    Mostra statistiche per una collection.

    Esempio:
        python cli.py stats --collection crawl_example_com_20260105
    """
    try:
        vector_store = VectorStoreManager()

        # Se collection non specificata, mostra lista
        if not collection:
            collections = vector_store.list_collections()

            if not collections:
                click.echo("❌ Nessuna collection trovata.", err=True)
                sys.exit(1)

            click.echo("\nCollection disponibili:\n")
            for i, coll in enumerate(collections, 1):
                click.echo(f"{i}. {coll}")

            choice = click.prompt("Seleziona collection (numero o nome)", type=str)

            if choice.isdigit():
                collection = collections[int(choice) - 1]
            else:
                collection = choice

        # Ottieni info
        info = vector_store.get_collection_info(collection)

        if not info:
            click.echo(f"❌ Collection non trovata: {collection}", err=True)
            sys.exit(1)

        # Mostra info
        click.echo(f"\n{'='*60}")
        click.echo("  STATISTICHE COLLECTION")
        click.echo(f"{'='*60}")
        click.echo(f"\nNome: {info['name']}")
        click.echo(f"Documenti (points): {info['points_count']}")
        click.echo(f"Vector size: {info['vector_size']}")
        click.echo(f"Distance metric: {info['distance']}")
        click.echo(f"Status: {info['status']}")

    except Exception as e:
        click.echo(f"❌ Errore: {e}", err=True)
        sys.exit(1)


@cli.command()
def setup():
    """
    Verifica e mostra configurazione.

    Esempio:
        python cli.py setup
    """
    click.echo(f"\n{'='*60}")
    click.echo("  CONFIGURAZIONE")
    click.echo(f"{'='*60}\n")

    # Check API keys
    click.echo("API Keys:")
    click.echo(f"  OpenAI: {'✓' if config.OPENAI_API_KEY else '✗ MANCANTE'}")
    click.echo(f"  Anthropic: {'✓' if config.ANTHROPIC_API_KEY else '✗ MANCANTE'}")

    # Check Qdrant
    click.echo(f"\nQdrant:")
    click.echo(f"  Modalità: {config.QDRANT_MODE}")
    click.echo(f"  Host: {config.QDRANT_HOST}:{config.QDRANT_PORT}")

    try:
        vector_store = VectorStoreManager()
        collections = vector_store.list_collections()
        click.echo(f"  Connessione: ✓")
        click.echo(f"  Collection: {len(collections)}")
    except Exception as e:
        click.echo(f"  Connessione: ✗ {e}")

    # Settings
    click.echo(f"\nImpostazioni:")
    click.echo(f"  Max pages: {config.MAX_PAGES}")
    click.echo(f"  Chunk size: {config.CHUNK_SIZE}")
    click.echo(f"  Chunk overlap: {config.CHUNK_OVERLAP}")
    click.echo(f"  Top-K retrieval: {config.TOP_K_RETRIEVAL}")
    click.echo(f"  Embedding model: {config.EMBEDDING_MODEL}")
    click.echo(f"  LLM model: {config.LLM_MODEL}")

    # Paths
    click.echo(f"\nPath:")
    click.echo(f"  Raw data: {config.RAW_DATA_PATH}")
    click.echo(f"  Qdrant data: {config.QDRANT_DATA_PATH}")

    click.echo()

    # Valida config
    try:
        config.validate_config()
        click.echo("✓ Configurazione valida!")
    except ValueError as e:
        click.echo(f"✗ Configurazione non valida:\n{e}", err=True)


if __name__ == "__main__":
    cli()

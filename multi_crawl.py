"""
Multi-Site Crawler per DataPizzaRouge.

Crawla multipli siti web e li unisce in una singola collection per RAG.

Uso:
    python multi_crawl.py sites.json
    python multi_crawl.py sites.json --crawl-only
    python multi_crawl.py sites.json --ingest-only
"""
import json
import sys
import subprocess
import argparse
from pathlib import Path
from urllib.parse import urlparse
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def load_config(config_file):
    """
    Carica configurazione da file JSON.

    Args:
        config_file: Path al file di configurazione

    Returns:
        Dict con configurazione
    """
    config_path = Path(config_file)

    if not config_path.exists():
        logger.error(f"File configurazione non trovato: {config_file}")
        sys.exit(1)

    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    # Valida configurazione
    if 'sites' not in config or not config['sites']:
        logger.error("Configurazione deve contenere almeno un sito in 'sites'")
        sys.exit(1)

    if 'collection_name' not in config:
        logger.error("Configurazione deve contenere 'collection_name'")
        sys.exit(1)

    return config


def crawl_sites(config, skip_crawl=False):
    """
    Fase 1: Crawl tutti i siti configurati.

    Args:
        config: Configurazione multi-crawl
        skip_crawl: Se True, salta questa fase

    Returns:
        Lista di domini crawlati con successo
    """
    if skip_crawl:
        logger.info("Crawl saltato (--ingest-only)")
        return []

    sites = config.get('sites', [])
    default_max_pages = config.get('max_pages_per_site', 100)

    print("\n" + "=" * 60)
    print("FASE 1: CRAWL SITI")
    print("=" * 60)
    print(f"Siti da crawlare: {len(sites)}\n")

    crawled_domains = []

    for i, site in enumerate(sites, 1):
        url = site.get('url')
        max_pages = site.get('max_pages', default_max_pages)

        if not url:
            logger.warning(f"Sito {i} senza URL, skip")
            continue

        # Estrai dominio
        domain = urlparse(url).netloc

        print(f"\n[{i}/{len(sites)}] Crawling: {url}")
        print(f"  Max pages: {max_pages}")

        # Comando crawl
        cmd = [
            sys.executable, 'cli.py', 'crawl', url,
            '--max-pages', str(max_pages)
        ]

        try:
            result = subprocess.run(cmd, check=False)

            if result.returncode == 0:
                print(f"  ✓ Crawl completato: {domain}")
                crawled_domains.append(domain)
            else:
                print(f"  ✗ Crawl fallito: {domain}")
                logger.error(f"Crawl fallito per {url} (exit code: {result.returncode})")

        except Exception as e:
            print(f"  ✗ Errore crawl: {domain}")
            logger.error(f"Errore durante crawl di {url}: {e}")

    print("\n" + "-" * 60)
    print(f"Crawl completati: {len(crawled_domains)}/{len(sites)}")
    print("-" * 60)

    return crawled_domains


def ingest_html(config, domains=None):
    """
    Fase 2: Ingestion HTML in collection unificata.

    Args:
        config: Configurazione multi-crawl
        domains: Lista domini da processare (se None, cerca tutti)

    Returns:
        Numero di domini processati con successo
    """
    collection_name = config.get('collection_name')

    print("\n" + "=" * 60)
    print("FASE 2: INGESTION HTML")
    print("=" * 60)
    print(f"Collection: {collection_name}\n")

    # Se domains non specificati, trova tutti in data/raw/
    if domains is None:
        raw_path = Path('data/raw')
        if not raw_path.exists():
            logger.error("Directory data/raw non trovata")
            return 0

        domains = [d.name for d in raw_path.iterdir() if d.is_dir()]
        logger.info(f"Trovati {len(domains)} domini in data/raw/")

    if not domains:
        logger.warning("Nessun dominio da processare")
        return 0

    processed = 0

    for i, domain in enumerate(domains, 1):
        # Verifica che il dominio esista
        domain_path = Path('data/raw') / domain

        if not domain_path.exists():
            print(f"\n[{i}/{len(domains)}] ⚠ Dominio non trovato: {domain}")
            continue

        # Conta pagine
        page_count = len(list(domain_path.glob('*.json')))

        print(f"\n[{i}/{len(domains)}] Ingestion HTML: {domain}")
        print(f"  Pagine: {page_count}")

        if i == 1:
            print(f"  → Creazione collection '{collection_name}'")
        else:
            print(f"  → Append a collection '{collection_name}'")

        # Comando ingestion (NO --force per append)
        cmd = [
            sys.executable, 'cli.py', 'ingest',
            '--domain', domain,
            '--collection', collection_name
        ]

        try:
            # Rispondi automaticamente "y" alla conferma
            result = subprocess.run(
                cmd,
                input="y\n",
                text=True,
                check=False
            )

            if result.returncode == 0:
                print(f"  ✓ Ingestion completata: {domain}")
                processed += 1
            else:
                print(f"  ✗ Ingestion fallita: {domain}")
                logger.error(f"Ingestion HTML fallita per {domain}")

        except Exception as e:
            print(f"  ✗ Errore ingestion: {domain}")
            logger.error(f"Errore durante ingestion HTML di {domain}: {e}")

    print("\n" + "-" * 60)
    print(f"Ingestion HTML completate: {processed}/{len(domains)}")
    print("-" * 60)

    return processed


def ingest_documents(config, domains=None):
    """
    Fase 3: Ingestion documenti in collection unificata.

    Args:
        config: Configurazione multi-crawl
        domains: Lista domini da processare (se None, cerca tutti)

    Returns:
        Numero di domini processati con successo
    """
    collection_name = config.get('collection_name')

    print("\n" + "=" * 60)
    print("FASE 3: INGESTION DOCUMENTI")
    print("=" * 60)
    print(f"Collection: {collection_name}\n")

    # Se domains non specificati, trova tutti in data/documents/
    if domains is None:
        docs_path = Path('data/documents')
        if not docs_path.exists():
            logger.warning("Directory data/documents non trovata")
            return 0

        domains = [d.name for d in docs_path.iterdir() if d.is_dir()]
        logger.info(f"Trovati {len(domains)} domini in data/documents/")

    if not domains:
        logger.warning("Nessun dominio con documenti")
        return 0

    processed = 0

    for i, domain in enumerate(domains, 1):
        docs_dir = Path('data/documents') / domain

        if not docs_dir.exists():
            print(f"\n[{i}/{len(domains)}] ⚠ Directory non trovata: {domain}")
            continue

        # Conta documenti (escludi registry files)
        doc_files = [
            f for f in docs_dir.glob('*.*')
            if f.is_file() and not f.name.startswith('.registry')
        ]

        if not doc_files:
            print(f"\n[{i}/{len(domains)}] ⚠ Nessun documento: {domain}")
            continue

        print(f"\n[{i}/{len(domains)}] Ingestion documenti: {domain}")
        print(f"  Documenti: {len(doc_files)}")
        print(f"  → Append a collection '{collection_name}'")

        # Comando ingestion documenti (NO --force per append)
        cmd = [
            sys.executable, 'cli.py', 'ingest-docs',
            '--dir', str(docs_dir),
            '--collection', collection_name
        ]

        try:
            # Rispondi automaticamente "y" alla conferma
            result = subprocess.run(
                cmd,
                input="y\n",
                text=True,
                check=False
            )

            if result.returncode == 0:
                print(f"  ✓ Ingestion documenti completata: {domain}")
                processed += 1
            else:
                print(f"  ✗ Ingestion documenti fallita: {domain}")
                logger.error(f"Ingestion documenti fallita per {domain}")

        except Exception as e:
            print(f"  ✗ Errore ingestion documenti: {domain}")
            logger.error(f"Errore durante ingestion documenti di {domain}: {e}")

    print("\n" + "-" * 60)
    print(f"Ingestion documenti completate: {processed}/{len(domains)}")
    print("-" * 60)

    return processed


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Multi-Site Crawler per DataPizzaRouge"
    )
    parser.add_argument(
        "config",
        help="File JSON con configurazione siti (es: sites.json)"
    )
    parser.add_argument(
        "--crawl-only",
        action="store_true",
        help="Esegui solo il crawl, salta ingestion"
    )
    parser.add_argument(
        "--ingest-only",
        action="store_true",
        help="Esegui solo ingestion, salta crawl"
    )

    args = parser.parse_args()

    # Carica configurazione
    config = load_config(args.config)

    collection_name = config.get('collection_name')
    sites_count = len(config.get('sites', []))

    print("\n" + "=" * 60)
    print("MULTI-SITE CRAWLER")
    print("=" * 60)
    print(f"Collection: {collection_name}")
    print(f"Siti configurati: {sites_count}")
    print("=" * 60)

    # Fase 1: Crawl
    crawled_domains = crawl_sites(config, skip_crawl=args.ingest_only)

    if args.crawl_only:
        print("\n✓ Crawl completato (--crawl-only, ingestion saltata)")
        return

    # Fase 2: Ingestion HTML
    html_processed = ingest_html(config, domains=crawled_domains if crawled_domains else None)

    # Fase 3: Ingestion Documenti
    docs_processed = ingest_documents(config, domains=crawled_domains if crawled_domains else None)

    # Riepilogo finale
    print("\n" + "=" * 60)
    print("MULTI-CRAWL COMPLETATO!")
    print("=" * 60)
    print(f"Collection: {collection_name}")
    print(f"Domini HTML processati: {html_processed}")
    print(f"Domini documenti processati: {docs_processed}")
    print("\nProssimo passo:")
    print(f"  python cli.py chat --collection {collection_name}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()

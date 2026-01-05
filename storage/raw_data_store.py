"""
Modulo per gestione dello storage dei dati raw crawlati.
Carica e gestisce i file JSON salvati dal crawler.
"""
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, Generator
from datetime import datetime

import config

logger = logging.getLogger(__name__)


class RawDataStore:
    """
    Gestisce l'accesso ai dati raw crawlati salvati come JSON.
    """

    def __init__(self, data_path: Optional[Path] = None):
        """
        Inizializza RawDataStore.

        Args:
            data_path: Path alla directory dei dati raw (default: config.RAW_DATA_PATH)
        """
        self.data_path = data_path or config.RAW_DATA_PATH
        self.data_path = Path(self.data_path)

        if not self.data_path.exists():
            self.data_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Creata directory dati: {self.data_path}")

    def list_domains(self) -> List[str]:
        """
        Lista tutti i domini presenti nello storage.

        Returns:
            Lista di nomi dominio
        """
        domains = []

        if not self.data_path.exists():
            return domains

        for domain_dir in self.data_path.iterdir():
            if domain_dir.is_dir():
                domains.append(domain_dir.name)

        return sorted(domains)

    def get_domain_path(self, domain: str) -> Path:
        """
        Ottiene il path della directory per un dominio.

        Args:
            domain: Nome del dominio

        Returns:
            Path alla directory del dominio
        """
        return self.data_path / domain

    def count_pages(self, domain: str) -> int:
        """
        Conta il numero di pagine per un dominio.

        Args:
            domain: Nome del dominio

        Returns:
            Numero di pagine
        """
        domain_path = self.get_domain_path(domain)

        if not domain_path.exists():
            return 0

        return len(list(domain_path.glob("*.json")))

    def load_page(self, domain: str, filename: str) -> Optional[Dict]:
        """
        Carica una singola pagina.

        Args:
            domain: Nome del dominio
            filename: Nome del file JSON

        Returns:
            Dict con i dati della pagina, o None se non trovato
        """
        file_path = self.get_domain_path(domain) / filename

        if not file_path.exists():
            logger.warning(f"File non trovato: {file_path}")
            return None

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data
        except Exception as e:
            logger.error(f"Errore caricando {file_path}: {e}")
            return None

    def iter_pages(self, domain: str) -> Generator[Dict, None, None]:
        """
        Itera su tutte le pagine di un dominio.

        Args:
            domain: Nome del dominio

        Yields:
            Dict con i dati di ogni pagina
        """
        domain_path = self.get_domain_path(domain)

        if not domain_path.exists():
            logger.warning(f"Directory non trovata per dominio: {domain}")
            return

        json_files = sorted(domain_path.glob("*.json"))
        total_files = len(json_files)

        logger.info(f"Trovati {total_files} file JSON per dominio {domain}")

        for i, json_file in enumerate(json_files, 1):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                if i % 100 == 0:
                    logger.info(f"Caricati {i}/{total_files} file")

                yield data

            except Exception as e:
                logger.error(f"Errore caricando {json_file}: {e}")
                continue

    def load_all_pages(self, domain: str) -> List[Dict]:
        """
        Carica tutte le pagine di un dominio in memoria.
        ATTENZIONE: Può usare molta memoria per domini grandi.

        Args:
            domain: Nome del dominio

        Returns:
            Lista di dict con i dati delle pagine
        """
        pages = list(self.iter_pages(domain))
        logger.info(f"Caricati {len(pages)} pagine per dominio {domain}")
        return pages

    def get_domain_stats(self, domain: str) -> Dict:
        """
        Ottiene statistiche per un dominio.

        Args:
            domain: Nome del dominio

        Returns:
            Dict con statistiche
        """
        domain_path = self.get_domain_path(domain)

        if not domain_path.exists():
            return {
                "domain": domain,
                "exists": False,
                "page_count": 0,
            }

        page_count = self.count_pages(domain)

        # Calcola dimensione totale
        total_size = 0
        for json_file in domain_path.glob("*.json"):
            total_size += json_file.stat().st_size

        # Trova date primo e ultimo crawl
        crawl_dates = []
        for data in self.iter_pages(domain):
            if "crawled_at" in data:
                crawl_dates.append(data["crawled_at"])

        first_crawl = min(crawl_dates) if crawl_dates else None
        last_crawl = max(crawl_dates) if crawl_dates else None

        return {
            "domain": domain,
            "exists": True,
            "page_count": page_count,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "first_crawl": first_crawl,
            "last_crawl": last_crawl,
        }

    def delete_domain(self, domain: str) -> bool:
        """
        Elimina tutti i dati per un dominio.

        Args:
            domain: Nome del dominio

        Returns:
            True se eliminato con successo
        """
        domain_path = self.get_domain_path(domain)

        if not domain_path.exists():
            logger.warning(f"Dominio non trovato: {domain}")
            return False

        try:
            # Elimina tutti i file JSON
            for json_file in domain_path.glob("*.json"):
                json_file.unlink()

            # Elimina directory
            domain_path.rmdir()

            logger.info(f"Eliminato dominio: {domain}")
            return True

        except Exception as e:
            logger.error(f"Errore eliminando dominio {domain}: {e}")
            return False


def get_store(data_path: Optional[Path] = None) -> RawDataStore:
    """
    Factory function per creare RawDataStore.

    Args:
        data_path: Path opzionale

    Returns:
        RawDataStore instance
    """
    return RawDataStore(data_path)


if __name__ == "__main__":
    # Test RawDataStore
    import sys

    logging.basicConfig(level=logging.INFO)

    store = get_store()

    print("=== Test Raw Data Store ===")
    print(f"Data path: {store.data_path}")

    domains = store.list_domains()
    print(f"\nDomini trovati: {len(domains)}")

    for domain in domains:
        stats = store.get_domain_stats(domain)
        print(f"\nDominio: {domain}")
        print(f"  Pagine: {stats['page_count']}")
        print(f"  Dimensione: {stats['total_size_mb']} MB")
        print(f"  Primo crawl: {stats['first_crawl']}")
        print(f"  Ultimo crawl: {stats['last_crawl']}")

        # Mostra prima pagina
        print(f"\n  Prima pagina:")
        for i, page in enumerate(store.iter_pages(domain)):
            print(f"    URL: {page.get('url')}")
            print(f"    Titolo: {page.get('title')}")
            break  # Solo prima pagina

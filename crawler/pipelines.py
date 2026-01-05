"""
Scrapy pipelines per processare e salvare item crawlati.
"""
import json
import logging
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse, quote
import hashlib

logger = logging.getLogger(__name__)


class JsonWriterPipeline:
    """
    Pipeline per salvare item crawlati come JSON file.
    Ogni pagina viene salvata in: data/raw/{domain}/{url_hash}.json
    """

    def __init__(self):
        self.items_processed = 0

    def open_spider(self, spider):
        """Chiamato quando spider si apre."""
        logger.info(f"JsonWriterPipeline aperto per spider: {spider.name}")
        self.items_processed = 0

    def close_spider(self, spider):
        """Chiamato quando spider si chiude."""
        logger.info(f"JsonWriterPipeline chiuso. Item processati: {self.items_processed}")

    def process_item(self, item, spider):
        """
        Processa e salva item.

        Args:
            item: Item da salvare
            spider: Spider che ha generato l'item

        Returns:
            Item processato
        """
        try:
            # Estrai dominio dall'URL
            parsed_url = urlparse(item["url"])
            domain = parsed_url.netloc

            # Crea hash dell'URL per nome file
            url_hash = hashlib.md5(item["url"].encode()).hexdigest()

            # Crea directory per il dominio
            domain_dir = Path("data") / "raw" / domain
            domain_dir.mkdir(parents=True, exist_ok=True)

            # Path del file JSON
            json_file = domain_dir / f"{url_hash}.json"

            # Salva item come JSON
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(item, f, ensure_ascii=False, indent=2)

            self.items_processed += 1

            if self.items_processed % 10 == 0:
                logger.info(f"Salvati {self.items_processed} item")

            logger.debug(f"Salvato: {json_file}")

        except Exception as e:
            logger.error(f"Errore salvando item {item.get('url')}: {e}")

        return item


class StatsCollectorPipeline:
    """Pipeline per collezionare statistiche durante il crawl."""

    def __init__(self):
        self.stats = {
            "total_pages": 0,
            "total_bytes": 0,
            "domains": set(),
            "status_codes": {},
        }

    def open_spider(self, spider):
        logger.info("StatsCollectorPipeline aperto")

    def close_spider(self, spider):
        """Stampa statistiche finali."""
        logger.info("=" * 50)
        logger.info("STATISTICHE CRAWL")
        logger.info("=" * 50)
        logger.info(f"Pagine totali: {self.stats['total_pages']}")
        logger.info(f"Byte totali: {self.stats['total_bytes']:,}")
        logger.info(f"Domini crawlati: {len(self.stats['domains'])}")
        logger.info(f"Status codes: {dict(self.stats['status_codes'])}")
        logger.info("=" * 50)

    def process_item(self, item, spider):
        """Aggiorna statistiche."""
        self.stats["total_pages"] += 1
        self.stats["total_bytes"] += len(item.get("html", ""))

        # Estrai dominio
        parsed_url = urlparse(item["url"])
        self.stats["domains"].add(parsed_url.netloc)

        # Conta status codes
        status = item.get("status_code", 0)
        self.stats["status_codes"][status] = self.stats["status_codes"].get(status, 0) + 1

        return item

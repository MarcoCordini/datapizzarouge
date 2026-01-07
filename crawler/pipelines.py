"""
Scrapy pipelines per processare e salvare item crawlati.
"""
import json
import logging
import shutil
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse, quote
import hashlib
from scrapy.pipelines.files import FilesPipeline
from scrapy.http import Request

logger = logging.getLogger(__name__)


class DomainFilesPipeline(FilesPipeline):
    """
    Custom FilesPipeline che organizza file per dominio.
    Invece di salvare in data/documents/full/<hash>,
    salva in data/documents/{domain}/{filename}.
    """

    def file_path(self, request, response=None, info=None, *, item=None):
        """
        Customizza path del file scaricato.
        Organizza per dominio: {domain}/{filename}

        Args:
            request: Request Scrapy
            response: Response (opzionale)
            info: Info (opzionale)
            item: Item Scrapy

        Returns:
            Path relativo dove salvare il file
        """
        # Estrai dominio dall'URL
        parsed_url = urlparse(request.url)
        domain = parsed_url.netloc

        # Estrai nome file dall'URL
        file_name = request.url.split("/")[-1]

        # Se nome file vuoto o generico, usa hash
        if not file_name or file_name in ["", "download", "file"]:
            # Usa hash dell'URL per nome univoco
            url_hash = hashlib.md5(request.url.encode()).hexdigest()[:8]
            # Determina estensione dall'URL o Content-Type
            ext = Path(parsed_url.path).suffix or ".bin"
            file_name = f"document_{url_hash}{ext}"

        # Costruisci path: {domain}/{filename}
        file_path = Path(domain) / file_name

        logger.debug(f"File path per {request.url}: {file_path}")

        return str(file_path)

    def get_media_requests(self, item, info):
        """
        Genera Request per scaricare file.
        Chiamato da Scrapy quando item ha 'file_urls'.

        Args:
            item: Item Scrapy
            info: Spider info

        Yields:
            Request per ogni file da scaricare
        """
        # Scarica solo se è un documento
        if item.get("metadata", {}).get("is_document", False):
            file_urls = item.get("file_urls", [])
            for file_url in file_urls:
                # Aggiungi metadata alla request per usarli in file_path
                yield Request(
                    url=file_url,
                    meta={"item": item}  # Passa item nel meta
                )

    def item_completed(self, results, item, info):
        """
        Chiamato quando tutti i file sono stati scaricati.

        Args:
            results: Lista di (success, file_info) tuple
            item: Item Scrapy
            info: Spider info

        Returns:
            Item modificato con info sui file scaricati
        """
        # Estrai info sui file scaricati con successo
        file_paths = []
        for success, file_info in results:
            if success:
                file_paths.append(file_info)
                logger.info(f"File scaricato: {file_info['path']}")
            else:
                logger.error(f"Errore scaricando file: {file_info}")

        # Aggiungi info file all'item
        item["files"] = file_paths

        return item


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


class DocumentHashPipeline:
    """
    Pipeline per gestire deduplicazione documenti tramite hash.
    Calcola hash SHA256 dei file scaricati e mantiene un registry.
    """

    def __init__(self):
        self.registry = {}
        self.registry_path = None
        self.documents_dir = None
        self.duplicates_skipped = 0
        self.documents_added = 0

    def open_spider(self, spider):
        """Chiamato quando spider si apre."""
        logger.info("DocumentHashPipeline aperto")

        # Determina percorso documents dir dal primo item
        # (verrà impostato nel primo process_item)
        self.duplicates_skipped = 0
        self.documents_added = 0

    def close_spider(self, spider):
        """Chiamato quando spider si chiude."""
        # Salva registry finale con backup
        if self.registry_path and self.registry:
            self._save_registry_with_backup()

        logger.info("=" * 50)
        logger.info("DOCUMENT HASH PIPELINE STATS")
        logger.info("=" * 50)
        logger.info(f"Documenti aggiunti: {self.documents_added}")
        logger.info(f"Duplicati skippati: {self.duplicates_skipped}")
        logger.info(f"Totale nel registry: {len(self.registry)}")
        logger.info("=" * 50)

    def process_item(self, item, spider):
        """
        Processa item: calcola hash e gestisce deduplicazione.

        Args:
            item: Item da processare
            spider: Spider che ha generato l'item

        Returns:
            Item processato (modificato se è un documento)
        """
        # Processa solo documenti
        is_document = item.get("metadata", {}).get("is_document", False)

        if not is_document:
            return item

        # Inizializza registry path al primo documento
        if self.registry_path is None:
            parsed_url = urlparse(item["url"])
            domain = parsed_url.netloc
            self.documents_dir = Path("data") / "documents" / domain
            self.documents_dir.mkdir(parents=True, exist_ok=True)
            self.registry_path = self.documents_dir / ".registry.json"

            # Carica registry esistente se presente
            self._load_registry()

        try:
            # Calcola hash del documento
            # NOTA: FilesPipeline salva il file, qui calcoliamo hash dopo download
            file_paths = item.get("files", [])

            if not file_paths:
                # File non ancora scaricato, FilesPipeline lo farà
                return item

            # Prendi il primo file (dovrebbe essercene solo uno)
            file_info = file_paths[0]
            file_path = Path("data") / "documents" / file_info["path"]

            if not file_path.exists():
                logger.warning(f"File non trovato: {file_path}")
                return item

            # Calcola hash SHA256
            file_hash = self._calculate_file_hash(file_path)

            # Controlla se è duplicato
            if file_hash in self.registry:
                logger.info(f"Duplicato rilevato! Hash: {file_hash[:8]}...")
                logger.info(f"  Originale: {self.registry[file_hash]['file_name']}")
                logger.info(f"  URL corrente: {item['url']}")

                # Aggiungi reference al documento esistente
                self.registry[file_hash]["references"].append(item["url"])
                self.registry[file_hash]["reference_count"] += 1

                # Aggiorna metadata dell'item
                item["metadata"]["file_hash"] = file_hash
                item["metadata"]["is_duplicate"] = True
                item["metadata"]["original_path"] = self.registry[file_hash]["file_path"]

                self.duplicates_skipped += 1

                # Cancella il file duplicato (FilesPipeline l'ha salvato)
                try:
                    file_path.unlink()
                    logger.debug(f"File duplicato cancellato: {file_path}")
                except Exception as e:
                    logger.warning(f"Impossibile cancellare duplicato: {e}")

            else:
                # Nuovo documento
                logger.info(f"Nuovo documento: {item['metadata']['file_name']}")
                logger.info(f"  Hash: {file_hash[:8]}...")

                # Aggiungi al registry
                self.registry[file_hash] = {
                    "file_path": str(file_path),
                    "file_name": item["metadata"]["file_name"],
                    "file_size": item["metadata"].get("file_size_kb", 0),
                    "download_date": datetime.utcnow().isoformat(),
                    "references": [item["url"]],
                    "reference_count": 1,
                }

                # Aggiorna metadata dell'item
                item["metadata"]["file_hash"] = file_hash
                item["metadata"]["is_duplicate"] = False

                self.documents_added += 1

            # Salva registry ogni 5 documenti
            if (self.documents_added + self.duplicates_skipped) % 5 == 0:
                self._save_registry_with_backup()

        except Exception as e:
            logger.error(f"Errore in DocumentHashPipeline per {item.get('url')}: {e}")
            import traceback
            traceback.print_exc()

        return item

    def _calculate_file_hash(self, file_path: Path) -> str:
        """
        Calcola hash SHA256 di un file.

        Args:
            file_path: Path del file

        Returns:
            Hash esadecimale
        """
        sha256_hash = hashlib.sha256()

        with open(file_path, "rb") as f:
            # Leggi in chunk per file grandi
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)

        return sha256_hash.hexdigest()

    def _load_registry(self):
        """Carica registry esistente se presente."""
        if self.registry_path and self.registry_path.exists():
            try:
                with open(self.registry_path, "r", encoding="utf-8") as f:
                    self.registry = json.load(f)
                logger.info(f"Registry caricato: {len(self.registry)} documenti esistenti")
            except Exception as e:
                logger.error(f"Errore caricando registry: {e}")
                self.registry = {}

    def _save_registry_with_backup(self):
        """Salva registry con backup automatico."""
        if not self.registry_path:
            return

        try:
            # 1. Backup del registry corrente
            if self.registry_path.exists():
                backup_path = self.registry_path.parent / ".registry.backup.json"
                shutil.copy(self.registry_path, backup_path)
                logger.debug("Registry backup creato")

                # 2. Backup storico (opzionale)
                history_dir = self.registry_path.parent / ".registry_history"
                history_dir.mkdir(exist_ok=True)

                timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
                historical_backup = history_dir / f"registry_{timestamp}.json"
                shutil.copy(self.registry_path, historical_backup)

                # 3. Cleanup vecchi backup (mantieni ultimi 10)
                backups = sorted(history_dir.glob("registry_*.json"))
                if len(backups) > 10:
                    for old_backup in backups[:-10]:
                        old_backup.unlink()
                        logger.debug(f"Backup vecchio rimosso: {old_backup.name}")

            # 4. Salva nuovo registry
            with open(self.registry_path, "w", encoding="utf-8") as f:
                json.dump(self.registry, f, ensure_ascii=False, indent=2)

            logger.debug(f"Registry salvato: {len(self.registry)} documenti")

        except Exception as e:
            logger.error(f"Errore salvando registry: {e}")

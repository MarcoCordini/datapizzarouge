"""
Spider Scrapy per crawlare tutte le pagine di un dominio.
Usa CrawlSpider con LinkExtractor per seguire automaticamente i link.
Estrae manualmente link a documenti da ogni pagina HTML.
"""
import logging
import hashlib
import re
from datetime import datetime
from urllib.parse import urlparse
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from scrapy import Request
from scrapy.exceptions import CloseSpider

logger = logging.getLogger(__name__)


class DomainSpider(CrawlSpider):
    """
    Spider per crawlare tutte le pagine accessibili di un dominio.

    Uso:
        scrapy crawl domain -a start_url=https://example.com -a max_pages=500
    """

    name = "domain"
    custom_settings = {
        "ROBOTSTXT_OBEY": True,
        "CONCURRENT_REQUESTS": 16,
        "DOWNLOAD_DELAY": 0.5,
        "COOKIES_ENABLED": False,
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_START_DELAY": 0.5,
        "AUTOTHROTTLE_MAX_DELAY": 10.0,
        "DEPTH_LIMIT": 10,
        "CLOSESPIDER_ITEMCOUNT": 1000,
    }

    def __init__(self, start_url=None, max_pages=None, *args, **kwargs):
        """
        Inizializza lo spider con URL di partenza dinamico.

        Args:
            start_url: URL da cui iniziare il crawling
            max_pages: Numero massimo di pagine da crawlare (opzionale)
        """
        super(DomainSpider, self).__init__(*args, **kwargs)

        if not start_url:
            raise ValueError("start_url è richiesto. Usa -a start_url=https://example.com")

        # Parse URL per estrarre dominio
        parsed_url = urlparse(start_url)
        domain = parsed_url.netloc

        # Configurazione dinamica
        self.start_urls = [start_url]
        self.allowed_domains = [domain]

        # Salva max_pages come attributo di istanza per controllo manuale
        self.max_pages_limit = int(max_pages) if max_pages else None

        logger.info(f"Spider inizializzato per dominio: {domain}")
        logger.info(f"Start URL: {start_url}")
        if self.max_pages_limit:
            logger.info(f"Max pages (HTML): {self.max_pages_limit}")
        else:
            logger.info(f"Max pages: Illimitato (default: {self.custom_settings['CLOSESPIDER_ITEMCOUNT']} items totali)")

        # Regole per il crawling
        self.rules = (
            # Regola 1: Cattura documenti (PDF, DOC, XLS, ecc.)
            Rule(
                LinkExtractor(
                    allow_domains=self.allowed_domains,
                    allow=(
                        r"\.pdf$",
                        r"\.doc$",
                        r"\.docx$",
                        r"\.xls$",
                        r"\.xlsx$",
                        r"\.ppt$",
                        r"\.pptx$",
                        r"\.odt$",
                        r"\.ods$",
                        r"\.odp$",
                    ),
                    unique=True,
                ),
                callback="parse_document",
                follow=False,  # Non seguire link dentro i documenti
            ),
            # Regola 2: Cattura pagine HTML (escludendo file binari/media)
            Rule(
                LinkExtractor(
                    allow_domains=self.allowed_domains,
                    deny=(
                        # Skip file binari
                        r"\.pdf$",
                        r"\.jpg$",
                        r"\.jpeg$",
                        r"\.png$",
                        r"\.gif$",
                        r"\.zip$",
                        r"\.tar$",
                        r"\.gz$",
                        r"\.exe$",
                        r"\.dmg$",
                        # Skip file multimediali
                        r"\.mp3$",
                        r"\.mp4$",
                        r"\.avi$",
                        r"\.mov$",
                        # Skip documenti (gestiti dalla regola 1)
                        r"\.doc$",
                        r"\.docx$",
                        r"\.xls$",
                        r"\.xlsx$",
                        r"\.ppt$",
                        r"\.pptx$",
                        r"\.odt$",
                        r"\.ods$",
                        r"\.odp$",
                    ),
                    unique=True,
                ),
                callback="parse_page",
                follow=True,
            ),
        )

        # Re-initialize rules dopo la definizione
        self._compile_rules()

        # Statistiche
        self.pages_crawled = 0
        self.documents_found = 0

    def parse_page(self, response):
        """
        Parse una pagina HTML ed estrae contenuto e metadata.
        Estrae anche link a documenti e genera Request per scaricarli.

        Args:
            response: Risposta HTTP di Scrapy

        Yields:
            dict: Item con contenuto della pagina
            Request: Request per documenti trovati
        """
        # Controlla se raggiunto limite pagine HTML
        if self.max_pages_limit and self.pages_crawled >= self.max_pages_limit:
            logger.warning(f"Raggiunto limite di {self.max_pages_limit} pagine HTML. Chiusura spider.")
            raise CloseSpider(f"Raggiunto limite di {self.max_pages_limit} pagine HTML")

        self.pages_crawled += 1
        logger.info(f"Crawling [{self.pages_crawled}/{self.max_pages_limit or '∞'}]: {response.url}")

        # Estrai metadata dalla pagina
        title = response.css("title::text").get()
        if title:
            title = title.strip()

        meta_description = response.css('meta[name="description"]::attr(content)').get()
        meta_keywords = response.css('meta[name="keywords"]::attr(content)').get()
        meta_author = response.css('meta[name="author"]::attr(content)').get()

        # Estrai headings per context
        h1_tags = response.css("h1::text").getall()
        h2_tags = response.css("h2::text").getall()

        # Costruisci item per la pagina
        item = {
            "url": response.url,
            "title": title or "",
            "html": response.text,
            "status_code": response.status,
            "crawled_at": datetime.utcnow().isoformat(),
            "metadata": {
                "description": meta_description or "",
                "keywords": meta_keywords or "",
                "author": meta_author or "",
                "h1_tags": [h.strip() for h in h1_tags if h.strip()],
                "h2_tags": [h.strip() for h in h2_tags if h.strip()],
                "domain": self.allowed_domains[0],
            },
        }

        yield item

        # Estrai link a documenti dalla pagina
        # Cerca tutti i link che terminano con estensioni documento
        doc_extensions = (
            r"\.pdf$", r"\.doc$", r"\.docx$", r"\.xls$", r"\.xlsx$",
            r"\.ppt$", r"\.pptx$", r"\.odt$", r"\.ods$", r"\.odp$"
        )

        doc_pattern = "|".join(doc_extensions)

        # Estrai tutti gli href dalla pagina
        all_links = response.css("a::attr(href)").getall()

        for link in all_links:
            # Converti link relativo in assoluto
            absolute_url = response.urljoin(link)

            # Controlla se è un documento
            if re.search(doc_pattern, absolute_url, re.IGNORECASE):
                # Verifica che sia del dominio consentito
                parsed = urlparse(absolute_url)
                if parsed.netloc in self.allowed_domains:
                    logger.debug(f"Documento trovato in pagina: {absolute_url}")
                    # Genera Request per il documento
                    yield Request(
                        url=absolute_url,
                        callback=self.parse_document,
                        dont_filter=False,  # Usa filtering normale
                        priority=10  # Alta priorità per documenti
                    )

    def parse_document(self, response):
        """
        Parse un documento (PDF, DOC, XLS, ecc.) ed estrae metadati.
        FilesPipeline scaricherà automaticamente il documento.

        Args:
            response: Risposta HTTP di Scrapy per il documento

        Yields:
            dict: Item con metadati del documento
        """
        self.pages_crawled += 1
        self.documents_found += 1
        logger.info(f"Documento trovato [{self.documents_found}]: {response.url}")

        # Estrai estensione e tipo documento
        url_path = response.url.lower()
        doc_type = None
        if url_path.endswith(".pdf"):
            doc_type = "PDF"
        elif url_path.endswith((".doc", ".docx")):
            doc_type = "Word"
        elif url_path.endswith((".xls", ".xlsx")):
            doc_type = "Excel"
        elif url_path.endswith((".ppt", ".pptx")):
            doc_type = "PowerPoint"
        elif url_path.endswith((".odt", ".ods", ".odp")):
            doc_type = "OpenDocument"
        else:
            doc_type = "Document"

        # Estrai dimensione dal Content-Length se disponibile
        file_size = response.headers.get("Content-Length")
        if file_size:
            file_size = int(file_size.decode("utf-8"))
            # Converti in KB
            file_size_kb = file_size / 1024
        else:
            file_size_kb = None

        # Estrai nome file dall'URL
        file_name = response.url.split("/")[-1]

        # Se file_name è vuoto o troppo generico, usa hash dell'URL
        if not file_name or file_name in ["", "download", "file"]:
            url_hash = hashlib.md5(response.url.encode()).hexdigest()[:8]
            # Determina estensione dal doc_type
            ext_map = {
                "PDF": ".pdf",
                "Word": ".docx",
                "Excel": ".xlsx",
                "PowerPoint": ".pptx",
                "OpenDocument": ".odt"
            }
            extension = ext_map.get(doc_type, ".bin")
            file_name = f"document_{url_hash}{extension}"

        # Costruisci item per il documento
        item = {
            "url": response.url,
            "title": file_name,
            "html": "",  # Non c'è HTML per i documenti
            "status_code": response.status,
            "crawled_at": datetime.utcnow().isoformat(),
            "file_urls": [response.url],  # FilesPipeline scaricherà da qui
            "metadata": {
                "description": f"{doc_type} document",
                "keywords": "",
                "author": "",
                "h1_tags": [],
                "h2_tags": [],
                "domain": self.allowed_domains[0],
                "document_type": doc_type,
                "file_name": file_name,
                "file_size_kb": file_size_kb,
                "is_document": True,  # Flag per identificare i documenti
            },
        }

        yield item

    def parse_start_url(self, response):
        """Override per processare anche lo start URL."""
        return self.parse_page(response)

    def closed(self, reason):
        """Chiamato quando lo spider si chiude."""
        logger.info("=" * 60)
        logger.info("SPIDER CHIUSO")
        logger.info("=" * 60)
        logger.info(f"Motivo: {reason}")
        logger.info(f"Pagine HTML crawlate: {self.pages_crawled}")
        if self.max_pages_limit:
            logger.info(f"Limite impostato: {self.max_pages_limit}")
        logger.info(f"Documenti trovati: {self.documents_found}")
        logger.info("=" * 60)

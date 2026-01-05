"""
Spider Scrapy per crawlare tutte le pagine di un dominio.
Usa CrawlSpider con LinkExtractor per seguire automaticamente i link.
"""
import logging
from datetime import datetime
from urllib.parse import urlparse
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from scrapy import Request

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

        # Override max_pages se specificato
        if max_pages:
            self.custom_settings["CLOSESPIDER_ITEMCOUNT"] = int(max_pages)

        logger.info(f"Spider inizializzato per dominio: {domain}")
        logger.info(f"Start URL: {start_url}")
        logger.info(f"Max pages: {self.custom_settings['CLOSESPIDER_ITEMCOUNT']}")

        # Regole per il crawling
        self.rules = (
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
                        # Skip documenti
                        r"\.doc$",
                        r"\.docx$",
                        r"\.xls$",
                        r"\.xlsx$",
                        r"\.ppt$",
                        r"\.pptx$",
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

    def parse_page(self, response):
        """
        Parse una pagina HTML ed estrae contenuto e metadata.

        Args:
            response: Risposta HTTP di Scrapy

        Yields:
            dict: Item con contenuto della pagina
        """
        self.pages_crawled += 1
        logger.info(f"Crawling [{self.pages_crawled}]: {response.url}")

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

        # Costruisci item
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

    def parse_start_url(self, response):
        """Override per processare anche lo start URL."""
        return self.parse_page(response)

    def closed(self, reason):
        """Chiamato quando lo spider si chiude."""
        logger.info(f"Spider chiuso. Motivo: {reason}")
        logger.info(f"Totale pagine crawlate: {self.pages_crawled}")

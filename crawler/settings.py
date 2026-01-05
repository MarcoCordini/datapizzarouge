"""
Impostazioni Scrapy per DataPizzaRouge crawler.
"""
import sys
from pathlib import Path

# Aggiungi la directory root al path per import
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

import config

# === BASIC SETTINGS ===
BOT_NAME = "datapizzarouge_crawler"
SPIDER_MODULES = ["crawler.spiders"]
NEWSPIDER_MODULE = "crawler.spiders"

# === CRAWL RESPONSIBLY ===
# Rispetta robots.txt
ROBOTSTXT_OBEY = True

# User agent
USER_AGENT = config.USER_AGENT

# Concurrent requests
CONCURRENT_REQUESTS = config.CONCURRENT_REQUESTS
CONCURRENT_REQUESTS_PER_DOMAIN = 8
CONCURRENT_REQUESTS_PER_IP = 0

# Download delay (secondi tra richieste allo stesso dominio)
DOWNLOAD_DELAY = config.DOWNLOAD_DELAY

# === AUTOTHROTTLE ===
# Throttling automatico per crawling educato
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 0.5
AUTOTHROTTLE_MAX_DELAY = 10.0
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
AUTOTHROTTLE_DEBUG = False

# === COOKIES ===
COOKIES_ENABLED = False

# === TELNET CONSOLE ===
TELNETCONSOLE_ENABLED = False

# === ITEM PIPELINES ===
ITEM_PIPELINES = {
    "crawler.pipelines.JsonWriterPipeline": 300,
}

# === DEPTH SETTINGS ===
DEPTH_LIMIT = config.DEPTH_LIMIT
DEPTH_PRIORITY = 1
SCHEDULER_DISK_QUEUE = "scrapy.squeues.PickleFifoDiskQueue"
SCHEDULER_MEMORY_QUEUE = "scrapy.squeues.FifoMemoryQueue"

# === LIMITS ===
# Chiudi spider dopo N item (safety limit)
CLOSESPIDER_ITEMCOUNT = config.MAX_PAGES

# Timeout per richieste
DOWNLOAD_TIMEOUT = 30

# === MEMORY USAGE ===
MEMUSAGE_ENABLED = True
MEMUSAGE_LIMIT_MB = 512
MEMUSAGE_WARNING_MB = 384

# === HTTPCACHE ===
# Cache per sviluppo (commentare in produzione)
# HTTPCACHE_ENABLED = True
# HTTPCACHE_EXPIRATION_SECS = 3600
# HTTPCACHE_DIR = "httpcache"
# HTTPCACHE_IGNORE_HTTP_CODES = [500, 502, 503, 504, 408, 429]

# === RETRY SETTINGS ===
RETRY_ENABLED = True
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429]

# === LOG SETTINGS ===
LOG_LEVEL = config.LOG_LEVEL
LOG_FILE = None  # None = output to console

# === EXTENSIONS ===
EXTENSIONS = {
    "scrapy.extensions.telnet.TelnetConsole": None,
}

# === REQUEST FINGERPRINTER ===
REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
FEED_EXPORT_ENCODING = "utf-8"

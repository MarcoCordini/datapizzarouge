# Ottimizzazione Crawling e Gestione Memoria

Guida per ottimizzare il crawling Scrapy e gestire l'uso della memoria.

---

## 🔧 Modifiche Applicate

### 1. Limiti Memoria Aumentati
```python
MEMUSAGE_LIMIT_MB = 2048      # Da 512MB a 2GB
MEMUSAGE_WARNING_MB = 1536    # Warning a 1.5GB
```

### 2. Richieste Concorrenti Ridotte
```python
CONCURRENT_REQUESTS = 8                # Ridotto per memoria
CONCURRENT_REQUESTS_PER_DOMAIN = 4    # Da 8 a 4
```

### 3. Garbage Collection Aggressivo
```python
gc.set_threshold(700, 10, 10)  # Libera memoria più frequentemente
```

---

## 📊 Strategie per Crawl Grandi

### Opzione 1: Crawl in Batch

Invece di crawlare 1000 pagine in una volta, dividi in batch:

```bash
# Batch 1: Prime 200 pagine
python cli.py crawl https://example.com --max-pages 200

# Batch 2: Altre 200 (modifica start URL o usa exclude patterns)
python cli.py crawl https://example.com/docs --max-pages 200

# Batch 3: ...
python cli.py crawl https://example.com/blog --max-pages 200

# Poi fai ingestion di tutto insieme
python cli.py ingest --domain example.com --collection example_full
```

### Opzione 2: Crawl Incrementale

Usa una collection con nome fisso e aggiorna periodicamente:

```bash
# Setup iniziale
python cli.py crawl https://docs.company.com --max-pages 100
python cli.py ingest --domain docs.company.com --collection company_docs

# Aggiornamento settimanale (sovrascrive)
python cli.py crawl https://docs.company.com --max-pages 100
python cli.py ingest --domain docs.company.com --collection company_docs --force
```

### Opzione 3: Crawl Selettivo

Crawla solo sezioni specifiche del sito:

```bash
# Solo documentazione
python cli.py crawl https://example.com/docs --max-pages 500

# Solo blog
python cli.py crawl https://example.com/blog --max-pages 200

# Solo API reference
python cli.py crawl https://example.com/api --max-pages 300
```

---

## 🐏 Verifica RAM Disponibile

Prima di crawlare, controlla la memoria del server:

```bash
# RAM totale e disponibile
free -h

# Output esempio:
#               total        used        free      shared  buff/cache   available
# Mem:           7.7Gi       2.1Gi       3.8Gi        89Mi       1.8Gi       5.3Gi
# Swap:          2.0Gi          0B       2.0Gi

# Se available < 2GB, usa batch più piccoli
```

### Raccomandazioni RAM:

| Pagine da Crawlare | RAM Consigliata | Limite Scrapy |
|--------------------|--------------------|---------------|
| < 50 pagine | 512 MB | 512 MB |
| 50-200 pagine | 1 GB | 1024 MB |
| 200-500 pagine | 2 GB | 2048 MB |
| 500-1000 pagine | 4 GB | 4096 MB |
| > 1000 pagine | 8 GB+ | 4096-8192 MB |

---

## 🔧 Configurazioni Avanzate

### Per Server con Poca RAM (< 2GB)

Modifica `crawler/settings.py`:

```python
# Limita memoria
MEMUSAGE_LIMIT_MB = 1024  # 1GB
MEMUSAGE_WARNING_MB = 768

# Riduci concurrency
CONCURRENT_REQUESTS = 4
CONCURRENT_REQUESTS_PER_DOMAIN = 2

# Aumenta delay
DOWNLOAD_DELAY = 1.0

# Batch più piccoli nel CLI
# python cli.py crawl URL --max-pages 50
```

### Per Server con Molta RAM (> 8GB)

Puoi aumentare performance:

```python
# Più memoria disponibile
MEMUSAGE_LIMIT_MB = 4096  # 4GB
MEMUSAGE_WARNING_MB = 3072

# Più richieste parallele
CONCURRENT_REQUESTS = 16
CONCURRENT_REQUESTS_PER_DOMAIN = 8

# Delay minimo
DOWNLOAD_DELAY = 0.25
```

### Disabilita Check Memoria (Non Raccomandato)

Solo se hai molta RAM e non vuoi limiti:

```python
MEMUSAGE_ENABLED = False
```

⚠️ **ATTENZIONE**: Questo può causare crash del server se la memoria si esaurisce!

---

## 📈 Monitoring Durante Crawl

### Monitor Memoria in Real-Time

Terminale 1 - Crawling:
```bash
python cli.py crawl https://example.com --max-pages 500
```

Terminale 2 - Monitoring:
```bash
# Monitor memoria ogni 2 secondi
watch -n 2 'free -h && echo "---" && ps aux | grep scrapy | head -n 1'

# Oppure con htop (più visuale)
htop
# Premi F4 e cerca "scrapy"
```

### Log Scrapy con Memoria

Scrapy logga automaticamente l'uso di memoria:

```
2026-01-06 15:30:00 [scrapy.extensions.memusage] INFO: Memory usage: 512 MiB
2026-01-06 15:35:00 [scrapy.extensions.memusage] INFO: Memory usage: 768 MiB
2026-01-06 15:40:00 [scrapy.extensions.memusage] WARNING: Memory usage exceeded 1536 MiB
```

---

## 🛠️ Troubleshooting Memoria

### Problema: Crawl si blocca o è lentissimo

**Causa:** Swapping (usa disco invece di RAM)

**Soluzione:**
```bash
# Verifica swap usage
free -h

# Se swap usage > 0, hai finito la RAM
# Opzioni:
# 1. Riduci --max-pages
# 2. Aumenta RAM del server
# 3. Usa crawl in batch
```

### Problema: "Memory usage exceeded" anche con limite alto

**Causa:** Memory leak in spider o pipeline

**Soluzione:**

1. Verifica il tuo spider custom (se ne hai)
2. Disabilita pipeline non necessarie:

```python
# In settings.py, commenta pipeline non usate
ITEM_PIPELINES = {
    "crawler.pipelines.JsonWriterPipeline": 300,
    # "crawler.pipelines.CustomPipeline": 400,  # Disabilitata
}
```

3. Usa crawl in batch più piccoli

### Problema: Server freezato durante crawl

**Causa:** OOM Killer (Linux termina processi che usano troppa memoria)

**Verifica:**
```bash
# Controlla se OOM killer ha terminato processi
sudo dmesg | grep -i "out of memory"
sudo grep -i "killed process" /var/log/syslog
```

**Soluzione:**
1. Aumenta RAM del server (se possibile)
2. Usa limiti molto più bassi:
   ```python
   MEMUSAGE_LIMIT_MB = 512
   CONCURRENT_REQUESTS = 2
   ```
3. Crawla in batch molto piccoli (--max-pages 20)

---

## 🎯 Best Practices

### 1. Stima Pagine Prima di Crawlare

```bash
# Test con poche pagine per stimare memoria
python cli.py crawl https://example.com --max-pages 10

# Controlla memoria usata nei log
# Se 10 pagine = 100MB, 100 pagine ≈ 1GB
```

### 2. Usa Robots.txt e Sitemap

Se il sito ha una sitemap, usala per crawl più efficiente:

```python
# In settings.py, aggiungi:
SITEMAP_ENABLED = True
```

### 3. Escludi Risorse Pesanti

Skippa PDF, immagini grandi, video:

```python
# In settings.py:
DOWNLOAD_MAXSIZE = 10485760  # 10 MB max per file
DOWNLOAD_WARNSIZE = 5242880  # Warning a 5 MB

# In spider, skippa URL non necessari
IGNORED_EXTENSIONS = ['pdf', 'zip', 'tar.gz', 'mp4', 'avi']
```

### 4. Schedule Crawl Durante Off-Peak

Se il server ha poco carico di notte:

```bash
# Crontab per crawl notturno
# 2 AM ogni lunedì
0 2 * * 1 cd /path/to/datapizzarouge && ./venv/bin/python cli.py crawl https://example.com -m 500 >> /var/log/crawl.log 2>&1
```

---

## 📝 Checklist Pre-Crawl

Prima di avviare un crawl grande:

- [ ] Verifica RAM disponibile: `free -h`
- [ ] Controlla spazio disco: `df -h`
- [ ] Verifica limite memoria in `settings.py`
- [ ] Stima pagine totali del sito
- [ ] Decidi batch size appropriato
- [ ] Configura monitoring (htop o watch)
- [ ] Test con --max-pages 10 prima
- [ ] Prepara script per crawl in batch se necessario

---

## 🔗 Risorse Utili

### Comandi Quick Reference

```bash
# Crawl piccolo (test)
python cli.py crawl URL --max-pages 10

# Crawl medio
python cli.py crawl URL --max-pages 100

# Crawl grande (usa batch se RAM < 4GB)
python cli.py crawl URL --max-pages 500

# Monitor memoria durante crawl
watch -n 2 'free -h'

# Verifica log Scrapy
tail -f logs/datapizzarouge.log
```

### Settings.py Reference

Posizione: `crawler/settings.py`

Parametri chiave:
- `MEMUSAGE_LIMIT_MB`: Limite memoria massima
- `CONCURRENT_REQUESTS`: Richieste parallele totali
- `CONCURRENT_REQUESTS_PER_DOMAIN`: Richieste parallele per dominio
- `DOWNLOAD_DELAY`: Pausa tra richieste
- `CLOSESPIDER_ITEMCOUNT`: Limite pagine (overridable con --max-pages)

---

## 💡 Tips & Tricks

### Priorità Download

Crawla prima le pagine importanti:

```python
# In spider, usa priority
def parse(self, response):
    for link in response.css('a::attr(href)').getall():
        if '/docs/' in link:
            yield Request(link, callback=self.parse, priority=10)  # Alta priorità
        else:
            yield Request(link, callback=self.parse, priority=1)   # Bassa priorità
```

### Filtra per Profondità

Evita pagine troppo profonde:

```python
# In settings.py
DEPTH_LIMIT = 3  # Max 3 livelli dal root
```

### Cache per Testing

Durante sviluppo, usa cache per non ricrawlare:

```python
# In settings.py per development
HTTPCACHE_ENABLED = True
HTTPCACHE_EXPIRATION_SECS = 3600  # 1 ora
HTTPCACHE_DIR = 'httpcache'
```

Ricorda di disabilitare in produzione!

---

**Per supporto:** Vedi `GUIDA_COMPLETA.md` o apri issue su GitHub

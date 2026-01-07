# Multi-Site Crawler

Crawla multipli siti web e uniscili in una singola collection per RAG.

## 🚀 Quick Start

### 1. Crea File Configurazione

Copia il template e personalizzalo:

```bash
cp sites.example.json sites.json
```

Modifica `sites.json`:

```json
{
  "collection_name": "mia_collection",
  "max_pages_per_site": 100,
  "sites": [
    {
      "url": "https://www.sito1.it/",
      "max_pages": 200
    },
    {
      "url": "https://www.sito2.it/",
      "max_pages": 50
    }
  ]
}
```

### 2. Esegui Multi-Crawl

```bash
# Crawl completo + ingestion
python multi_crawl.py sites.json
```

### 3. Chat con Collection Unificata

```bash
python cli.py chat --collection mia_collection
```

## 📋 Configurazione

### Parametri File JSON

| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `collection_name` | string | Nome collection Qdrant (OBBLIGATORIO) |
| `max_pages_per_site` | int | Limite pagine default per tutti i siti |
| `sites` | array | Lista siti da crawlare (OBBLIGATORIO) |
| `sites[].url` | string | URL del sito (OBBLIGATORIO) |
| `sites[].max_pages` | int | Limite pagine per questo sito (opzionale) |

### Esempio Configurazione Completa

```json
{
  "collection_name": "enti_pubblici_completa",
  "max_pages_per_site": 100,
  "sites": [
    {
      "url": "https://www.aranagenzia.it/",
      "max_pages": 500
    },
    {
      "url": "https://www.governo.it/",
      "max_pages": 200
    },
    {
      "url": "https://www.inps.it/",
      "max_pages": 300
    },
    {
      "url": "https://www.agid.gov.it/",
      "max_pages": 150
    }
  ]
}
```

## 🎯 Modalità di Utilizzo

### Modalità 1: Completa (Default)

Crawl + Ingestion HTML + Ingestion Documenti

```bash
python multi_crawl.py sites.json
```

**Output:**
```
[FASE 1] CRAWL SITI
  [1/3] Crawling: https://www.aranagenzia.it/
  [2/3] Crawling: https://www.governo.it/
  [3/3] Crawling: https://www.inps.it/

[FASE 2] INGESTION HTML
  [1/3] Ingestion HTML: www.aranagenzia.it
  [2/3] Ingestion HTML: www.governo.it (APPEND)
  [3/3] Ingestion HTML: www.inps.it (APPEND)

[FASE 3] INGESTION DOCUMENTI
  [1/3] Ingestion documenti: www.aranagenzia.it (APPEND)
  [2/3] Ingestion documenti: www.governo.it (APPEND)
  [3/3] Ingestion documenti: www.inps.it (APPEND)

✓ MULTI-CRAWL COMPLETATO!
Collection: enti_pubblici
```

### Modalità 2: Solo Crawl

Crawl senza ingestion (utile per scaricare dati):

```bash
python multi_crawl.py sites.json --crawl-only
```

Poi ingestion manualmente in seguito:

```bash
python multi_crawl.py sites.json --ingest-only
```

### Modalità 3: Solo Ingestion

Processa dati già crawlati:

```bash
python multi_crawl.py sites.json --ingest-only
```

Utile se:
- Hai già crawlato i siti separatamente
- Vuoi rifare ingestion con nuovi parametri
- Hai interrotto lo script dopo il crawl

## 📂 Struttura Dati

Dopo il multi-crawl:

```
data/
├── raw/
│   ├── www.aranagenzia.it/       # Pagine HTML crawlate
│   │   ├── page1_hash.json
│   │   └── ...
│   ├── www.governo.it/
│   │   ├── page1_hash.json
│   │   └── ...
│   └── www.inps.it/
│       └── ...
│
├── documents/
│   ├── www.aranagenzia.it/       # Documenti scaricati
│   │   ├── .registry.json
│   │   ├── report.pdf
│   │   └── ...
│   ├── www.governo.it/
│   │   └── ...
│   └── www.inps.it/
│       └── ...
```

**Qdrant Collection:**
```
Collection: enti_pubblici
├── Chunks da www.aranagenzia.it (HTML + documenti)
├── Chunks da www.governo.it (HTML + documenti)
└── Chunks da www.inps.it (HTML + documenti)
```

Ogni chunk ha metadata che identifica il dominio:
```json
{
  "text": "...",
  "metadata": {
    "url": "https://www.aranagenzia.it/page1",
    "domain": "www.aranagenzia.it",
    "source_type": "html",
    ...
  }
}
```

## 🔍 Query su Collection Unificata

### Query Standard

```bash
python cli.py chat --collection enti_pubblici
```

```
> Quali sono le normative sui contratti pubblici?

[Cerca in TUTTI i siti della collection]
Risultati da:
- www.aranagenzia.it: ...
- www.governo.it: ...
- www.inps.it: ...
```

### Filtraggio per Dominio

Puoi filtrare risultati per dominio specifico tramite API:

```python
from rag.retrieval_pipeline import RetrievalPipeline

pipeline = RetrievalPipeline(collection_name="enti_pubblici")

# Query solo su aranagenzia.it
results = pipeline.search(
    query="normative contratti",
    filter_conditions={"domain": "www.aranagenzia.it"}
)
```

## ⚙️ Opzioni Avanzate

### Aggiungere Nuovi Siti a Collection Esistente

1. Modifica `sites.json` aggiungendo nuovi siti
2. Esegui crawl:

```bash
python multi_crawl.py sites.json
```

Lo script fa automaticamente **append** alla collection esistente.

### Rifare Ingestion Collection

Se vuoi **ricreare** la collection da zero:

```bash
# 1. Elimina collection esistente
python -c "
from storage.vector_store_manager import VectorStoreManager
vm = VectorStoreManager()
vm.client.delete_collection('enti_pubblici')
print('Collection eliminata')
"

# 2. Ri-esegui ingestion
python multi_crawl.py sites.json --ingest-only
```

### Gestione Errori

Se uno o più siti falliscono:

```
[1/3] ✓ Crawl completato: www.aranagenzia.it
[2/3] ✗ Crawl fallito: www.governo.it
[3/3] ✓ Crawl completato: www.inps.it

Crawl completati: 2/3
```

Lo script **continua** con i siti rimanenti. Puoi:

1. Correggere il problema (es. URL errato)
2. Ri-eseguire lo script → skip siti già processati

## 🐛 Troubleshooting

### "Collection già esistente"

**Normale!** Lo script fa append. Se vuoi ricreare:

```bash
# Opzione 1: Usa nome collection diverso in sites.json
# Opzione 2: Elimina collection (vedi sopra)
```

### "Dominio non trovato"

Durante `--ingest-only`, se dice "dominio non trovato":

- Verifica che il crawl sia completato con successo
- Controlla che esista `data/raw/{dominio}/`

### "Nessun documento"

Se dice "nessun documento" per un dominio:

- Normale se il sito non ha PDF/DOCX linkati
- Verifica con: `python scripts/registry_manager.py {dominio} --stats`

## 📊 Statistiche

Controlla registry documenti per ogni dominio:

```bash
python scripts/registry_manager.py www.aranagenzia.it --stats
python scripts/registry_manager.py www.governo.it --stats
```

Controlla collection unificata:

```bash
python cli.py stats --collection enti_pubblici
```

## 💡 Use Cases

### Use Case 1: Knowledge Base Multi-Ente

Crea KB unificata di più enti pubblici:

```json
{
  "collection_name": "pubblica_amministrazione",
  "max_pages_per_site": 200,
  "sites": [
    {"url": "https://www.aranagenzia.it/", "max_pages": 500},
    {"url": "https://www.governo.it/", "max_pages": 300},
    {"url": "https://www.inps.it/", "max_pages": 400},
    {"url": "https://www.agid.gov.it/", "max_pages": 200}
  ]
}
```

### Use Case 2: Comparazione Normative

Crawla siti di enti diversi per confrontare normative:

```json
{
  "collection_name": "normative_comparate",
  "sites": [
    {"url": "https://www.normattiva.it/", "max_pages": 100},
    {"url": "https://eur-lex.europa.eu/", "max_pages": 50},
    {"url": "https://www.gazzettaufficiale.it/", "max_pages": 100}
  ]
}
```

Query: "Confronta normativa italiana ed europea su privacy"

### Use Case 3: Monitoring Aggiornamenti

Ri-crawl periodico per tenere KB aggiornata:

```bash
# Cron job settimanale
0 2 * * 0 cd /path/to/datapizzarouge && python multi_crawl.py sites.json
```

## 📝 Note

- **Append automatico:** Ingestion successive alla stessa collection fanno append
- **Deduplicazione documenti:** Gestita automaticamente per dominio
- **Rate limiting:** Rispetta AUTOTHROTTLE configurato in Scrapy
- **OCR automatico:** Attivo su tutti i PDF scansionati
- **Timeout:** Ogni sito ha timeout indipendenti

## 🔗 Comandi Utili

```bash
# Multi-crawl completo
python multi_crawl.py sites.json

# Solo crawl
python multi_crawl.py sites.json --crawl-only

# Solo ingestion
python multi_crawl.py sites.json --ingest-only

# Chat
python cli.py chat --collection enti_pubblici

# Stats collection
python cli.py stats --collection enti_pubblici

# Registry documenti
python scripts/registry_manager.py www.aranagenzia.it --stats

# Lista collection
python cli.py list-collections
```

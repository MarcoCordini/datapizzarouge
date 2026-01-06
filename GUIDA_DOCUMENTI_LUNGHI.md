# Guida per Query su Documenti Lunghi

## Problema: Informazioni Incomplete o Frammentate

Quando un PDF contiene molte sezioni diverse (es: disciplinari di 50+ denominazioni DOC), il sistema RAG potrebbe recuperare solo **frammenti sparsi** invece dell'intera sezione richiesta.

### Perché succede?

1. **Retrieval basato su similarità**: Il sistema seleziona i chunk più simili alla query, ma potrebbero non essere consecutivi
2. **TOP_K limitato**: Con TOP_K=20 su un PDF di 608 pagine, recuperi solo ~3% del contenuto
3. **Query ambigua**: "DOC Abruzzo" potrebbe matchare parzialmente anche altri testi che menzionano "Abruzzo"

## Soluzioni Pratiche

### 1. Workflow Ottimale per Query Specifiche

```bash
# Passo 1: Avvia chat
python cli.py chat --collection disciplinari_test

# Passo 2: Identifica il file corretto
Tu: /files

File disponibili:
  1. Disciplinari_A_B.pdf
  2. Disciplinari_C_D.pdf

# Passo 3: Filtra per quel file
Tu: /filter Disciplinari_A_B.pdf

# Passo 4: Aumenta TOP_K per più contesto
Tu: /topk 50

TOP_K impostato a 50
SUGGERIMENTO: Con filtro file attivo, valori alti (50-100) recuperano più contesto.

# Passo 5: Fai la query
Tu: Elenca per intero la zona di produzione della DOC Abruzzo

[Ora recupererà 50 chunk SOLO da Disciplinari_A_B.pdf]
```

### 2. Valori TOP_K Consigliati

| Scenario | TOP_K | Quando Usarlo |
|----------|-------|---------------|
| Query generica su molti file | 10-20 | Prima esplorazione |
| Query su file specifico (piccolo) | 30-50 | File <100 pagine |
| Query su file specifico (grande) | 50-100 | File >200 pagine |
| Recupero di intera sezione | 100-200 | Quando serve tutto il contesto |

**Esempio**:
```
Tu: /filter Disciplinari_A_B.pdf
Tu: /topk 100
Tu: Descrivi completamente la DOC Abruzzo: zona, vitigni, caratteristiche, tutto
```

### 3. Strategie di Query Progressive

#### Strategia A: Query Incrementale
```
1. /topk 20
2. "Dammi una panoramica della DOC Abruzzo"
3. [Leggi la risposta, vedi cosa manca]
4. /topk 50
5. "Quali sono TUTTE le zone di produzione della DOC Abruzzo?"
6. [Se ancora incompleto]
7. /topk 100
8. "Elenca per intero la zona di produzione"
```

#### Strategia B: Query Specifica + Contesto
```
1. /filter Disciplinari_A_B.pdf
2. /topk 80
3. Query molto specifica: "Elenca tutti i comuni della zona di produzione della DOC Abruzzo, dall'inizio alla fine"
```

#### Strategia C: Query Multiple
```
1. /topk 30
2. "Quali sono le zone di produzione della DOC Abruzzo? (parte 1)"
3. "Continua con le zone di produzione della DOC Abruzzo (parte 2)"
4. "Continua con le zone di produzione (parte 3)"
```

### 4. Come Verificare la Completezza

Dopo ogni risposta, controlla:

```
Tu: /sources

Fonti:
- Disciplinari_A_B.pdf
  Percorso: D:\...\Disciplinari_A_B.pdf

[30 documenti trovati | 8542 tokens]
```

**Indicatori di incompletezza**:
- Risposta che dice "Il documento si interrompe..."
- Chunk da pagine molto distanti (es: pag 50, pag 200, pag 350)
- Score di rilevanza molto bassi (<0.25) negli ultimi risultati
- Menzione di denominazioni diverse da quella richiesta

**Soluzioni**:
```
# Se vedi questi segni:
Tu: /topk 80  # Aumenta TOP_K
Tu: [Ripeti la query con più specificità]
```

### 5. Query per Sezioni Lunghe

Per recuperare liste complete (es: tutti i comuni di una zona):

```python
# Query ottimale:
"Elenca COMPLETAMENTE e per INTERO tutti i comuni della zona di produzione
della DOC Abruzzo. Includi tutti i comuni dall'inizio alla fine senza
omettere nulla, anche se sono molti."
```

**Perché funziona meglio**:
- "COMPLETAMENTE" e "per INTERO" enfatizzano la necessità di tutto il contesto
- "dall'inizio alla fine" suggerisce continuità
- "senza omettere nulla" rinforza l'esaustività
- "anche se sono molti" prepara il sistema a recuperare molto contesto

### 6. Quando il Documento è VERAMENTE Troppo Grande

Se nemmeno con TOP_K=200 ottieni la sezione completa:

#### Opzione A: Re-ingestion con Chunk Più Grandi
```bash
# Modifica .env
CHUNK_SIZE=2000     # Invece di 1000
CHUNK_OVERLAP=400   # Invece di 200

# Re-ingest
python cli.py ingest-docs --dir ./documents --collection disciplinari_v2 --force
```

#### Opzione B: Accesso Diretto al PDF
```python
# Script custom per estrarre sezione specifica
from processors.document_loaders import DocumentLoader

loader = DocumentLoader()
doc = loader.load("Disciplinari_A_B.pdf")

# Cerca la sezione specifica nel testo completo
text = doc["text"]
start = text.find("ABRUZZO")
end = text.find("ALEATICO DI GRADOLI")  # Prossima denominazione
section = text[start:end]

print(section)
```

#### Opzione C: Chunking Intelligente per Sezioni
Modifica l'ingestion per dividere il PDF per denominazione invece che per dimensione:

```python
# In futuro: implementare in document_loaders.py
def chunk_by_denomination(pdf_text):
    """Divide PDF per denominazione DOC invece che per dimensione."""
    # Trova tutti i titoli di denominazione
    # Crea un chunk per ogni denominazione completa
    pass
```

### 7. Debug e Analisi

Per capire cosa sta recuperando il sistema:

```python
# Script di debug
from rag.retrieval_pipeline import RetrievalPipeline

pipeline = RetrievalPipeline("disciplinari_test", top_k=50)
results = pipeline.retrieve(
    "zona di produzione DOC Abruzzo",
    filter_by_file="Disciplinari_A_B.pdf"
)

# Analizza i risultati
for i, r in enumerate(results):
    print(f"\n=== Chunk {i+1} ===")
    print(f"Score: {r['score']:.3f}")
    print(f"File: {r['metadata']['file_name']}")
    print(f"Chunk index: {r['metadata'].get('chunk_index', 'N/A')}")
    print(f"Text preview: {r['text'][:200]}...")
```

## Best Practices Riassuntive

### ✅ DO
1. **Sempre filtrare per file** quando cerchi in documento specifico
2. **Aumentare TOP_K** progressivamente fino a ottenere completezza
3. **Query specifiche ed esaustive** ("elenca COMPLETAMENTE tutti...")
4. **Verificare fonti** con `/sources` dopo ogni risposta
5. **Usare TOP_K alto** (50-100) per documenti grandi filtrati

### ❌ DON'T
1. Non usare query generiche su documenti grandi senza filtro
2. Non aspettarti che TOP_K=20 recuperi liste complete da PDF di 600 pagine
3. Non fare query ambigue su collection con molti file simili
4. Non ignorare i warning di Claude su contesto incompleto

## Esempio Completo: Query Ottimale

```bash
$ python cli.py chat --collection disciplinari_test

Tu: /files
File disponibili:
  1. Disciplinari_A_B.pdf

Tu: /filter Disciplinari_A_B.pdf
Filtro attivo per: Disciplinari_A_B.pdf

Tu: /topk 80
TOP_K impostato a 80

Tu: /info
Info Collection:
  Nome: disciplinari_test
  Punti: 12450
  Filtro attivo: Disciplinari_A_B.pdf

Tu: Elenca COMPLETAMENTE e per INTERO tutti i comuni della zona di produzione della denominazione DOC "Abruzzo". Includi tutti i comuni dall'inizio alla fine, senza omettere nulla, anche se sono molti. Se la lista è lunga, continua fino alla fine.

Assistente: [Risposta con lista completa basata su 80 chunk da Disciplinari_A_B.pdf]

[80 documenti trovati | 15234 tokens]

Fonti:
- Disciplinari_A_B.pdf
```

## Metriche di Successo

**Prima** (TOP_K=20, no filtro):
- Recuperati: 20 chunk da file multipli
- Score medio: 0.32
- Completezza: ~10% della sezione richiesta
- Risposta: Frammentata e incompleta

**Dopo** (TOP_K=80, filtro attivo):
- Recuperati: 80 chunk dal file specifico
- Score medio: 0.38
- Completezza: ~80-90% della sezione richiesta
- Risposta: Sostanzialmente completa con dettagli

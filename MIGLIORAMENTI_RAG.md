# Miglioramenti Sistema RAG per Documenti

## Problemi Identificati e Risoluzioni

### 1. TOP_K Troppo Basso
**Problema**: Con `TOP_K_RETRIEVAL = 5`, per un PDF di 608 pagine, il sistema recuperava solo 5 chunk, insufficienti per rispondere correttamente.

**Soluzione**:
- Aumentato `TOP_K_RETRIEVAL` da 5 a 20 in `config.py`
- L'utente può configurarlo tramite variabile d'ambiente `TOP_K_RETRIEVAL`

```python
# config.py
TOP_K_RETRIEVAL = int(os.getenv("TOP_K_RETRIEVAL", "20"))
```

### 2. Metadata Documenti Non Visualizzati
**Problema**: Il formato del contesto mostrava solo URL e titoli (per web crawling), non i metadata dei documenti PDF/Word.

**Soluzione**:
- Aggiornato `format_context()` in `retrieval_pipeline.py` per includere:
  - `file_name`: Nome del file
  - `file_type`: Tipo di file (.pdf, .docx, etc.)
  - `source`: Percorso completo del file
  - `extraction_method`: Metodo di estrazione usato

**Esempio output**:
```
[Documento 1]
File: Disciplinari_A_B.pdf (tipo: .pdf)
Percorso: D:\...\Disciplinari_A_B.pdf
Rilevanza: 0.512

[Testo del documento...]
```

### 3. Impossibilità di Filtrare per File Specifico
**Problema**: Quando si chiedeva "Parlami della DOC Abruzzo", il sistema recuperava chunk da tutti i documenti, non solo dal file rilevante.

**Soluzione**:
- Aggiunto parametro `filter_by_file` al metodo `retrieve()` in `retrieval_pipeline.py`
- Aggiunto comando `/filter <nome_file>` nella chat interattiva
- Aggiunto comando `/files` per listare file disponibili
- Aggiunto comando `/nofilter` per rimuovere il filtro

**Uso**:
```
Tu: /files
File disponibili:
  1. Disciplinari_A_B.pdf
  2. Disciplinari_C_D.pdf

Tu: /filter Disciplinari_A_B.pdf
Filtro attivo per: Disciplinari_A_B.pdf
Le query cercheranno SOLO in questo file.

Tu: Parlami della DOC Abruzzo
[Ora cerca SOLO nel file specificato]
```

### 4. System Prompt Non Abbastanza Rigoroso
**Problema**: Claude rispondeva con informazioni non presenti nel contesto, inventando o deducendo dettagli.

**Soluzione**: Riscritto completamente il system prompt in `chat_interface.py` con regole CRITICHE:

```
REGOLE CRITICHE - SEGUI RIGOROSAMENTE:
1. RISPONDI SOLO CON INFORMAZIONI PRESENTI NEL CONTESTO
2. NON INVENTARE, NON DEDURRE, NON AGGIUNGERE
3. CITA SEMPRE LE FONTI
4. VERIFICA LA RILEVANZA
5. SEGNALA INFORMAZIONI INCOMPLETE
6. SEGNALA CONTRADDIZIONI
```

### 5. Mancanza di Diversificazione nei Risultati
**Problema**: I risultati potevano contenere chunk molto simili tra loro (duplicati semantici).

**Soluzione**:
- Aggiunto metodo `retrieve_diverse()` in `retrieval_pipeline.py`
- Usa algoritmo di diversificazione basato su Jaccard similarity
- Recupera più risultati (top_k * 3) e seleziona i più diversi
- Parametro `use_diverse_retrieval` in `ChatInterface`

### 6. Errori Unicode su Windows
**Problema**: Emoji nel logging (📚, ✓, ✗, ⚠️) causavano `UnicodeEncodeError` su Windows con encoding cp1252.

**Soluzione**: Rimossi tutti gli emoji dai file:
- `rag/ingestion_pipeline.py`
- `processors/document_loaders.py`
- `cli.py`
- `rag/chat_interface.py`

### 7. Errore `collection_exists`
**Problema**: `VectorStoreManager` non aveva il metodo `collection_exists()`.

**Soluzione**: Modificato `process_documents()` per usare direttamente `create_collection()` con `force_recreate`.

## Nuove Funzionalità

### 1. Retrieval Diversificato
```python
# Usa retrieval diversificato per evitare duplicati
chat = ChatInterface(collection_name="docs", use_diverse_retrieval=True)
```

### 2. Filtri per File
```python
# Programmaticamente
chat.set_file_filter("Disciplinari_A_B.pdf")
results = chat.retrieval.retrieve("query", filter_by_file="Disciplinari_A_B.pdf")

# Interattivamente
/filter Disciplinari_A_B.pdf
/nofilter
```

### 3. Lista File in Collection
```python
files = chat.list_available_files()
# ['Disciplinari_A_B.pdf', 'Disciplinari_C_D.pdf', ...]
```

### 4. Metadata Estesi in VectorStore
Ora il vector store salva tutti i metadata dei documenti:
- `file_name`, `file_type`, `source`
- `pages`, `extraction_method`
- Per web: `url`, `domain`, `crawled_at`

## Configurazione Consigliata

### File .env
```env
# Retrieval
TOP_K_RETRIEVAL=20          # Aumentato da 5 per documenti grandi
CHUNK_SIZE=1000             # Dimensione chunk
CHUNK_OVERLAP=200           # Overlap tra chunk

# Modelli
EMBEDDING_MODEL=text-embedding-3-small
LLM_MODEL=claude-sonnet-4-5-20250929
```

### Per Documenti Molto Grandi (>1000 pagine)
```env
TOP_K_RETRIEVAL=30
CHUNK_SIZE=1200
CHUNK_OVERLAP=300
```

## Comandi Chat Interattiva

| Comando | Descrizione |
|---------|-------------|
| `/files` | Lista tutti i file nella collection |
| `/filter <nome>` | Filtra risultati per file specifico |
| `/nofilter` | Rimuovi filtro file |
| `/sources` | Mostra fonti dell'ultima risposta |
| `/info` | Info sulla collection (include filtro attivo) |
| `/clear` | Pulisci cronologia conversazione |
| `/quit` | Esci |

## Workflow Consigliato

### Per Query Generiche
```bash
python cli.py chat --collection my_docs
Tu: Parlami di vitigni italiani
```

### Per Query su Documento Specifico
```bash
python cli.py chat --collection my_docs
Tu: /files
Tu: /filter Disciplinari_A_B.pdf
Tu: Quali sono le caratteristiche della DOC Abruzzo?
```

### Per Debugging Retrieval
```python
from rag.retrieval_pipeline import RetrievalPipeline

pipeline = RetrievalPipeline("my_docs", top_k=20)
results = pipeline.retrieve("DOC Abruzzo")

# Verifica file nei risultati
for r in results:
    print(f"Score: {r['score']:.3f} - File: {r['metadata'].get('file_name')}")
```

## Metriche di Miglioramento

### Prima
- TOP_K: 5
- Score medio: 0.30-0.32
- File rilevanti nei top 5: 0-1
- Risposta: Spesso con informazioni errate

### Dopo
- TOP_K: 20
- Score medio: 0.30-0.52 (maggiore varietà)
- File rilevanti nei top 20: 5-10
- Risposta: Basata solo su contesto effettivo

## Prossimi Miglioramenti Possibili

1. **Re-ranking**: Implementare un secondo stadio di ranking con modello dedicato
2. **Query Expansion**: Espandere la query con sinonimi/termini correlati
3. **Hybrid Search**: Combinare vector search con keyword search (BM25)
4. **Chunk Context**: Recuperare anche chunk adiacenti per più contesto
5. **Citation Tracking**: Tracking preciso di da quale chunk proviene ogni frase della risposta
6. **Multi-hop Reasoning**: Per domande che richiedono informazioni da più documenti

## Troubleshooting

### Score Bassi (<0.3)
- Considera di aumentare TOP_K
- Verifica che il modello di embedding sia lo stesso per ingestion e retrieval
- Prova query più specifiche

### Documenti Sbagliati nei Risultati
- Usa `/filter` per limitare a file specifico
- Verifica che il PDF sia stato ingested correttamente
- Controlla i metadata con `/files` e `/info`

### Risposte Che Inventano Informazioni
- Il nuovo system prompt è più rigoros, ma verifica sempre le fonti con `/sources`
- Usa filtri per file per ridurre ambiguità
- Considera di abbassare la temperature del LLM

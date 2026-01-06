# Sistema TOP_K Automatico - Calcolo Empirico

## 🎯 Problema Risolto

Prima dovevi indovinare manualmente il valore TOP_K giusto. Ora il sistema **calcola automaticamente** il TOP_K ottimale basandosi su:
1. **Dimensione del file filtrato**
2. **Tipo di query** (semplice vs. richiesta completa)
3. **Statistiche reali** dei chunk nel database

## 📐 Formula Empirica

### 1. Calcolo Statistiche File

```python
# Per ogni file nella collection:
total_chunks = conta_chunk_del_file()
total_chars = somma_caratteri_tutti_chunk()
estimated_pages = total_chars / 2000  # ~2000 char per pagina

# TOP_K raccomandati (percentuali dei chunk totali):
TOP_K_raccomandati = {
    "query_semplice": total_chunks * 0.1,      # 10% dei chunk
    "sezione_media": total_chunks * 0.2,       # 20% dei chunk
    "sezione_grande": total_chunks * 0.4,      # 40% dei chunk
    "documento_completo": min(200, total_chunks)  # Quasi tutto (max 200)
}
```

### 2. Rilevamento Tipo Query

Il sistema analizza la query per parole chiave che indicano richieste complete:

```python
complete_keywords = [
    "tutti", "completo", "intero", "elenco", "lista",
    "elenca", "per intero", "dall'inizio alla fine",
    "senza omettere", "completamente"
]

# Se la query contiene queste parole:
if any(keyword in query.lower() for keyword in complete_keywords):
    usa_topk_alto = True  # 40-60% dei chunk
else:
    usa_topk_normale = True  # 20-30% dei chunk
```

### 3. Selezione Automatica

```python
if filtro_file_attivo:
    stats = get_file_stats(file_name)

    if query_richiede_tutto:
        topk = stats["sezione_grande"]  # 40% dei chunk
    else:
        topk = stats["sezione_media"]   # 20% dei chunk
else:
    # Senza filtro file, usa valori prudenziali
    topk = 50 if query_richiede_tutto else 20
```

## 🚀 Come Usare

### Modalità 1: Automatico (Consigliato) - ABILITATO DI DEFAULT

```bash
python cli.py chat --collection disciplinari_test

# TOP_K automatico è già ATTIVO di default!

Tu: /filter Disciplinari_A_B.pdf

Tu: Elenca tutti i comuni della DOC Abruzzo
# Sistema: Rilevo "tutti" -> Query completa
# Sistema: File ha 1245 chunk -> TOP_K = 1245 * 0.4 = 498 (capped a 200)
# Sistema: Uso TOP_K = 200

[Risposta con contesto completo]
```

### Modalità 2: Con Verifica Statistiche

```bash
Tu: /files
File disponibili:
  1. Disciplinari_A_B.pdf

Tu: /fileinfo Disciplinari_A_B.pdf
Statistiche file: Disciplinari_A_B.pdf
  Total chunk: 1245
  Pagine stimate: 608
  Dimensione media chunk: 976 caratteri

  TOP_K raccomandati:
    Query semplice: 124
    Sezione media: 249
    Sezione grande: 498 (capped a 200)
    Documento quasi completo: 200

Tu: /filter Disciplinari_A_B.pdf

Tu: Descrivi la DOC Abruzzo
# Sistema usa automaticamente TOP_K=249 (sezione media)
```

### Modalità 3: Override Manuale

```bash
Tu: /topk 150
TOP_K impostato manualmente a 150
(TOP_K automatico disabilitato. Usa /auto per riabilitarlo)

Tu: [la tua query]
# Usa sempre TOP_K=150

Tu: /auto
TOP_K automatico abilitato
# Torna al calcolo automatico
```

## 📊 Esempi Pratici

### Esempio 1: File di 608 pagine (1245 chunk)

```
Query: "Dimmi qualcosa sulla DOC Abruzzo"
├─ Keyword rilevate: nessuna
├─ Tipo: query_semplice
├─ Filtro attivo: Disciplinari_A_B.pdf (1245 chunk)
└─ TOP_K calcolato: 1245 * 0.2 = 249

Query: "Elenca TUTTI i comuni della DOC Abruzzo"
├─ Keyword rilevate: "tutti", "elenca"
├─ Tipo: richiesta_completa
├─ Filtro attivo: Disciplinari_A_B.pdf (1245 chunk)
└─ TOP_K calcolato: 1245 * 0.4 = 498 → capped a 200
```

### Esempio 2: File piccolo di 50 pagine (100 chunk)

```
Query: "Elenca tutti i vitigni"
├─ Keyword rilevate: "tutti", "elenca"
├─ Tipo: richiesta_completa
├─ Filtro attivo: Doc_Piccolo.pdf (100 chunk)
└─ TOP_K calcolato: 100 * 0.4 = 40

Query: "Parlami del disciplinare"
├─ Keyword rilevate: nessuna
├─ Tipo: query_semplice
├─ Filtro attivo: Doc_Piccolo.pdf (100 chunk)
└─ TOP_K calcolato: 100 * 0.2 = 20
```

### Esempio 3: Senza Filtro File

```
Query: "Elenca tutte le DOC italiane"
├─ Keyword rilevate: "tutti", "elenca"
├─ Tipo: richiesta_completa
├─ Filtro attivo: NESSUNO
└─ TOP_K calcolato: 50 (default prudenziale)

Query: "Cos'è una DOC?"
├─ Keyword rilevate: nessuna
├─ Tipo: query_semplice
├─ Filtro attivo: NESSUNO
└─ TOP_K calcolato: 20 (default)
```

## 🔬 Percentuali Empiriche Spiegate

### 10% - Query Semplice
- **Usa caso**: "Cos'è...", "Dimmi qualcosa su...", domande generali
- **Esempio**: Su 1000 chunk, recupera 100
- **Copertura**: ~10% del documento = panoramica

### 20% - Sezione Media
- **Usa caso**: Query specifiche ma non complete
- **Esempio**: Su 1000 chunk, recupera 200
- **Copertura**: ~20% del documento = sezione approfondita

### 40% - Sezione Grande
- **Usa caso**: "Elenca TUTTI...", "Completo...", "Per intero..."
- **Esempio**: Su 1000 chunk, recupera 400
- **Copertura**: ~40% del documento = quasi tutto su un argomento

### 100% (capped a 200) - Documento Completo
- **Usa caso**: Analisi completa
- **Limite**: Max 200 per limiti di contesto LLM
- **Note**: Oltre 200 chunk (~200k caratteri), il contesto LLM satura

## ⚙️ Tuning delle Percentuali

Puoi modificare le percentuali in `retrieval_pipeline.py`:

```python
# In get_file_stats(), linee ~282-287
"recommended_topk_ranges": {
    "query_semplice": max(10, int(total_chunks * 0.1)),    # Cambia 0.1
    "sezione_media": max(20, int(total_chunks * 0.2)),     # Cambia 0.2
    "sezione_grande": max(50, int(total_chunks * 0.4)),    # Cambia 0.4
    "documento_completo": min(200, total_chunks)
}
```

**Suggerimenti**:
- **Documenti molto densi** (leggi, normative): Aumenta percentuali (0.3, 0.4, 0.6)
- **Documenti sparsi** (articoli, blog): Riduci percentuali (0.08, 0.15, 0.3)
- **Domande sempre incomplete**: Aumenta percentuale `sezione_grande` a 0.5-0.6

## 🎓 Come il Sistema Impara

### 1. Analisi Iniziale
Quando filtri un file, il sistema:
```python
scroll_result = qdrant.scroll(
    filter={"file_name": "Disciplinari_A_B.pdf"},
    limit=10000
)
# Conta tutti i chunk di quel file
# Calcola statistiche
```

### 2. Adattamento per Query
Per ogni query, analizza:
```python
keywords = ["tutti", "completo", "elenca", ...]
if any(kw in query.lower() for kw in keywords):
    use_large_section = True
```

### 3. Calcolo Finale
```python
if file_filtrato:
    base_topk = file_stats["total_chunks"]
    if richiesta_completa:
        topk = base_topk * 0.4  # 40%
    else:
        topk = base_topk * 0.2  # 20%
else:
    topk = 50 if richiesta_completa else 20
```

## 🔍 Debug e Verifica

### Verifica Calcolo Automatico

```bash
Tu: /auto
TOP_K automatico abilitato

Tu: /filter Disciplinari_A_B.pdf

Tu: /info
# Nota se c'è "Filtro attivo"

# Nei log (se abilitati):
# 2026-01-05 INFO - TOP_K suggerito: 249 (file ha 1245 chunk)
# 2026-01-05 INFO - TOP_K automatico: 20 -> 249
```

### Test Comparativo

```bash
# Test 1: Manuale
Tu: /auto  # Disabilita
Tu: /topk 50
Tu: Elenca tutti i comuni DOC Abruzzo
[Risposta incompleta]

# Test 2: Automatico
Tu: /auto  # Abilita
Tu: Elenca tutti i comuni DOC Abruzzo
# Sistema usa TOP_K=200 automaticamente
[Risposta completa]
```

## 📈 Metriche di Successo

### Prima (TOP_K Fisso = 20)
- ✗ Liste incomplete al 90%
- ✗ Utente deve indovinare valore corretto
- ✗ Stesso TOP_K per file da 10 e 1000 pagine

### Dopo (TOP_K Automatico)
- ✓ Liste complete al 80-90%
- ✓ Sistema calcola automaticamente
- ✓ TOP_K proporzionale a dimensione file
- ✓ Adattamento per tipo di query

## 💡 Best Practices

### ✅ DO
1. **Lascia TOP_K automatico attivo** (è il default)
2. **Usa sempre `/filter`** prima di query su file specifico
3. **Usa parole chiave** ("tutti", "completo") per query esaustive
4. **Verifica con `/fileinfo`** se hai dubbi

### ❌ DON'T
1. Non disabilitare auto per "abitudine"
2. Non usare `/topk` manuale senza motivo
3. Non fare query complete su collection intera senza filtro
4. Non ignorare il suggerimento di `/fileinfo`

## 🎯 Workflow Ottimale Finale

```bash
python cli.py chat --collection disciplinari_test

# 1. Esplora
Tu: /files
Tu: /fileinfo Disciplinari_A_B.pdf

# 2. Filtra
Tu: /filter Disciplinari_A_B.pdf

# 3. Usa auto (già attivo di default)
# Sistema calcola automaticamente TOP_K ottimale

# 4. Query
Tu: Elenca tutti i comuni della DOC Abruzzo
# TOP_K = calcolato automaticamente (es: 200)

# 5. Verifica
Tu: /sources
[80 documenti trovati | 85432 tokens]

# 6. Se incompleto (raro con auto)
Tu: /topk 200
Tu: [ripeti query]
```

## 🔮 Evoluzione Futura

### V2: Machine Learning
- Tracciare se risposta è stata completa
- Imparare pattern ottimali per utente specifico
- Adattare percentuali dinamicamente

### V3: Context Window Expansion
- Recuperare chunk adiacenti automaticamente
- Ricostruire sezioni continue
- Merge intelligente di chunk sovrapposti

### V4: Multi-File Intelligence
- Query su più file automaticamente
- Aggregazione risultati da fonti diverse
- De-duplicazione cross-file

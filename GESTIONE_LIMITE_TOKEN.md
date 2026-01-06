# Gestione Intelligente Limite Token

## 🚨 Problema Risolto

**Prima**:
```
Tu: Elenca tutti i comuni
Sistema: TOP_K = 1050
Claude: Error: 'prompt is too long: 213990 tokens > 200000 maximum'
```

**Ora**:
```
Tu: Elenca tutti i comuni
Sistema: TOP_K = 1050 → LIMITATO A 600 (per token)
Sistema: Context troncato a 580/1050 documenti (149,500 token)
Claude: [Risposta con massimo contesto possibile]
```

## 📐 Sistema a Tre Livelli

### Livello 1: Stima Preventiva
```python
# Prima di suggerire TOP_K, stima i token
avg_chunk_tokens = avg_chunk_size // 4  # ~250 token per chunk
estimated_total = suggested_topk * avg_chunk_tokens

if estimated_total > 150000:  # Limite sicuro
    # Limita TOP_K automaticamente
    max_safe_topk = 150000 // avg_chunk_tokens
    suggested_topk = min(suggested_topk, max_safe_topk)
```

### Livello 2: Truncation Dinamica
```python
# Durante format_context, conta token in tempo reale
total_tokens = 0
for chunk in results:
    chunk_tokens = len(chunk) // 4
    if total_tokens + chunk_tokens > 150000:
        # STOP: troncato qui
        break
    context_parts.append(chunk)
    total_tokens += chunk_tokens
```

### Livello 3: Protezione Finale
```python
# Nel messaggio a Claude
max_context_tokens = 150000  # Lascia 50k per system+risposta
context = format_context(results, max_context_tokens=150000)
# Total: 150k context + 50k overhead = 200k (entro limite)
```

## 🎯 Limiti Configurati

| Componente | Limite Token | Buffer | Totale |
|------------|--------------|--------|--------|
| **Context RAG** | 150,000 | - | 150k |
| System Prompt | ~1,000-2,000 | - | 2k |
| Query Utente | ~100-500 | - | 0.5k |
| Risposta Claude | ~5,000-10,000 | - | 10k |
| **Safety Buffer** | - | ~37,500 | 37.5k |
| **TOTALE** | **~158k-162.5k** | | **< 200k** ✓ |

## 📊 Calcolo Automatico

### Formula Euristica
```
1 token ≈ 4 caratteri (per inglese/italiano)

Chunk medio: 1000 caratteri
Token medi: 1000 / 4 = 250 token per chunk

TOP_K massimo sicuro = 150,000 / 250 = 600 chunk
```

### Esempio Reale: Disciplinari_A_B.pdf

```bash
Tu: /fileinfo Disciplinari_A_B.pdf

Statistiche file: Disciplinari_A_B.pdf
  Total chunk: 1245
  Pagine stimate: 608
  Dimensione media chunk: 976 caratteri
  Token medi per chunk: ~244

  TOP_K raccomandati (con stima token):
    Query semplice: 124 (~30,256 token)
    Sezione media: 249 (~60,756 token)
    Sezione grande: 498 (~121,512 token)
    Documento completo: 200 (~48,800 token) [!] CAPPED

  Limite token contesto: 150,000
  Limite totale Claude: 200,000
```

**Analisi**:
- Sezione grande richiederebbe 498 chunk (121k token) ✓ OK
- Documento completo (1245 chunk) richiederebbe 303k token ✗ SUPERA LIMITE
- Sistema limita automaticamente a 614 chunk max (150k token)

## 🛡️ Protezioni Implementate

### 1. Pre-emptive Capping
```python
# In suggest_topk()
if estimated_tokens > 150000:
    max_topk = 150000 // avg_chunk_tokens
    suggested = min(suggested, max_topk)
    logger.warning(f"TOP_K limitato: {original} -> {suggested}")
```

### 2. Runtime Truncation
```python
# In format_context()
for i, chunk in enumerate(chunks):
    if total_tokens + chunk_tokens > max_context_tokens:
        logger.warning(f"Troncato a {i}/{len(chunks)} documenti")
        break
```

### 3. User Warning
```python
# Nel contesto inviato a Claude
[NOTA: Contesto limitato a 580/1050 documenti per limiti di token.
Documenti inclusi hanno i punteggi di rilevanza più alti.]
```

## 🚀 Come Funziona in Pratica

### Scenario 1: Query Normale (Nessun Problema)
```bash
Tu: /filter Disciplinari_A_B.pdf
Tu: Descrivi la DOC Abruzzo

Sistema:
1. Query non contiene "tutti/completo" → sezione_media
2. Calcola: TOP_K = 249 (20% di 1245)
3. Stima: 249 * 244 = 60,756 token
4. Check: 60,756 < 150,000 ✓ OK
5. Usa TOP_K = 249

Risultato: ✓ Tutto il contesto incluso, nessun troncamento
```

### Scenario 2: Query Completa (Limite Rispettato)
```bash
Tu: /filter Disciplinari_A_B.pdf
Tu: Elenca tutti i comuni della DOC Abruzzo

Sistema:
1. Query contiene "tutti" + "elenca" → sezione_grande
2. Calcola: TOP_K = 498 (40% di 1245)
3. Stima: 498 * 244 = 121,512 token
4. Check: 121,512 < 150,000 ✓ OK
5. Usa TOP_K = 498

Risultato: ✓ Tutto il contesto incluso, nessun troncamento
```

### Scenario 3: File Enorme (Protezione Attiva)
```bash
Tu: /filter DocumentoEnorme.pdf  # 5000 chunk, 250 token/chunk
Tu: Elenca tutti i dettagli

Sistema:
1. Query contiene "tutti" → sezione_grande
2. Calcola: TOP_K = 2000 (40% di 5000)
3. Stima: 2000 * 250 = 500,000 token
4. Check: 500,000 > 150,000 ✗ SUPERA
5. Limita: TOP_K = 150,000 / 250 = 600
6. Usa TOP_K = 600 (invece di 2000)

Risultato: ✓ Protetto, usa massimo possibile (600 chunk)
           ⚠️ Non tutto il file, ma il massimo recuperabile
```

### Scenario 4: TOP_K Manuale Troppo Alto
```bash
Tu: /topk 2000  # Utente forza valore alto
Tu: Descrivi tutto

Sistema:
1. TOP_K manuale = 2000
2. Durante format_context():
   - Aggiunge chunk 1: 250 token (tot: 250)
   - Aggiunge chunk 2: 250 token (tot: 500)
   - ... continua ...
   - Aggiunge chunk 600: 250 token (tot: 150,000)
   - Chunk 601: SKIP (supererebbe 150k)
3. Troncato a 600/2000 documenti

Risultato: ✓ Protetto con truncation runtime
           ⚠️ User vede nota di troncamento
```

## 📱 Interfaccia Utente

### Avvisi Visibili

**Durante `/fileinfo`**:
```
TOP_K raccomandati (con stima token):
  Query semplice: 124 (~30,256 token)
  Sezione media: 249 (~60,756 token)
  Sezione grande: 498 (~121,512 token)
  Documento completo: 1245 (~303,800 token) [!] SUPERA LIMITE TOKEN -> usa max 614
```

**Durante Query (nei log)**:
```
2026-01-05 INFO - TOP_K suggerito: 600 (file ha 1245 chunk, ~150,000 token)
2026-01-05 WARNING - TOP_K limitato per token: 1050 -> 600 (stimato 256,200 token > limite 150,000)
2026-01-05 INFO - Context finale: 580 documenti, ~145,000 token stimati
```

**Nel Contesto a Claude** (se troncato):
```
[Documento 578]
[...]

[Documento 580]
[...]

[NOTA: Contesto limitato a 580/1050 documenti per limiti di token.
Documenti inclusi hanno i punteggi di rilevanza più alti.]
```

**Nella Risposta Utente**:
```
[580 documenti trovati | 145,234 token]
```

## 🔧 Configurazione Limiti

Puoi modificare i limiti in `config.py` o `.env`:

```python
# .env
MAX_CONTEXT_TOKENS=150000    # Limite contesto RAG
MAX_LLM_TOKENS=200000         # Limite totale Claude

# Oppure in codice:
chat = ChatInterface(
    collection_name="docs",
    max_context_tokens=150000  # Custom
)
```

### Limiti per Modelli Diversi

| Modello | Context Window | Context RAG Safe | System+Output |
|---------|----------------|------------------|---------------|
| **Claude Sonnet 4.5** | 200k | 150k | 50k |
| Claude Opus 3.5 | 200k | 150k | 50k |
| GPT-4 Turbo | 128k | 100k | 28k |
| GPT-4 | 8k | 6k | 2k |

## 🎓 Best Practices

### ✅ DO
1. **Lascia funzionare il sistema automatico** - gestisce tutto
2. **Usa `/fileinfo`** per verificare limiti prima di query
3. **Filtra per file** per ridurre chunk necessari
4. **Usa parole chiave specifiche** per recupero mirato

### ❌ DON'T
1. Non forzare `/topk 5000` su file grandi - verrà troncato
2. Non aspettarti di processare file da 10k chunk in una query
3. Non disabilitare protezioni - sono per tua sicurezza
4. Non ignorare warning di troncamento

## 🧮 Calcolo Manuale TOP_K Sicuro

Se vuoi calcolare manualmente TOP_K massimo:

```python
# 1. Ottieni avg_chunk_size dal file
avg_chunk_size = 976  # caratteri

# 2. Calcola token medi
avg_tokens = avg_chunk_size // 4  # = 244 token

# 3. Calcola TOP_K massimo
max_topk = 150000 // avg_tokens  # = 614 chunk

# 4. Usa quel valore
/topk 614
```

## 📈 Performance vs Completezza

| TOP_K | Token | Tempo API | Costo | Completezza |
|-------|-------|-----------|-------|-------------|
| 20 | ~5k | 2s | $0.01 | ~10% |
| 100 | ~25k | 5s | $0.05 | ~40% |
| 300 | ~75k | 12s | $0.15 | ~70% |
| 600 | ~150k | 25s | $0.30 | ~95% |

**Trade-off**:
- Più TOP_K = Più completo ma più lento e costoso
- Sistema automatico bilancia: massimo contesto possibile entro limiti

## 🔮 Cosa Fare Se Serve Tutto il Documento

Se il documento è troppo grande (>600 chunk utili):

### Opzione A: Query Multiple
```bash
Tu: Elenca comuni DOC Abruzzo zona A
[Risposta con primi comuni]

Tu: Continua con comuni DOC Abruzzo zona B
[Risposta con altri comuni]
```

### Opzione B: Re-ingestion con Chunk Più Grandi
```bash
# Aumenta chunk size per ridurre numero chunk
CHUNK_SIZE=2000  # Invece di 1000
# Re-ingest documento
python cli.py ingest-docs --dir ./docs --collection docs_v2 --force
```

### Opzione C: Accesso Diretto
```python
# Script per leggere sezione completa direttamente
from processors.document_loaders import DocumentLoader

loader = DocumentLoader()
doc = loader.load("Disciplinari_A_B.pdf")
full_text = doc["text"]

# Cerca sezione specifica
# ...
```

## 🎯 Riepilogo

Il sistema ora:
- ✅ **Previene errori di limite token** automaticamente
- ✅ **Calcola TOP_K ottimale** considerando token
- ✅ **Tronca intelligentemente** se necessario
- ✅ **Avvisa l'utente** quando tronca
- ✅ **Massimizza contesto** entro limiti sicuri

**Non devi più preoccuparti di**:
- ❌ Calcolare token manualmente
- ❌ Errori "prompt too long"
- ❌ Indovinare TOP_K corretto

Il sistema gestisce tutto automaticamente! 🚀

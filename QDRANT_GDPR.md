# Qdrant Cloud e GDPR - Documentazione Compliance

Guida alla compliance GDPR per l'utilizzo di Qdrant Cloud (data center Germania).

---

## Cos'è il GDPR

Il **GDPR (General Data Protection Regulation)** è il regolamento europeo 2016/679 sulla protezione dei dati personali, in vigore dal 25 maggio 2018.

**Si applica a**:
- Tutte le aziende UE che trattano dati personali
- Aziende extra-UE che trattano dati di cittadini UE
- Include dati di dipendenti, clienti, utenti

**Definizione di "dati personali"**:
Qualsiasi informazione relativa a persona fisica identificata o identificabile:
- Nome, cognome, email, telefono
- Indirizzo IP, cookie, ID utente
- Dati di geolocalizzazione
- **Anche contenuti testuali che menzionano persone**

---

## Qdrant Cloud e GDPR

### ✅ Compliance di Qdrant

**Qdrant Cloud** è **GDPR-compliant** perché:

1. **Data Residency EU**
   - Data center in **Germania (Frankfurt)** per cluster EU
   - I dati **non escono mai dall'Unione Europea**
   - Conforme all'Art. 44-50 GDPR (trasferimento dati)

2. **Certificazioni ISO**
   - ISO 27001 (gestione sicurezza informazioni)
   - ISO 27017 (sicurezza cloud)
   - ISO 27018 (protezione dati personali nel cloud)

3. **Data Processing Agreement (DPA)**
   - Qdrant fornisce **DPA standard EU** (Art. 28 GDPR)
   - Disponibile per clienti aziendali
   - Definisce responsabilità e obblighi

4. **Sicurezza Dati**
   - Crittografia **in transito** (TLS 1.3)
   - Crittografia **at rest** (AES-256)
   - Accesso tramite API Key univoca
   - Audit log disponibili

5. **Privacy by Design**
   - Isolamento cluster per cliente
   - Controllo accessi granulare
   - Backup automatici cifrati

### 📍 Data Center Germania

**Vantaggi data center Frankfurt**:
- ✅ **Giurisdizione EU** - Leggi europee sulla privacy
- ✅ **No US Cloud Act** - Dati non accessibili a governi extra-UE
- ✅ **Bassa latenza** - Ottimale per Italia/Europa
- ✅ **DSGVO (GDPR tedesco)** - Tra i più stringenti in EU

**Hosting provider**: AWS Frankfurt (eu-central-1) o Google Cloud Europe-West3 (Frankfurt)

---

## Il Tuo Progetto DataPizzaRouge

### Tipologia di Dati Trattati

Nel tuo caso, **crawli siti web pubblici** e memorizzi in Qdrant:

**Dati memorizzati**:
- Contenuto testuale delle pagine web
- URL delle pagine
- Metadata (titoli, data crawl)
- Embeddings vettoriali (rappresentazioni numeriche del testo)

**Rischio GDPR**:
- 🟢 **Basso** se crawli solo contenuti pubblici (es: sito aziendale istituzionale)
- 🟡 **Medio** se il sito contiene nomi di persone, contatti, commenti utenti
- 🔴 **Alto** se crawli dati sensibili (salute, opinioni politiche, dati biometrici)

### Base Giuridica (Art. 6 GDPR)

Per il tuo sistema RAG, la base giuridica più probabile è:

**Art. 6.1(f) - Legittimo Interesse**:
- Migliorare l'accesso alle informazioni aziendali
- Fornire assistenza automatica basata su contenuti pubblici
- Bilanciare interesse vs. diritti utenti

**Se crawli dati di terzi**: Serve valutazione caso per caso.

---

## Ruoli GDPR

### Chi è Chi?

**Data Controller (Titolare)**:
- **Tu** (la tua azienda)
- Decidi **perché** e **come** trattare i dati
- Responsabile ultimo della compliance

**Data Processor (Responsabile)**:
- **Qdrant** (servizio cloud)
- **OpenAI** (embeddings)
- **Anthropic** (generazione risposte)
- Trattano dati **per conto tuo**

**Obbligo**: Devi avere **DPA (Data Processing Agreement)** con tutti i processor.

---

## Misure di Sicurezza (Art. 32 GDPR)

### Misure Tecniche Implementate

#### 1. Crittografia

**In transito**:
```python
# Qdrant Cloud usa TLS 1.3
QDRANT_URL=https://xyz.aws.qdrant.io:6333  # ← HTTPS obbligatorio
```

**At rest**:
- Qdrant: AES-256 su storage
- OpenAI: Crittografia dati embeddings
- Anthropic: Crittografia dati conversazioni

#### 2. Controllo Accessi

**API Keys**:
```bash
# Nel .env - NON committare su git!
QDRANT_API_KEY=secret-key-here
OPENAI_API_KEY=sk-proj-...
ANTHROPIC_API_KEY=sk-ant-...
```

**Best practices**:
- ✅ API Key separate per ambiente (dev/prod)
- ✅ Rotazione periodica (ogni 3-6 mesi)
- ✅ Principio least privilege (accesso minimo necessario)

#### 3. Audit e Logging

**Log Qdrant**:
```python
# storage/vector_store_manager.py logga tutte le operazioni
logger.info(f"Ricerca su collection {collection_name}")
logger.info(f"Inseriti {len(vectors)} documenti")
```

**Retention log**:
- Conserva log per **12 mesi** (bilanciamento sicurezza/privacy)
- Log contiene: timestamp, operazione, collection, NO contenuti

#### 4. Backup e Disaster Recovery

**Qdrant Cloud**:
- Backup automatici giornalieri
- Retention 7 giorni (free tier) / 30 giorni (paid)
- Recovery point objective (RPO): 24h

**Dati raw locali**:
```bash
# Backup manuale dati crawlati
tar -czf backup_$(date +%Y%m%d).tar.gz data/raw/
```

---

## Diritti degli Interessati (Capi III GDPR)

### 1. Diritto di Accesso (Art. 15)

**Scenario**: Un utente chiede "quali miei dati avete?"

**Come rispondere**:
```bash
# 1. Identifica collection
python cli.py list-collections

# 2. Verifica se contiene dati dell'utente
# (es: cerca nome/email nelle sources)

# 3. Estrai dati relevanti
# (non c'è comando automatico, serve query manuale su Qdrant)
```

**Limite**: Non è facile cercare "tutti i dati di Mario Rossi" in un vector store. Considera:
- Metadata aggiuntivo per tracciare utenti
- O documenta che "non è tecnicamente possibile identificare dati specifici utente"

### 2. Diritto alla Cancellazione (Art. 17 - "Right to be Forgotten")

**Scenario**: Un utente chiede cancellazione dei suoi dati

**Implementazione**:

**Opzione A - Cancella e ri-ingest tutto** (semplice ma lenta):
```bash
# 1. Rimuovi pagine con dati utente dai raw
rm data/raw/www.tuosito.com/pagina_con_dati_utente_*.json

# 2. Ricrea collection da zero
python cli.py ingest --domain www.tuosito.com --collection tuosito_latest --force
```

**Opzione B - Cancellazione selettiva** (richiede custom code):
```python
# Pseudo-codice (da implementare)
from qdrant_client.models import Filter, FieldCondition, MatchValue

# Trova e cancella tutti i chunk di una specifica pagina
vector_store.client.delete(
    collection_name="tuosito_latest",
    points_selector=Filter(
        must=[
            FieldCondition(
                key="url",
                match=MatchValue(value="https://www.tuosito.com/pagina-utente")
            )
        ]
    )
)
```

**Tempo di risposta**: Entro **30 giorni** dalla richiesta (Art. 12.3).

### 3. Diritto alla Portabilità (Art. 20)

**Scenario**: Utente chiede "esportatemi i miei dati"

**Implementazione**:
```bash
# Export collection Qdrant (formato JSON)
# Richiede script custom per chiamare API Qdrant
# Formato: JSON strutturato leggibile
```

**Nota**: Embeddings vettoriali sono "dati derivati", non sempre richiesti. Fornisci principalmente testo originale.

### 4. Diritto di Opposizione (Art. 21)

**Scenario**: Utente dice "non voglio che usiate i miei dati"

**Azione**: Cancella dati (vedi Art. 17) + **blacklist URL/dominio** per non ri-crawlarlo.

**Implementazione**:
```python
# config.py - aggiungi lista blacklist
BLACKLIST_URLS = [
    "https://www.tuosito.com/utente/mario-rossi",
    "https://www.tuosito.com/profilo/*"
]

# crawler/spiders/domain_spider.py - filtra URL blacklisted
def parse_item(self, response):
    if any(fnmatch.fnmatch(response.url, pattern) for pattern in BLACKLIST_URLS):
        return None  # Skip
```

---

## Data Retention (Conservazione Dati)

### Policy Suggerita

**Dati raw crawlati** (`data/raw/`):
- Conservazione: **3 mesi**
- Dopo 3 mesi: Cancellazione automatica (se non serve storico)
- Giustificazione: Tempo ragionevole per aggiornamenti e rollback

**Vector store Qdrant**:
- Conservazione: **Indefinita** (finché il sito è attivo)
- Aggiornamento: **Settimanale** (sovrascrittura collection)
- Cancellazione: Quando sito dismesso o su richiesta

**Log applicativi**:
- Conservazione: **12 mesi**
- Giustificazione: Sicurezza, audit, troubleshooting

**Implementazione cancellazione automatica**:
```bash
# Script Linux/Mac (cron mensile)
find data/raw/ -type f -mtime +90 -delete

# PowerShell Windows (Task Scheduler mensile)
Get-ChildItem -Path "data\raw" -Recurse -File |
  Where-Object {$_.LastWriteTime -lt (Get-Date).AddDays(-90)} |
  Remove-Item -Force
```

---

## Data Processing Agreement (DPA)

### Con Qdrant

**Free Tier**: DPA disponibile su richiesta (email: support@qdrant.io)
**Paid Plans**: DPA incluso automaticamente

**Contenuto DPA tipico**:
- Ruoli: Tu = Controller, Qdrant = Processor
- Istruzioni trattamento: Memorizzazione embeddings, query search
- Subprocessor: AWS (hosting), può cambiare con preavviso
- Sicurezza: Crittografia, accessi, audit
- Data breach notification: Entro 72h
- Cancellazione post-contratto: Entro 30 giorni

**Azione**: Richiedi DPA a Qdrant e conserva copia.

### Con OpenAI

**DPA**: https://openai.com/enterprise-privacy/
- Disponibile per tutti i clienti
- Embeddings API: OpenAI **non trattiene dati** per training
- Retention: 30 giorni per abuse monitoring, poi cancellazione

**Azione**: Leggi e accetta DPA OpenAI.

### Con Anthropic

**DPA**: https://www.anthropic.com/legal/commercial-terms
- Claude API: Dati **non usati per training**
- Retention: Zero-data retention per API (non conservano conversazioni)

**Azione**: Leggi e accetta DPA Anthropic.

---

## Documentazione Obbligatoria

### 1. Informativa Privacy (Art. 13-14)

Se il tuo sistema RAG è usato da **utenti finali** (es: chat Blazor pubblica), serve informativa che spieghi:

**Contenuto minimo**:
- Titolare del trattamento (la tua azienda)
- Dati raccolti (query utente, metadata)
- Finalità (assistenza via RAG)
- Base giuridica (legittimo interesse o consenso)
- Destinatari dati (OpenAI, Anthropic, Qdrant)
- Trasferimenti extra-UE (nessuno, tutto in EU)
- Retention (es: query salvate X mesi)
- Diritti utente (accesso, cancellazione, ecc.)
- Contatto DPO se nominato

**Dove pubblicare**:
- Link in footer app Blazor
- Prima dell'uso della chat (checkbox "ho letto l'informativa")

### 2. Registro Trattamenti (Art. 30)

Se >250 dipendenti o trattamenti rischiosi, serve **Registro dei Trattamenti**.

**Esempio scheda per DataPizzaRouge**:

```
TRATTAMENTO: Sistema RAG per assistenza clienti

TITOLARE: [La tua azienda]
RESPONSABILE PROTEZIONE DATI: [Nome DPO se applicabile]

FINALITÀ:
- Fornire assistenza automatizzata basata su contenuti sito web
- Migliorare ricerca informazioni aziendali

CATEGORIE INTERESSATI:
- Visitatori sito web
- Clienti che usano chat

CATEGORIE DATI:
- Query utente (domande testuali)
- Metadata tecnici (IP, timestamp) [solo in log]
- Contenuti sito web crawlati (pubblici)

BASE GIURIDICA:
- Art. 6.1(f) - Legittimo interesse

DESTINATARI:
- Qdrant (vector store, Germania)
- OpenAI (embeddings, USA con clausole contrattuali standard)
- Anthropic (LLM, USA con clausole contrattuali standard)

TRASFERIMENTI EXTRA-UE:
- OpenAI: Clausole contrattuali standard EU-USA
- Anthropic: Clausole contrattuali standard EU-USA
- Nota: Entrambi certificati Privacy Shield successor

TEMPI CONSERVAZIONE:
- Query utente in log: 12 mesi
- Dati crawl sito: Aggiornamento settimanale, retention indefinita
- Embeddings Qdrant: Indefinita (fino a dismissione)

MISURE SICUREZZA:
- Crittografia TLS/AES-256
- API Key per accessi
- Backup giornalieri cifrati
- Audit log
- Network isolation cluster Qdrant

DATA INIZIO: [Data primo deploy]
```

### 3. Valutazione Impatto Privacy (DPIA - Art. 35)

**Quando serve**: Se trattamento "ad alto rischio"

**Alto rischio se**:
- Profilazione automatizzata con effetti legali
- Trattamento dati sensibili su larga scala
- Monitoraggio sistematico aree pubbliche

**Il tuo caso**: Probabilmente **NON serve DPIA** se:
- ✅ Crawli solo contenuti pubblici
- ✅ Non fai profilazione utenti
- ✅ Non tratti dati sensibili (salute, biometrici, giudiziari)

**Se in dubbio**: Consulta un avvocato privacy o DPO.

---

## Trasferimenti Extra-UE

### OpenAI (USA)

**Problema**: OpenAI è azienda USA, dati embeddings vanno su server USA.

**Soluzione GDPR**:
- **Clausole Contrattuali Standard (SCC)** - OpenAI le fornisce nel DPA
- **Valutazione adeguatezza**: OpenAI ha misure tecniche adeguate
- **Art. 46 GDPR**: Trasferimento legittimo se SCC + garanzie aggiuntive

**Alternative EU**:
- Considera embeddings provider EU (es: Cohere EU, Aleph Alpha)
- Impatto: Cambiare codice in `rag/ingestion_pipeline.py`

### Anthropic (USA)

**Problema**: Anthropic è azienda USA (Claude API).

**Soluzione GDPR**:
- **Clausole Contrattuali Standard (SCC)** fornite da Anthropic
- **Zero data retention**: Anthropic non memorizza conversazioni API
- **Art. 46 GDPR**: Trasferimento legittimo

**Alternative EU**:
- Mistral AI (Francia) - modello `mistral-large`
- Aleph Alpha (Germania) - modelli Luminous
- Impatto: Cambiare `datapizza-ai-clients-anthropic` con altro client

### Valutazione Rischio

**Per il tuo caso**:
- 🟢 **Rischio basso**: Dati sono contenuti web pubblici (non sensibili)
- 🟢 **Mitigazione**: OpenAI/Anthropic non trattengono dati, solo processing temporaneo
- 🟢 **SCC in vigore**: Trasferimenti legittimi

**Best practice**: Documenta nel Registro Trattamenti che hai valutato il trasferimento e ritenuto lecito con SCC.

---

## Checklist Compliance GDPR

### ✅ Setup Tecnico

- [ ] **Qdrant Cloud con cluster EU** (Germania)
- [ ] **API Keys sicure** (non in git, rotation policy)
- [ ] **Crittografia attiva** (TLS per connessioni)
- [ ] **Backup configurati** (Qdrant automatici + raw locali)
- [ ] **Log retention policy** (es: 12 mesi, poi cancellazione)
- [ ] **Data retention policy** (es: dati raw 3 mesi, vector store aggiornamento settimanale)

### ✅ Documentazione Legale

- [ ] **DPA con Qdrant** (richiesto e firmato)
- [ ] **DPA con OpenAI** (letto e accettato online)
- [ ] **DPA con Anthropic** (letto e accettato online)
- [ ] **Informativa Privacy** (pubblicata su app/sito)
- [ ] **Registro Trattamenti** (compilato se >250 dip.)
- [ ] **DPIA** (se trattamento alto rischio)

### ✅ Processi Operativi

- [ ] **Procedura richiesta accesso** (Art. 15)
- [ ] **Procedura cancellazione dati** (Art. 17)
- [ ] **Procedura data breach** (notifica entro 72h)
- [ ] **Review periodica fornitori** (verifica DPA aggiornati)
- [ ] **Training team** (consapevolezza GDPR)

### ✅ Diritti Utenti

- [ ] **Contatto privacy** (email/form per richieste)
- [ ] **Tempo risposta max 30 giorni**
- [ ] **Formato export dati** (JSON leggibile)
- [ ] **Blacklist URL** (per diritto opposizione)

---

## Best Practices

### 1. Minimizzazione Dati (Art. 5.1c)

**Principio**: Raccogliere solo dati necessari.

**Applicazione**:
- ✅ Crawla solo sezioni pubbliche rilevanti (escludi: profili utente, commenti, forum)
- ✅ Non loggare query utente se non necessario
- ✅ Non memorizzare IP utenti (se possibile)

**Implementazione**:
```python
# crawler/spiders/domain_spider.py
# Escludi URL con dati utente
rules = (
    Rule(
        LinkExtractor(
            deny=[
                r'/user/',      # Profili utente
                r'/profile/',   # Profili
                r'/comments/',  # Commenti
                r'/forum/',     # Forum
            ]
        ),
        callback='parse_item'
    ),
)
```

### 2. Pseudonimizzazione (Art. 32.1a)

**Principio**: Se devi memorizzare dati personali, usa hash/pseudonimi.

**Esempio**:
```python
import hashlib

# Se devi tracciare utente per rate limiting
user_id = request.headers.get("X-User-Email")
pseudonym = hashlib.sha256(user_id.encode()).hexdigest()[:16]
# Usa 'pseudonym' nei log invece di email vera
```

### 3. Privacy by Default

**Principio**: Impostazioni più restrittive di default.

**Applicazione**:
```python
# api.py - Non salvare query di default
@app.post("/api/query")
async def query_rag(request: QueryRequest, save_query: bool = False):  # ← Default False
    if save_query:
        # Salva solo se esplicitamente richiesto
        logger.info(f"Query salvata: {request.query}")
```

### 4. Trasparenza

**Principio**: Utenti devono sapere come usi i loro dati.

**Applicazione**:
- ✅ Spiega che le query vanno a OpenAI/Anthropic
- ✅ Link a privacy policy in chat Blazor
- ✅ Avviso se log sono conservati

**UI Blazor**:
```razor
<div class="alert alert-info">
    ℹ️ Le tue domande sono processate da AI (Claude) e non vengono memorizzate.
    <a href="/privacy">Privacy Policy</a>
</div>
```

---

## Cosa Fare in Caso di Data Breach

**Data breach**: Violazione sicurezza che causa perdita/accesso non autorizzato a dati.

**Esempi**:
- API Key Qdrant esposta su GitHub pubblico
- Database leak da attacco hacker
- Employee accede dati senza autorizzazione

### Procedura (Art. 33-34)

**1. Rilevamento (T+0)**:
```bash
# Esempio: Notifica GitHub che API key è esposta
# O alert Qdrant di accessi anomali
```

**2. Contenimento Immediato (T+1h)**:
```bash
# Revoca API Key compromessa
# Qdrant Dashboard → API Keys → Revoke

# Genera nuova API Key
# Aggiorna .env con nuova key

# Verifica accessi sospetti
# Qdrant Dashboard → Audit Logs
```

**3. Valutazione Rischio (T+24h)**:
- Che dati sono stati compromessi? (embeddings? query utenti? metadata?)
- Quante persone coinvolte?
- Rischi per diritti e libertà? (basso se solo contenuti pubblici)

**4. Notifica Autorità (T+72h)**:
Se **alto rischio** per gli interessati:
- Notifica a **Garante Privacy** (Italia: garante@gpdp.it) entro **72 ore**
- Modulo: https://www.garanteprivacy.it/modulistica

**5. Notifica Interessati**:
Se **rischio elevato**:
- Invia comunicazione a persone coinvolte
- Spiega breach, conseguenze, misure correttive

**6. Documentazione**:
- Registra breach nel "Registro violazioni" (obbligatorio)
- Include: data, natura, conseguenze, misure adottate

---

## Template Informativa Privacy (Minima)

```markdown
# INFORMATIVA PRIVACY - Sistema RAG

Ai sensi dell'art. 13 del Regolamento UE 2016/679 (GDPR):

## Titolare del Trattamento
[La Tua Azienda S.r.l.]
Via [Indirizzo], [Città], [CAP]
Email: privacy@tuaazienda.com

## Finalità del Trattamento
Il sistema RAG (Retrieval-Augmented Generation) processa le tue domande per fornirti risposte basate sui contenuti del nostro sito web.

## Base Giuridica
Art. 6.1(f) GDPR - Legittimo interesse (fornire assistenza clienti).

## Dati Raccolti
- Testo della tua domanda
- Metadata tecnici (timestamp, sessione)

## Destinatari Dati
I tuoi dati sono trattati da:
- **Qdrant** (vector database, Germania - UE)
- **OpenAI** (embeddings, USA - con clausole contrattuali standard)
- **Anthropic** (generazione risposte, USA - con clausole contrattuali standard)

## Conservazione
- Query: Non memorizzate permanentemente
- Log tecnici: 12 mesi

## I Tuoi Diritti
Hai diritto di:
- Accedere ai tuoi dati (Art. 15)
- Richiedere cancellazione (Art. 17)
- Opporti al trattamento (Art. 21)

Per esercitare i diritti: privacy@tuaazienda.com

## Reclami
Puoi presentare reclamo al Garante Privacy: www.garanteprivacy.it

Data: [Data]
```

---

## Risorse Utili

### Documentazione Qdrant
- **Qdrant Cloud Security**: https://qdrant.tech/documentation/cloud/security/
- **GDPR Compliance**: https://qdrant.tech/legal/privacy-policy/

### Documentazione Provider AI
- **OpenAI DPA**: https://openai.com/enterprise-privacy/
- **Anthropic Privacy**: https://www.anthropic.com/legal/privacy

### Normativa
- **Testo GDPR**: https://eur-lex.europa.eu/eli/reg/2016/679/oj
- **Garante Privacy Italia**: https://www.garanteprivacy.it/
- **Linee guida EDPB**: https://edpb.europa.eu/

### Tools
- **GDPR Checklist**: https://gdprchecklist.io/
- **DPO Professionale**: Considera consulenza se tratti dati su larga scala

---

## Conclusioni

### ✅ Il Tuo Setup è GDPR-Compliant Se:

1. **Qdrant Cloud in EU** (Germania) ✓
2. **DPA firmati** con tutti i processor ✓
3. **Informativa Privacy** pubblicata ✓
4. **Misure sicurezza** implementate (crittografia, API keys) ✓
5. **Processi per diritti utenti** definiti ✓
6. **Solo dati pubblici** crawlati (basso rischio) ✓

### ⚠️ Attenzione a:

- **Contenuti sensibili**: Non crawlare dati sanitari, biometrici, giudiziari
- **Dati minori**: Evita forum, social, sezioni con dati di bambini <16 anni
- **Profilazione**: Non usare RAG per decisioni automatizzate con effetti legali

### 🎯 Next Steps

1. Configura Qdrant Cloud con cluster Germania
2. Richiedi DPA a Qdrant (email support)
3. Leggi e accetta DPA OpenAI/Anthropic
4. Pubblica informativa privacy su app Blazor
5. Documenta nel Registro Trattamenti
6. Testa sistema con `python cli.py setup`

---

**Disclaimer**: Questa documentazione fornisce linee guida generali. Per compliance legale specifica, consulta un avvocato specializzato in privacy/GDPR.

---

Data: 2026-01-05
Versione: 1.0

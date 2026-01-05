# RAG da Documenti - PDF, Word, Immagini

Guida completa per fare RAG su documenti (non solo siti web).

---

## 🎯 Tipi di Documenti Supportabili

| Tipo | Formato | Difficoltà | Libreria | Qualità Estrazione |
|------|---------|------------|----------|-------------------|
| **PDF Testo** | .pdf | ⭐ Facile | PyMuPDF, pdfplumber | ⭐⭐⭐⭐⭐ Ottima |
| **PDF Scansionato** | .pdf (immagini) | ⭐⭐⭐ Media | PyMuPDF + Tesseract OCR | ⭐⭐⭐ Buona |
| **Word** | .docx | ⭐ Facile | python-docx | ⭐⭐⭐⭐⭐ Ottima |
| **Word Legacy** | .doc | ⭐⭐ Media | antiword, LibreOffice | ⭐⭐⭐ Buona |
| **Excel** | .xlsx | ⭐⭐ Media | openpyxl, pandas | ⭐⭐⭐⭐ Ottima |
| **PowerPoint** | .pptx | ⭐⭐ Media | python-pptx | ⭐⭐⭐⭐ Ottima |
| **Immagini (OCR)** | .jpg, .png | ⭐⭐⭐ Media | Tesseract, EasyOCR | ⭐⭐⭐ Variabile |
| **Immagini (AI)** | .jpg, .png | ⭐⭐ Media | GPT-4 Vision, Claude | ⭐⭐⭐⭐⭐ Ottima |
| **Markdown** | .md | ⭐ Facile | Built-in | ⭐⭐⭐⭐⭐ Ottima |
| **Testo** | .txt | ⭐ Facile | Built-in | ⭐⭐⭐⭐⭐ Ottima |

---

## 🏗️ Architettura Estesa

```
Documenti (PDF/Word/Images)
   ↓
Document Processors (estrazione testo)
   ↓
Content Chunker (esistente)
   ↓
Embeddings (OpenAI - esistente)
   ↓
Qdrant Vector Store (esistente)
   ↓
RAG Query (esistente)
```

**Moduli da aggiungere**:
- `processors/document_loaders.py` - Estrazione testo da vari formati
- `cli.py` - Nuovo comando `ingest-docs`

---

## 📦 Installazione Librerie

### Requirements Base

```bash
# Aggiungi a requirements.txt

# PDF
PyMuPDF==1.23.8          # (fitz) - Veloce, completo
pdfplumber==0.10.3       # Alternativa, tabelle

# Word/Office
python-docx==1.1.0       # DOCX
python-pptx==0.6.23      # PPTX
openpyxl==3.1.2          # XLSX

# OCR
pytesseract==0.3.10      # Tesseract wrapper
Pillow==10.1.0           # Image processing
easyocr==1.7.0           # OCR alternativo (più accurato, più lento)

# Markdown
markdown==3.5.1

# Utilities
filetype==1.2.0          # Auto-detect file type
```

```bash
pip install -r requirements.txt
```

### Tesseract OCR (Sistema)

**Linux (Ubuntu/Debian)**:
```bash
sudo apt update
sudo apt install tesseract-ocr
sudo apt install tesseract-ocr-ita  # Lingua italiana
sudo apt install tesseract-ocr-eng  # Lingua inglese
```

**Windows**:
```bash
# Download installer
# https://github.com/UB-Mannheim/tesseract/wiki

# Installa e aggiungi a PATH
# O specifica path in codice:
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
```

**macOS**:
```bash
brew install tesseract
brew install tesseract-lang  # Tutte le lingue
```

---

## 💻 Implementazione - Document Loaders

### Crea `processors/document_loaders.py`

```python
"""
Document loaders per vari formati.
Estrae testo da PDF, Word, Excel, PowerPoint, Immagini (OCR).
"""
import logging
from pathlib import Path
from typing import Dict, List, Optional
import filetype

# PDF
import fitz  # PyMuPDF
import pdfplumber

# Office
from docx import Document as DocxDocument
from pptx import Presentation
import openpyxl

# OCR
from PIL import Image
import pytesseract

# Utilities
import re

logger = logging.getLogger(__name__)


class DocumentLoader:
    """Carica e estrae testo da vari formati di documento."""

    def __init__(self, ocr_language: str = "ita+eng"):
        """
        Args:
            ocr_language: Lingue per OCR (es: "ita", "eng", "ita+eng")
        """
        self.ocr_language = ocr_language

    def load(self, file_path: str) -> Dict:
        """
        Carica documento e estrae testo.

        Returns:
            {
                "text": "Contenuto estratto...",
                "metadata": {
                    "file_name": "doc.pdf",
                    "file_type": "pdf",
                    "pages": 10,
                    "source": "/path/to/doc.pdf"
                }
            }
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File non trovato: {file_path}")

        # Auto-detect file type
        kind = filetype.guess(str(path))
        extension = path.suffix.lower()

        logger.info(f"Caricamento {path.name} (tipo: {extension})")

        # Router per tipo file
        if extension == ".pdf":
            return self._load_pdf(path)
        elif extension == ".docx":
            return self._load_docx(path)
        elif extension == ".doc":
            return self._load_doc_legacy(path)
        elif extension == ".pptx":
            return self._load_pptx(path)
        elif extension == ".xlsx":
            return self._load_xlsx(path)
        elif extension in [".txt", ".md", ".csv"]:
            return self._load_text(path)
        elif extension in [".jpg", ".jpeg", ".png", ".bmp", ".tiff"]:
            return self._load_image_ocr(path)
        else:
            raise ValueError(f"Formato non supportato: {extension}")

    # === PDF ===

    def _load_pdf(self, path: Path) -> Dict:
        """Carica PDF (testo o scansionato con OCR)."""
        try:
            # Prima prova estrazione testo nativo
            doc = fitz.open(str(path))
            text_parts = []
            has_text = False

            for page_num, page in enumerate(doc, start=1):
                text = page.get_text()
                if text.strip():
                    has_text = True
                    text_parts.append(text)

            doc.close()

            # Se PDF ha testo nativo, usa quello
            if has_text:
                logger.info(f"PDF con testo nativo ({len(text_parts)} pagine)")
                return {
                    "text": "\n\n".join(text_parts),
                    "metadata": {
                        "file_name": path.name,
                        "file_type": "pdf",
                        "pages": len(text_parts),
                        "source": str(path.absolute()),
                        "extraction_method": "native_text"
                    }
                }

            # Altrimenti, usa OCR
            logger.info(f"PDF scansionato, uso OCR...")
            return self._load_pdf_ocr(path)

        except Exception as e:
            logger.error(f"Errore caricamento PDF: {e}")
            raise

    def _load_pdf_ocr(self, path: Path) -> Dict:
        """Carica PDF scansionato con OCR."""
        doc = fitz.open(str(path))
        text_parts = []

        for page_num, page in enumerate(doc, start=1):
            logger.info(f"OCR pagina {page_num}/{len(doc)}")

            # Renderizza pagina come immagine
            pix = page.get_pixmap(dpi=300)  # Alta risoluzione per OCR
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            # OCR
            text = pytesseract.image_to_string(img, lang=self.ocr_language)
            text_parts.append(text)

        doc.close()

        return {
            "text": "\n\n".join(text_parts),
            "metadata": {
                "file_name": path.name,
                "file_type": "pdf",
                "pages": len(text_parts),
                "source": str(path.absolute()),
                "extraction_method": "ocr"
            }
        }

    # === WORD ===

    def _load_docx(self, path: Path) -> Dict:
        """Carica Word DOCX."""
        doc = DocxDocument(str(path))

        # Estrai paragrafi
        text_parts = [para.text for para in doc.paragraphs if para.text.strip()]

        # Estrai tabelle
        for table in doc.tables:
            for row in table.rows:
                row_text = " | ".join(cell.text for cell in row.cells)
                if row_text.strip():
                    text_parts.append(row_text)

        return {
            "text": "\n\n".join(text_parts),
            "metadata": {
                "file_name": path.name,
                "file_type": "docx",
                "paragraphs": len(doc.paragraphs),
                "tables": len(doc.tables),
                "source": str(path.absolute())
            }
        }

    def _load_doc_legacy(self, path: Path) -> Dict:
        """Carica Word DOC legacy (richiede LibreOffice o antiword)."""
        import subprocess

        # Prova con antiword (se installato)
        try:
            result = subprocess.run(
                ["antiword", str(path)],
                capture_output=True,
                text=True,
                check=True
            )
            text = result.stdout

            return {
                "text": text,
                "metadata": {
                    "file_name": path.name,
                    "file_type": "doc",
                    "source": str(path.absolute()),
                    "extraction_method": "antiword"
                }
            }
        except (FileNotFoundError, subprocess.CalledProcessError):
            raise ValueError(
                "Formato .doc legacy non supportato. "
                "Installa antiword o converti in .docx"
            )

    # === POWERPOINT ===

    def _load_pptx(self, path: Path) -> Dict:
        """Carica PowerPoint PPTX."""
        prs = Presentation(str(path))
        text_parts = []

        for slide_num, slide in enumerate(prs.slides, start=1):
            slide_texts = []

            # Estrai testo da tutti gli shapes
            for shape in slide.shapes:
                if hasattr(shape, "text") and shape.text.strip():
                    slide_texts.append(shape.text)

            if slide_texts:
                text_parts.append(f"[Slide {slide_num}]\n" + "\n".join(slide_texts))

        return {
            "text": "\n\n".join(text_parts),
            "metadata": {
                "file_name": path.name,
                "file_type": "pptx",
                "slides": len(prs.slides),
                "source": str(path.absolute())
            }
        }

    # === EXCEL ===

    def _load_xlsx(self, path: Path) -> Dict:
        """Carica Excel XLSX."""
        wb = openpyxl.load_workbook(str(path), data_only=True)
        text_parts = []

        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            sheet_texts = [f"[Foglio: {sheet_name}]"]

            for row in ws.iter_rows(values_only=True):
                row_text = " | ".join(str(cell) if cell else "" for cell in row)
                if row_text.strip(" |"):
                    sheet_texts.append(row_text)

            if len(sheet_texts) > 1:  # Ha contenuto oltre al titolo
                text_parts.append("\n".join(sheet_texts))

        return {
            "text": "\n\n".join(text_parts),
            "metadata": {
                "file_name": path.name,
                "file_type": "xlsx",
                "sheets": len(wb.sheetnames),
                "source": str(path.absolute())
            }
        }

    # === TESTO ===

    def _load_text(self, path: Path) -> Dict:
        """Carica file di testo (TXT, MD, CSV)."""
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()

        return {
            "text": text,
            "metadata": {
                "file_name": path.name,
                "file_type": path.suffix.lower(),
                "source": str(path.absolute())
            }
        }

    # === IMMAGINI (OCR) ===

    def _load_image_ocr(self, path: Path) -> Dict:
        """Carica immagine con OCR."""
        logger.info(f"OCR su immagine {path.name}")

        img = Image.open(str(path))
        text = pytesseract.image_to_string(img, lang=self.ocr_language)

        return {
            "text": text,
            "metadata": {
                "file_name": path.name,
                "file_type": "image",
                "dimensions": f"{img.width}x{img.height}",
                "source": str(path.absolute()),
                "extraction_method": "ocr"
            }
        }


# === BATCH PROCESSING ===

class DocumentBatchLoader:
    """Carica batch di documenti da una directory."""

    def __init__(self, ocr_language: str = "ita+eng"):
        self.loader = DocumentLoader(ocr_language=ocr_language)

    def load_directory(
        self,
        directory: str,
        recursive: bool = True,
        extensions: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Carica tutti i documenti da una directory.

        Args:
            directory: Path directory
            recursive: Se True, cerca anche in subdirectory
            extensions: Lista estensioni da processare (es: [".pdf", ".docx"])
                        Se None, processa tutti i formati supportati

        Returns:
            Lista di documenti estratti
        """
        path = Path(directory)

        if not path.exists():
            raise FileNotFoundError(f"Directory non trovata: {directory}")

        if extensions is None:
            extensions = [
                ".pdf", ".docx", ".doc", ".pptx", ".xlsx",
                ".txt", ".md", ".jpg", ".jpeg", ".png"
            ]

        # Trova file
        if recursive:
            files = [f for f in path.rglob("*") if f.suffix.lower() in extensions]
        else:
            files = [f for f in path.glob("*") if f.suffix.lower() in extensions]

        logger.info(f"Trovati {len(files)} documenti in {directory}")

        # Carica
        documents = []
        for file_path in files:
            try:
                doc = self.loader.load(str(file_path))
                documents.append(doc)
                logger.info(f"✓ {file_path.name}")
            except Exception as e:
                logger.error(f"✗ Errore caricando {file_path.name}: {e}")

        return documents
```

---

## 🔧 Integrazione con Ingestion Pipeline

### Modifica `rag/ingestion_pipeline.py`

Aggiungi metodo per ingestire documenti:

```python
# Aggiungi import
from processors.document_loaders import DocumentBatchLoader

class IngestionPipeline:
    # ... codice esistente ...

    def process_documents(
        self,
        documents_dir: str,
        collection_name: str,
        force_recreate: bool = False,
        recursive: bool = True,
        extensions: Optional[List[str]] = None
    ):
        """
        Processa documenti locali (PDF, Word, etc.) e crea vector store.

        Args:
            documents_dir: Directory con documenti
            collection_name: Nome collection Qdrant
            force_recreate: Se True, ricrea collection se esiste
            recursive: Cerca documenti in subdirectory
            extensions: Lista estensioni da processare
        """
        logger.info(f"📚 Ingestion documenti da: {documents_dir}")

        # 1. Carica documenti
        batch_loader = DocumentBatchLoader(ocr_language="ita+eng")
        documents = batch_loader.load_directory(
            documents_dir,
            recursive=recursive,
            extensions=extensions
        )

        if not documents:
            logger.warning("Nessun documento trovato!")
            return

        logger.info(f"Caricati {len(documents)} documenti")

        # 2. Prepara collection
        if force_recreate or not self.vector_store.collection_exists(collection_name):
            logger.info(f"Creazione collection: {collection_name}")
            self.vector_store.create_collection(
                collection_name=collection_name,
                vector_size=self.embedding_dimensions
            )

        # 3. Process e chunking
        all_chunks = []
        for doc in documents:
            # Pulisci testo (rimuovi whitespace multipli, etc.)
            cleaned_text = self._clean_text(doc["text"])

            # Chunking
            chunks = self.chunker.chunk_text(
                text=cleaned_text,
                metadata={
                    **doc["metadata"],
                    "chunk_strategy": "semantic"
                }
            )

            all_chunks.extend(chunks)

        logger.info(f"Totale chunks: {len(all_chunks)}")

        # 4. Genera embeddings e inserisci
        self._batch_embed_and_insert(all_chunks, collection_name)

        logger.info(f"✅ Ingestion completata: {collection_name}")

    def _clean_text(self, text: str) -> str:
        """Pulizia testo da documenti."""
        import re

        # Rimuovi whitespace multipli
        text = re.sub(r'\s+', ' ', text)

        # Rimuovi righe vuote multiple
        text = re.sub(r'\n\s*\n', '\n\n', text)

        return text.strip()
```

---

## 🖥️ Nuovo Comando CLI

### Modifica `cli.py`

Aggiungi comando `ingest-docs`:

```python
@cli.command("ingest-docs")
@click.option(
    "--dir",
    "-d",
    required=True,
    help="Directory con documenti (PDF, Word, etc.)"
)
@click.option(
    "--collection",
    "-c",
    required=True,
    help="Nome collection Qdrant"
)
@click.option(
    "--recursive/--no-recursive",
    default=True,
    help="Cerca documenti in subdirectory"
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Forza ricreazione collection se esiste"
)
@click.option(
    "--extensions",
    "-e",
    multiple=True,
    help="Estensioni da processare (es: -e .pdf -e .docx)"
)
def ingest_docs(dir, collection, recursive, force, extensions):
    """
    Ingestion documenti locali (PDF, Word, Excel, PowerPoint, Immagini).

    Esempi:

        # Processa tutti i PDF in una directory
        python cli.py ingest-docs --dir ./documents --collection my_docs

        # Solo PDF e Word
        python cli.py ingest-docs --dir ./docs --collection my_docs -e .pdf -e .docx

        # Forza ricreazione
        python cli.py ingest-docs --dir ./docs --collection my_docs --force
    """
    from rag.ingestion_pipeline import IngestionPipeline

    click.echo(f"📚 Ingestion documenti da: {dir}")
    click.echo(f"📦 Collection: {collection}")

    # Converti extensions da tuple a list
    extensions_list = list(extensions) if extensions else None

    # Pipeline
    pipeline = IngestionPipeline()

    try:
        pipeline.process_documents(
            documents_dir=dir,
            collection_name=collection,
            force_recreate=force,
            recursive=recursive,
            extensions=extensions_list
        )

        click.echo(f"✅ Ingestion completata!")
        click.echo(f"Usa: python cli.py chat --collection {collection}")

    except Exception as e:
        click.echo(f"❌ Errore: {e}", err=True)
        raise click.Abort()
```

---

## 🚀 Utilizzo

### Esempi Pratici

#### 1. Ingestion PDF

```bash
# Directory con PDF
mkdir -p data/documents/manuals
# Copia i tuoi PDF in data/documents/manuals/

# Ingestion
python cli.py ingest-docs \
  --dir data/documents/manuals \
  --collection manuals_latest

# Chat
python cli.py chat --collection manuals_latest
```

#### 2. Ingestion Word + Excel

```bash
# Directory con documenti Office
mkdir -p data/documents/reports

# Solo .docx e .xlsx
python cli.py ingest-docs \
  --dir data/documents/reports \
  --collection company_reports \
  -e .docx \
  -e .xlsx
```

#### 3. Ingestion Immagini con OCR

```bash
# Directory con scansioni/screenshot
mkdir -p data/documents/scans

# Processa immagini
python cli.py ingest-docs \
  --dir data/documents/scans \
  --collection scanned_docs \
  -e .jpg \
  -e .png
```

#### 4. Mix Web + Documenti

```bash
# 1. Crawl sito web
python cli.py crawl https://www.tuosito.com --max-pages 50
python cli.py ingest --domain www.tuosito.com --collection knowledge_base

# 2. Aggiungi documenti alla STESSA collection
python cli.py ingest-docs \
  --dir data/documents \
  --collection knowledge_base  # ← Stessa collection!

# Ora puoi fare query su ENTRAMBE le fonti
python cli.py chat --collection knowledge_base
> "Quali sono i prodotti?" (risponde con web + PDF)
```

---

## 🎨 OCR Avanzato - EasyOCR (Opzionale)

**EasyOCR** è più accurato di Tesseract ma più lento.

### Installazione

```bash
pip install easyocr
```

### Modifica `document_loaders.py`

```python
import easyocr

class DocumentLoader:
    def __init__(self, ocr_language: str = "ita+eng", use_easyocr: bool = False):
        self.ocr_language = ocr_language
        self.use_easyocr = use_easyocr

        if use_easyocr:
            logger.info("Inizializzazione EasyOCR...")
            languages = ocr_language.split("+")
            lang_map = {"ita": "it", "eng": "en"}
            easy_langs = [lang_map.get(l, l) for l in languages]
            self.easyocr_reader = easyocr.Reader(easy_langs)

    def _load_image_ocr(self, path: Path) -> Dict:
        """Carica immagine con OCR."""
        if self.use_easyocr:
            # EasyOCR
            result = self.easyocr_reader.readtext(str(path))
            text = "\n".join([detection[1] for detection in result])
        else:
            # Tesseract
            img = Image.open(str(path))
            text = pytesseract.image_to_string(img, lang=self.ocr_language)

        return {
            "text": text,
            "metadata": {
                "file_name": path.name,
                "file_type": "image",
                "source": str(path.absolute()),
                "extraction_method": "easyocr" if self.use_easyocr else "tesseract"
            }
        }
```

**Uso**:
```python
loader = DocumentLoader(ocr_language="ita+eng", use_easyocr=True)
```

---

## 🤖 Estrazione con AI - GPT-4 Vision / Claude (Premium)

Per **immagini complesse** (grafici, diagrammi, screenshot UI), usa AI multimodale.

### Esempio con Claude (Anthropic)

```python
import base64
from anthropic import Anthropic

class AIDocumentExtractor:
    def __init__(self, api_key: str):
        self.client = Anthropic(api_key=api_key)

    def extract_from_image(self, image_path: str) -> str:
        """Estrae testo da immagine con Claude Vision."""
        # Leggi immagine
        with open(image_path, "rb") as f:
            image_data = base64.standard_b64encode(f.read()).decode("utf-8")

        # Determina media type
        ext = Path(image_path).suffix.lower()
        media_type = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp"
        }.get(ext, "image/jpeg")

        # Query Claude
        message = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": (
                            "Estrai TUTTO il testo da questa immagine. "
                            "Includi titoli, paragrafi, didascalie, testo in grafici, "
                            "e qualsiasi altra informazione testuale. "
                            "Mantieni la struttura e formattazione originale."
                        )
                    }
                ],
            }]
        )

        return message.content[0].text
```

**Vantaggi**:
- ⭐⭐⭐⭐⭐ Qualità eccellente
- ✅ Capisce context (grafici, tabelle, layout)
- ✅ Supporta handwriting

**Svantaggi**:
- 💰 Costa (circa $0.003/immagine)
- 🐌 Più lento di OCR tradizionale

---

## 📊 Confronto Soluzioni OCR

| Soluzione | Velocità | Accuratezza | Costo | Use Case |
|-----------|----------|-------------|-------|----------|
| **Tesseract** | ⚡⚡⚡ Veloce | ⭐⭐⭐ Buona | Gratis | Testo pulito, scansioni |
| **EasyOCR** | ⚡⚡ Media | ⭐⭐⭐⭐ Ottima | Gratis | Multi-lingua, handwriting |
| **Claude Vision** | ⚡ Lenta | ⭐⭐⭐⭐⭐ Eccellente | $$ | Grafici, layout complessi |
| **GPT-4 Vision** | ⚡ Lenta | ⭐⭐⭐⭐⭐ Eccellente | $$$ | Come Claude |
| **Azure OCR** | ⚡⚡ Media | ⭐⭐⭐⭐ Ottima | $ | Enterprise, batch |

---

## 🎯 Best Practices

### 1. Preprocessing Immagini

Per migliorare OCR:

```python
from PIL import Image, ImageEnhance

def preprocess_image_for_ocr(image_path: str) -> Image.Image:
    """Migliora immagine per OCR."""
    img = Image.open(image_path)

    # Converti a grayscale
    img = img.convert("L")

    # Aumenta contrasto
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(2.0)

    # Aumenta sharpness
    enhancer = ImageEnhance.Sharpness(img)
    img = enhancer.enhance(2.0)

    # Ridimensiona se troppo piccola (DPI per OCR: 300)
    if img.width < 1000:
        scale = 1000 / img.width
        img = img.resize((int(img.width * scale), int(img.height * scale)))

    return img
```

### 2. Chunking Intelligente per PDF

Per PDF lunghi, chunka per sezione:

```python
def chunk_pdf_by_sections(pdf_path: str) -> List[Dict]:
    """Chunka PDF per sezioni (headings)."""
    doc = fitz.open(pdf_path)
    chunks = []

    for page in doc:
        text = page.get_text()

        # Trova headings (font più grande)
        blocks = page.get_text("dict")["blocks"]
        # Analizza font size, identifica sezioni
        # Chunka per sezione invece che per dimensione fissa
        ...

    return chunks
```

### 3. Metadata Ricchi

Aggiungi metadata utili:

```python
metadata = {
    "file_name": "manual.pdf",
    "file_type": "pdf",
    "page_number": 15,
    "section": "Capitolo 3 - Installazione",
    "author": "Mario Rossi",
    "creation_date": "2024-01-05",
    "language": "ita"
}
```

Così puoi filtrare query:
```python
# Solo pagine 10-20
filter = {"page_number": {"$gte": 10, "$lte": 20}}

# Solo sezione specifica
filter = {"section": "Installazione"}
```

### 4. Batch Processing con Progress

```python
from tqdm import tqdm

def process_documents_with_progress(directory: str):
    files = list(Path(directory).rglob("*.pdf"))

    for file_path in tqdm(files, desc="Processing PDFs"):
        doc = loader.load(str(file_path))
        # ... process ...
```

---

## 🔄 Workflow Completo - Esempio Reale

### Scenario: Knowledge Base Aziendale

**Fonti**:
- Sito web aziendale (pubblico)
- Manuali PDF (interni)
- Presentazioni PowerPoint (training)
- Immagini scansionate (documenti legacy)

**Workflow**:

```bash
# 1. Crawl sito web
python cli.py crawl https://www.azienda.com --max-pages 100
python cli.py ingest --domain www.azienda.com --collection kb_azienda

# 2. Aggiungi manuali PDF
mkdir -p data/documents/manuals
# Copia PDF in data/documents/manuals/
python cli.py ingest-docs \
  --dir data/documents/manuals \
  --collection kb_azienda \
  -e .pdf

# 3. Aggiungi presentazioni
mkdir -p data/documents/presentations
# Copia PPTX
python cli.py ingest-docs \
  --dir data/documents/presentations \
  --collection kb_azienda \
  -e .pptx

# 4. Aggiungi scansioni legacy (OCR)
mkdir -p data/documents/scans
# Copia immagini
python cli.py ingest-docs \
  --dir data/documents/scans \
  --collection kb_azienda \
  -e .jpg \
  -e .png

# 5. Chat su TUTTO
python cli.py chat --collection kb_azienda
> "Quali sono le procedure di sicurezza?"
  (risponde usando: sito + PDF manuale + slide training)
```

---

## 📈 Statistiche e Monitoring

Aggiungi tracking per documenti:

```python
# Dopo ingestion
stats = pipeline.vector_store.get_collection_info("kb_azienda")

print(f"Documenti totali: {stats['points_count']}")

# Breakdown per tipo
# Query Qdrant con scroll per contare tipi
from collections import Counter

file_types = Counter()
# ... scroll collection, conta metadata['file_type']

print(f"PDF: {file_types['pdf']}")
print(f"DOCX: {file_types['docx']}")
print(f"Immagini OCR: {file_types['image']}")
```

---

## 🚨 Limitazioni e Problemi Comuni

### 1. PDF Scansionati Male

**Problema**: OCR produce testo illeggibile

**Soluzione**:
- Migliora qualità scansione (300+ DPI)
- Preprocessing immagine (contrasto, sharpness)
- Usa EasyOCR o Claude Vision

### 2. Layout Complessi

**Problema**: PDF con colonne, tabelle complesse

**Soluzione**:
- Usa `pdfplumber` invece di PyMuPDF (migliore per tabelle)
- Considera Claude Vision per layout molto complessi
- Chunka manualmente per sezione

### 3. Performance con Molti Documenti

**Problema**: Ingestion lenta con 1000+ documenti

**Soluzione**:
```python
# Multiprocessing
from multiprocessing import Pool

def process_file(file_path):
    loader = DocumentLoader()
    return loader.load(file_path)

with Pool(processes=4) as pool:
    documents = pool.map(process_file, file_paths)
```

### 4. OCR Multi-Lingua

**Problema**: Documenti in più lingue

**Soluzione**:
```bash
# Tesseract multi-lingua
pytesseract.image_to_string(img, lang="ita+eng+fra+deu")

# EasyOCR
reader = easyocr.Reader(['it', 'en', 'fr', 'de'])
```

---

## 🎯 Quick Reference

### Comando Base
```bash
python cli.py ingest-docs --dir <directory> --collection <nome>
```

### Opzioni Comuni
```bash
# Solo PDF
python cli.py ingest-docs --dir ./docs --collection kb -e .pdf

# Ricorsivo (subdirectory)
python cli.py ingest-docs --dir ./docs --collection kb --recursive

# Non ricorsivo
python cli.py ingest-docs --dir ./docs --collection kb --no-recursive

# Forza ricreazione
python cli.py ingest-docs --dir ./docs --collection kb --force

# Mix estensioni
python cli.py ingest-docs --dir ./docs --collection kb -e .pdf -e .docx -e .pptx
```

---

## 📚 Risorse

- **PyMuPDF**: https://pymupdf.readthedocs.io/
- **python-docx**: https://python-docx.readthedocs.io/
- **Tesseract OCR**: https://tesseract-ocr.github.io/
- **EasyOCR**: https://github.com/JaidedAI/EasyOCR
- **Claude Vision**: https://docs.anthropic.com/claude/docs/vision

---

Ora puoi fare RAG su qualsiasi tipo di documento! 🎉

Vuoi che implementi subito il codice completo o hai altre domande? 💪

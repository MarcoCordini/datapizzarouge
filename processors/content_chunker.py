"""
Modulo per chunking semantico del testo.
Divide il testo in chunk con overlap, preservando confini di paragrafi e frasi.
"""
import re
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class ContentChunker:
    """
    Chunker semantico per testo.
    Divide il testo mantenendo contesto e confini naturali.
    """

    def __init__(self, chunk_size: int = 1000, overlap: int = 200):
        """
        Inizializza ContentChunker.

        Args:
            chunk_size: Dimensione target del chunk in caratteri
            overlap: Overlap tra chunk consecutivi in caratteri
        """
        self.chunk_size = chunk_size
        self.overlap = overlap

        if overlap >= chunk_size:
            raise ValueError("Overlap deve essere minore di chunk_size")

    def chunk_text(
        self,
        text: str,
        metadata: Optional[Dict] = None,
    ) -> List[Dict]:
        """
        Divide testo in chunk con overlap.

        Args:
            text: Testo da dividere
            metadata: Metadata da aggiungere a ogni chunk

        Returns:
            Lista di dict con chunk e metadata
        """
        if not text or not text.strip():
            return []

        # Split in paragrafi
        paragraphs = self._split_paragraphs(text)

        chunks = []
        current_chunk = ""
        chunk_paragraphs = []

        for para in paragraphs:
            # Se il paragrafo da solo è più lungo del chunk_size, dividilo
            if len(para) > self.chunk_size:
                # Prima salva il chunk corrente se esiste
                if current_chunk:
                    chunks.append(
                        self._create_chunk(
                            current_chunk,
                            len(chunks),
                            chunk_paragraphs,
                            metadata,
                        )
                    )
                    current_chunk = ""
                    chunk_paragraphs = []

                # Dividi il paragrafo lungo in sentence-based chunks
                para_chunks = self._chunk_long_paragraph(para)
                for pc in para_chunks:
                    chunks.append(
                        self._create_chunk(
                            pc,
                            len(chunks),
                            [para[:50] + "..."],  # Riferimento al paragrafo
                            metadata,
                        )
                    )
            else:
                # Controlla se aggiungere questo paragrafo supera chunk_size
                test_chunk = current_chunk + "\n\n" + para if current_chunk else para

                if len(test_chunk) <= self.chunk_size:
                    # Aggiungi al chunk corrente
                    current_chunk = test_chunk
                    chunk_paragraphs.append(para)
                else:
                    # Salva chunk corrente e inizia nuovo
                    if current_chunk:
                        chunks.append(
                            self._create_chunk(
                                current_chunk,
                                len(chunks),
                                chunk_paragraphs,
                                metadata,
                            )
                        )

                    # Inizia nuovo chunk con overlap
                    if self.overlap > 0 and current_chunk:
                        overlap_text = current_chunk[-self.overlap :]
                        current_chunk = overlap_text + "\n\n" + para
                    else:
                        current_chunk = para

                    chunk_paragraphs = [para]

        # Aggiungi ultimo chunk
        if current_chunk:
            chunks.append(
                self._create_chunk(
                    current_chunk,
                    len(chunks),
                    chunk_paragraphs,
                    metadata,
                )
            )

        logger.debug(f"Diviso testo in {len(chunks)} chunks")

        return chunks

    def _split_paragraphs(self, text: str) -> List[str]:
        """
        Divide testo in paragrafi.

        Args:
            text: Testo da dividere

        Returns:
            Lista di paragrafi
        """
        # Split su doppi newline
        paragraphs = re.split(r"\n\s*\n", text)

        # Pulisci e filtra paragrafi vuoti
        paragraphs = [p.strip() for p in paragraphs if p.strip()]

        return paragraphs

    def _chunk_long_paragraph(self, paragraph: str) -> List[str]:
        """
        Divide un paragrafo lungo in chunk basati su frasi.

        Args:
            paragraph: Paragrafo da dividere

        Returns:
            Lista di chunk
        """
        # Split in frasi
        sentences = self._split_sentences(paragraph)

        chunks = []
        current_chunk = ""

        for sentence in sentences:
            test_chunk = (
                current_chunk + " " + sentence if current_chunk else sentence
            )

            if len(test_chunk) <= self.chunk_size:
                current_chunk = test_chunk
            else:
                # Salva chunk corrente
                if current_chunk:
                    chunks.append(current_chunk)

                # Inizia nuovo chunk
                if len(sentence) > self.chunk_size:
                    # Frase troppo lunga, dividila forzatamente
                    chunks.extend(self._force_split(sentence))
                    current_chunk = ""
                else:
                    # Aggiungi overlap se possibile
                    if self.overlap > 0 and current_chunk:
                        overlap_text = current_chunk[-self.overlap :]
                        current_chunk = overlap_text + " " + sentence
                    else:
                        current_chunk = sentence

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def _split_sentences(self, text: str) -> List[str]:
        """
        Divide testo in frasi.

        Args:
            text: Testo da dividere

        Returns:
            Lista di frasi
        """
        # Pattern per split frasi (semplificato)
        sentence_endings = r"[.!?]+[\s]+"
        sentences = re.split(sentence_endings, text)

        # Pulisci frasi vuote
        sentences = [s.strip() for s in sentences if s.strip()]

        return sentences

    def _force_split(self, text: str) -> List[str]:
        """
        Forza split di testo che non può essere diviso semanticamente.

        Args:
            text: Testo da dividere

        Returns:
            Lista di chunk
        """
        chunks = []
        start = 0

        while start < len(text):
            end = start + self.chunk_size
            chunk = text[start:end]
            chunks.append(chunk)
            start = end - self.overlap if self.overlap > 0 else end

        return chunks

    def _create_chunk(
        self,
        text: str,
        index: int,
        paragraphs: List[str],
        metadata: Optional[Dict],
    ) -> Dict:
        """
        Crea dict per chunk con metadata.

        Args:
            text: Testo del chunk
            index: Indice del chunk
            paragraphs: Paragrafi nel chunk
            metadata: Metadata addizionali

        Returns:
            Dict con chunk e metadata
        """
        chunk = {
            "text": text.strip(),
            "chunk_index": index,
            "char_count": len(text),
            "word_count": len(text.split()),
        }

        # Aggiungi metadata se presenti
        if metadata:
            chunk.update(metadata)

        return chunk

    def chunk_document(
        self,
        text: str,
        url: str,
        title: str = "",
        page_metadata: Optional[Dict] = None,
    ) -> List[Dict]:
        """
        Chunka un documento con metadata completi.

        Args:
            text: Testo del documento
            url: URL del documento
            title: Titolo del documento
            page_metadata: Metadata addizionali della pagina

        Returns:
            Lista di chunk con metadata completi
        """
        # Prepara metadata base
        base_metadata = {
            "url": url,
            "page_title": title,
        }

        if page_metadata:
            base_metadata.update(page_metadata)

        # Chunka testo
        chunks = self.chunk_text(text, base_metadata)

        # Aggiungi total_chunks a ogni chunk
        total_chunks = len(chunks)
        for chunk in chunks:
            chunk["total_chunks"] = total_chunks

        return chunks


def chunk_text(
    text: str,
    chunk_size: int = 1000,
    overlap: int = 200,
    metadata: Optional[Dict] = None,
) -> List[Dict]:
    """
    Funzione helper per chunking testo.

    Args:
        text: Testo da chunkare
        chunk_size: Dimensione chunk
        overlap: Overlap tra chunk
        metadata: Metadata opzionali

    Returns:
        Lista di chunk
    """
    chunker = ContentChunker(chunk_size=chunk_size, overlap=overlap)
    return chunker.chunk_text(text, metadata)


if __name__ == "__main__":
    # Test ContentChunker
    test_text = """
    This is the first paragraph. It contains some content that should be in the first chunk.

    This is the second paragraph. It has more content that might push us to a second chunk depending on size.

    This is the third paragraph with even more content. We want to test how the chunker handles multiple paragraphs and creates overlapping chunks.

    Final paragraph here to complete the test document.
    """

    chunker = ContentChunker(chunk_size=150, overlap=30)
    chunks = chunker.chunk_document(
        text=test_text,
        url="https://example.com/test",
        title="Test Document",
    )

    print("=== Test Content Chunker ===")
    print(f"Total chunks: {len(chunks)}\n")

    for i, chunk in enumerate(chunks):
        print(f"Chunk {i + 1}:")
        print(f"  Char count: {chunk['char_count']}")
        print(f"  Word count: {chunk['word_count']}")
        print(f"  Text preview: {chunk['text'][:100]}...")
        print()

"""
Image Manager - Gestione immagini estratte da documenti.
Salva, organizza e recupera immagini associate ai documenti del RAG.
"""
import logging
import hashlib
from pathlib import Path
from typing import Dict, List, Optional
import base64

import config

logger = logging.getLogger(__name__)


class ImageManager:
    """Gestisce il salvataggio e recupero delle immagini estratte dai documenti."""

    def __init__(self, base_path: Optional[Path] = None):
        """
        Args:
            base_path: Directory base per salvare immagini (default: data/images)
        """
        self.base_path = base_path or Path(config.DATA_PATH) / "images"
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"ImageManager inizializzato: {self.base_path}")

    def save_document_images(
        self,
        collection_name: str,
        document_name: str,
        images: List[Dict]
    ) -> List[Dict]:
        """
        Salva le immagini estratte da un documento.

        Args:
            collection_name: Nome collection Qdrant
            document_name: Nome del documento (senza path)
            images: Lista di dict con chiavi: data, content_type, paragraph_index, etc.

        Returns:
            Lista di dict con informazioni immagini salvate: [{
                "saved_path": "data/images/collection/doc/img_001.png",
                "relative_path": "collection/doc/img_001.png",
                "paragraph_index": 3,
                "content_type": "image/png",
                "size_bytes": 12345
            }]
        """
        if not images:
            return []

        # Crea directory per collection e documento
        doc_clean_name = self._sanitize_filename(document_name)
        doc_dir = self.base_path / collection_name / doc_clean_name
        doc_dir.mkdir(parents=True, exist_ok=True)

        saved_images = []

        for idx, img_data in enumerate(images, start=1):
            try:
                # Determina estensione da content_type
                extension = self._get_extension_from_content_type(
                    img_data.get("content_type", "image/png")
                )

                # Nome file
                img_filename = f"img_{idx:03d}{extension}"
                img_path = doc_dir / img_filename

                # Salva immagine
                with open(img_path, "wb") as f:
                    f.write(img_data["data"])

                # Path relativo (per portabilità)
                relative_path = img_path.relative_to(self.base_path)

                saved_images.append({
                    "saved_path": str(img_path),
                    "relative_path": str(relative_path),
                    "paragraph_index": img_data.get("paragraph_index", -1),
                    "content_type": img_data.get("content_type", "image/png"),
                    "size_bytes": len(img_data["data"]),
                    "text_before": img_data.get("text_before", "")
                })

                logger.debug(f"Salvata immagine: {relative_path}")

            except Exception as e:
                logger.error(f"Errore salvando immagine {idx}: {e}")

        logger.info(f"Salvate {len(saved_images)}/{len(images)} immagini da {document_name}")
        return saved_images

    def get_image_path(self, relative_path: str) -> Optional[Path]:
        """
        Restituisce il path assoluto di un'immagine dato il path relativo.

        Args:
            relative_path: Path relativo (es: "collection/doc/img_001.png")

        Returns:
            Path assoluto se l'immagine esiste, None altrimenti
        """
        abs_path = self.base_path / relative_path
        return abs_path if abs_path.exists() else None

    def get_image_base64(self, relative_path: str) -> Optional[str]:
        """
        Restituisce l'immagine codificata in base64 (per embedding in HTML/JSON).

        Args:
            relative_path: Path relativo dell'immagine

        Returns:
            Stringa base64 dell'immagine, None se non trovata
        """
        img_path = self.get_image_path(relative_path)
        if not img_path:
            return None

        try:
            with open(img_path, "rb") as f:
                img_data = f.read()
            return base64.b64encode(img_data).decode("utf-8")
        except Exception as e:
            logger.error(f"Errore leggendo immagine {relative_path}: {e}")
            return None

    def delete_collection_images(self, collection_name: str) -> bool:
        """
        Elimina tutte le immagini di una collection.

        Args:
            collection_name: Nome collection

        Returns:
            True se eliminazione riuscita
        """
        collection_dir = self.base_path / collection_name
        if not collection_dir.exists():
            logger.warning(f"Collection images non trovate: {collection_name}")
            return False

        try:
            import shutil
            shutil.rmtree(collection_dir)
            logger.info(f"Eliminate immagini collection: {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Errore eliminando immagini {collection_name}: {e}")
            return False

    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitizza nome file per usarlo come nome directory.

        Args:
            filename: Nome file originale (es: "My Doc.docx")

        Returns:
            Nome sanitizzato (es: "my_doc")
        """
        # Rimuovi estensione
        name = Path(filename).stem

        # Sostituisci caratteri non validi
        name = name.lower()
        name = name.replace(" ", "_")
        name = "".join(c if c.isalnum() or c == "_" else "_" for c in name)

        # Limita lunghezza
        if len(name) > 100:
            # Usa hash per nomi troppo lunghi
            hash_suffix = hashlib.md5(filename.encode()).hexdigest()[:8]
            name = name[:90] + "_" + hash_suffix

        return name

    def _get_extension_from_content_type(self, content_type: str) -> str:
        """
        Determina estensione file da content-type.

        Args:
            content_type: MIME type (es: "image/png")

        Returns:
            Estensione con punto (es: ".png")
        """
        mapping = {
            "image/png": ".png",
            "image/jpeg": ".jpg",
            "image/jpg": ".jpg",
            "image/gif": ".gif",
            "image/bmp": ".bmp",
            "image/tiff": ".tiff",
            "image/webp": ".webp",
            "image/svg+xml": ".svg",
        }

        return mapping.get(content_type.lower(), ".png")

    def get_collection_stats(self, collection_name: str) -> Dict:
        """
        Restituisce statistiche sulle immagini di una collection.

        Args:
            collection_name: Nome collection

        Returns:
            Dict con statistiche: {
                "total_images": 42,
                "total_size_mb": 5.2,
                "documents": 10
            }
        """
        collection_dir = self.base_path / collection_name

        if not collection_dir.exists():
            return {"total_images": 0, "total_size_mb": 0, "documents": 0}

        total_images = 0
        total_size = 0
        documents = set()

        for img_file in collection_dir.rglob("*"):
            if img_file.is_file() and img_file.suffix.lower() in ['.png', '.jpg', '.jpeg', '.gif', '.bmp']:
                total_images += 1
                total_size += img_file.stat().st_size
                documents.add(img_file.parent.name)

        return {
            "total_images": total_images,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "documents": len(documents)
        }

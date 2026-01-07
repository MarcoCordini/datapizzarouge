"""
Utility per gestire i registry dei documenti scaricati.
Permette di visualizzare, validare e riparare registry.
"""
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional
import argparse

# Aggiungi root al path per import
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))


class RegistryManager:
    """Manager per operazioni sui registry documenti."""

    def __init__(self, domain: str):
        """
        Inizializza manager per un dominio.

        Args:
            domain: Nome del dominio
        """
        self.domain = domain
        self.documents_dir = Path("data") / "documents" / domain
        self.registry_path = self.documents_dir / ".registry.json"
        self.backup_path = self.documents_dir / ".registry.backup.json"
        self.history_dir = self.documents_dir / ".registry_history"

        self.registry = {}
        self._load_registry()

    def _load_registry(self):
        """Carica registry corrente."""
        if self.registry_path.exists():
            with open(self.registry_path, "r", encoding="utf-8") as f:
                self.registry = json.load(f)
            print(f"✓ Registry caricato: {len(self.registry)} documenti")
        else:
            print(f"⚠ Registry non trovato: {self.registry_path}")

    def show_stats(self):
        """Mostra statistiche del registry."""
        if not self.registry:
            print("Registry vuoto o non trovato.")
            return

        total_docs = len(self.registry)
        total_size = sum(doc.get("file_size", 0) for doc in self.registry.values())
        total_refs = sum(doc.get("reference_count", 0) for doc in self.registry.values())

        # Duplicati (documenti con più di 1 reference)
        duplicates = [doc for doc in self.registry.values() if doc.get("reference_count", 0) > 1]
        duplicate_count = len(duplicates)

        # Documento più referenziato
        most_referenced = max(
            self.registry.values(),
            key=lambda x: x.get("reference_count", 0)
        )

        print("\n" + "=" * 60)
        print("REGISTRY STATISTICS")
        print("=" * 60)
        print(f"Dominio: {self.domain}")
        print(f"Documenti totali: {total_docs}")
        print(f"Dimensione totale: {total_size / 1024:.2f} MB")
        print(f"Reference totali: {total_refs}")
        print(f"Documenti con duplicati: {duplicate_count}")
        print(f"\nDocumento più referenziato:")
        print(f"  Nome: {most_referenced['file_name']}")
        print(f"  Reference: {most_referenced['reference_count']}")
        print("=" * 60)

    def list_documents(self, show_references: bool = False):
        """
        Lista tutti i documenti nel registry.

        Args:
            show_references: Mostra tutte le reference per ogni documento
        """
        if not self.registry:
            print("Registry vuoto o non trovato.")
            return

        print("\n" + "=" * 60)
        print("DOCUMENTS IN REGISTRY")
        print("=" * 60)

        for i, (file_hash, doc) in enumerate(self.registry.items(), 1):
            print(f"\n{i}. {doc['file_name']}")
            print(f"   Hash: {file_hash[:16]}...")
            print(f"   Size: {doc.get('file_size', 0) / 1024:.2f} MB")
            print(f"   Downloaded: {doc.get('download_date', 'N/A')}")
            print(f"   References: {doc.get('reference_count', 0)}")

            if show_references:
                print("   URLs:")
                for ref in doc.get("references", []):
                    print(f"     - {ref}")

        print("=" * 60)

    def find_duplicates(self):
        """Trova e mostra documenti con duplicati."""
        duplicates = {
            hash_: doc for hash_, doc in self.registry.items()
            if doc.get("reference_count", 0) > 1
        }

        if not duplicates:
            print("Nessun duplicato trovato.")
            return

        print("\n" + "=" * 60)
        print("DUPLICATE DOCUMENTS")
        print("=" * 60)

        for i, (file_hash, doc) in enumerate(duplicates.items(), 1):
            print(f"\n{i}. {doc['file_name']}")
            print(f"   Hash: {file_hash[:16]}...")
            print(f"   Reference count: {doc['reference_count']}")
            print("   URLs:")
            for ref in doc.get("references", []):
                print(f"     - {ref}")

        print("=" * 60)
        print(f"Totale duplicati: {len(duplicates)}")

    def validate(self) -> bool:
        """
        Valida integrità del registry.
        Controlla che i file esistano e che gli hash siano corretti.

        Returns:
            True se tutto OK, False se ci sono problemi
        """
        print("\n" + "=" * 60)
        print("VALIDATING REGISTRY")
        print("=" * 60)

        if not self.registry:
            print("Registry vuoto o non trovato.")
            return False

        issues = []

        for file_hash, doc in self.registry.items():
            file_path = Path(doc.get("file_path", ""))

            # Controlla esistenza file
            if not file_path.exists():
                issues.append(f"File mancante: {doc['file_name']} ({file_path})")
                continue

            # Controlla hash (calcola hash del file e confronta)
            try:
                import hashlib
                sha256_hash = hashlib.sha256()
                with open(file_path, "rb") as f:
                    for byte_block in iter(lambda: f.read(4096), b""):
                        sha256_hash.update(byte_block)
                actual_hash = sha256_hash.hexdigest()

                if actual_hash != file_hash:
                    issues.append(f"Hash non corrispondente: {doc['file_name']}")
            except Exception as e:
                issues.append(f"Errore validando {doc['file_name']}: {e}")

        if issues:
            print("\n⚠ PROBLEMI TROVATI:")
            for issue in issues:
                print(f"  - {issue}")
            print("=" * 60)
            return False
        else:
            print("\n✓ Registry valido! Tutti i file esistono e gli hash corrispondono.")
            print("=" * 60)
            return True

    def restore_from_backup(self):
        """Ripristina registry da backup."""
        if not self.backup_path.exists():
            print("⚠ Backup non trovato!")
            return False

        try:
            import shutil
            shutil.copy(self.backup_path, self.registry_path)
            print(f"✓ Registry ripristinato da backup: {self.backup_path}")
            self._load_registry()
            return True
        except Exception as e:
            print(f"✗ Errore ripristinando da backup: {e}")
            return False

    def list_backups(self):
        """Lista backup disponibili."""
        if not self.history_dir.exists():
            print("Nessun backup storico trovato.")
            return

        backups = sorted(self.history_dir.glob("registry_*.json"))

        if not backups:
            print("Nessun backup storico trovato.")
            return

        print("\n" + "=" * 60)
        print("AVAILABLE BACKUPS")
        print("=" * 60)

        for i, backup in enumerate(backups, 1):
            print(f"{i}. {backup.name}")

        print("=" * 60)


def main():
    """Main CLI."""
    parser = argparse.ArgumentParser(
        description="Gestione registry documenti crawlati"
    )
    parser.add_argument(
        "domain",
        help="Dominio da gestire (es: www.example.com)"
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Mostra statistiche registry"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Lista documenti nel registry"
    )
    parser.add_argument(
        "--show-refs",
        action="store_true",
        help="Mostra tutte le reference (con --list)"
    )
    parser.add_argument(
        "--duplicates",
        action="store_true",
        help="Trova e mostra duplicati"
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Valida integrità registry"
    )
    parser.add_argument(
        "--restore",
        action="store_true",
        help="Ripristina da backup"
    )
    parser.add_argument(
        "--backups",
        action="store_true",
        help="Lista backup disponibili"
    )

    args = parser.parse_args()

    # Crea manager
    manager = RegistryManager(args.domain)

    # Esegui comando
    if args.stats:
        manager.show_stats()
    elif args.list:
        manager.list_documents(show_references=args.show_refs)
    elif args.duplicates:
        manager.find_duplicates()
    elif args.validate:
        manager.validate()
    elif args.restore:
        manager.restore_from_backup()
    elif args.backups:
        manager.list_backups()
    else:
        # Default: mostra stats
        manager.show_stats()


if __name__ == "__main__":
    main()

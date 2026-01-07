"""
Utility per ri-scaricare documenti dal registry.
Utile quando i file fisici sono stati persi ma il registry esiste ancora.
"""
import json
import sys
import requests
from pathlib import Path
from typing import List
import argparse
from tqdm import tqdm

# Aggiungi root al path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

import config


def load_registry(domain: str) -> dict:
    """
    Carica registry per un dominio.

    Args:
        domain: Nome del dominio

    Returns:
        Dict con registry
    """
    registry_path = Path("data") / "documents" / domain / ".registry.json"

    if not registry_path.exists():
        print(f"⚠ Registry non trovato: {registry_path}")
        return {}

    with open(registry_path, "r", encoding="utf-8") as f:
        registry = json.load(f)

    print(f"✓ Registry caricato: {len(registry)} documenti")
    return registry


def check_missing_files(registry: dict) -> List[tuple]:
    """
    Controlla quali file mancano.

    Args:
        registry: Registry da controllare

    Returns:
        Lista di (file_hash, doc_info) per file mancanti
    """
    missing = []

    for file_hash, doc in registry.items():
        file_path = Path(doc.get("file_path", ""))

        if not file_path.exists():
            # Prendi la prima reference per re-download
            url = doc.get("references", [])[0] if doc.get("references") else None
            if url:
                missing.append((file_hash, doc, url))

    return missing


def download_file(url: str, save_path: Path, timeout: int = 180) -> bool:
    """
    Scarica un file da URL.

    Args:
        url: URL da scaricare
        save_path: Path dove salvare
        timeout: Timeout in secondi

    Returns:
        True se successo, False altrimenti
    """
    try:
        # Usa headers da config
        headers = {"User-Agent": config.USER_AGENT}

        response = requests.get(url, headers=headers, timeout=timeout, stream=True)
        response.raise_for_status()

        # Crea directory se non esiste
        save_path.parent.mkdir(parents=True, exist_ok=True)

        # Salva file
        total_size = int(response.headers.get("content-length", 0))

        with open(save_path, "wb") as f:
            if total_size:
                # Progress bar per file grandi
                with tqdm(total=total_size, unit="B", unit_scale=True, desc=save_path.name) as pbar:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                        pbar.update(len(chunk))
            else:
                # Nessuna info size, scrivi direttamente
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

        return True

    except Exception as e:
        print(f"✗ Errore scaricando {url}: {e}")
        return False


def redownload_missing(domain: str, dry_run: bool = False):
    """
    Re-download documenti mancanti dal registry.

    Args:
        domain: Dominio da processare
        dry_run: Se True, mostra solo cosa verrebbe scaricato senza fare download
    """
    print("\n" + "=" * 60)
    print("RE-DOWNLOAD MISSING DOCUMENTS")
    print("=" * 60)

    # Carica registry
    registry = load_registry(domain)

    if not registry:
        return

    # Controlla file mancanti
    print("\nControllando file mancanti...")
    missing = check_missing_files(registry)

    if not missing:
        print("✓ Tutti i file esistono! Nessun re-download necessario.")
        return

    print(f"\n⚠ Trovati {len(missing)} file mancanti:")
    for i, (file_hash, doc, url) in enumerate(missing, 1):
        print(f"{i}. {doc['file_name']}")
        print(f"   URL: {url}")

    if dry_run:
        print("\n[DRY RUN] Nessun download effettuato.")
        return

    # Chiedi conferma
    response = input(f"\nScaricare {len(missing)} file? (y/n): ")
    if response.lower() != "y":
        print("Operazione annullata.")
        return

    # Re-download
    print("\nRe-downloading file...")
    success_count = 0
    failed = []

    for file_hash, doc, url in missing:
        file_path = Path(doc["file_path"])
        print(f"\n📥 {doc['file_name']}...")

        if download_file(url, file_path):
            success_count += 1
            print(f"   ✓ Salvato: {file_path}")
        else:
            failed.append((doc['file_name'], url))

    # Riepilogo
    print("\n" + "=" * 60)
    print("RIEPILOGO RE-DOWNLOAD")
    print("=" * 60)
    print(f"Successi: {success_count}/{len(missing)}")

    if failed:
        print(f"Falliti: {len(failed)}")
        print("\nFile falliti:")
        for file_name, url in failed:
            print(f"  - {file_name}")
            print(f"    {url}")

    print("=" * 60)


def main():
    """Main CLI."""
    parser = argparse.ArgumentParser(
        description="Re-download documenti mancanti dal registry"
    )
    parser.add_argument(
        "domain",
        help="Dominio da processare (es: www.example.com)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostra cosa verrebbe scaricato senza fare download"
    )

    args = parser.parse_args()

    redownload_missing(args.domain, dry_run=args.dry_run)


if __name__ == "__main__":
    main()

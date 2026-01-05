"""
Script di test per verificare che l'API FastAPI funzioni correttamente.

Uso:
    python test_api.py
"""
import requests
import json
import sys

BASE_URL = "http://localhost:8000"


def print_result(test_name, success, message=""):
    """Stampa risultato test."""
    status = "✓" if success else "✗"
    color = "\033[92m" if success else "\033[91m"
    reset = "\033[0m"
    print(f"{color}{status}{reset} {test_name}")
    if message:
        print(f"  {message}")


def test_health():
    """Test health endpoint."""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_result(
                "Health Check",
                data["qdrant_connected"],
                f"Status: {data['status']}, Qdrant: {data['qdrant_connected']}",
            )
            return data["qdrant_connected"]
        else:
            print_result("Health Check", False, f"Status code: {response.status_code}")
            return False
    except Exception as e:
        print_result("Health Check", False, str(e))
        return False


def test_list_collections():
    """Test lista collection."""
    try:
        response = requests.get(f"{BASE_URL}/api/collections", timeout=5)
        if response.status_code == 200:
            collections = response.json()
            print_result(
                "Lista Collection",
                len(collections) > 0,
                f"Trovate {len(collections)} collection: {collections}",
            )
            return collections if collections else None
        else:
            print_result(
                "Lista Collection", False, f"Status code: {response.status_code}"
            )
            return None
    except Exception as e:
        print_result("Lista Collection", False, str(e))
        return None


def test_collection_info(collection_name):
    """Test info collection."""
    try:
        response = requests.get(
            f"{BASE_URL}/api/collections/{collection_name}", timeout=5
        )
        if response.status_code == 200:
            info = response.json()
            print_result(
                f"Info Collection '{collection_name}'",
                True,
                f"Points: {info['points_count']}, Status: {info['status']}",
            )
            return True
        else:
            print_result(
                f"Info Collection '{collection_name}'",
                False,
                f"Status code: {response.status_code}",
            )
            return False
    except Exception as e:
        print_result(f"Info Collection '{collection_name}'", False, str(e))
        return False


def test_query(collection_name):
    """Test query RAG."""
    try:
        payload = {
            "collection": collection_name,
            "query": "test query",
            "top_k": 3,
            "include_sources": True,
        }

        response = requests.post(
            f"{BASE_URL}/api/query", json=payload, timeout=60  # Timeout lungo per query
        )

        if response.status_code == 200:
            result = response.json()
            print_result(
                f"Query RAG '{collection_name}'",
                True,
                f"Risposta: {result['answer'][:100]}... | Risultati: {result['num_results']}",
            )
            return True
        else:
            print_result(
                f"Query RAG '{collection_name}'",
                False,
                f"Status code: {response.status_code}",
            )
            return False
    except Exception as e:
        print_result(f"Query RAG '{collection_name}'", False, str(e))
        return False


def test_retrieval(collection_name):
    """Test retrieval documenti."""
    try:
        payload = {
            "collection": collection_name,
            "query": "test",
            "top_k": 5,
        }

        response = requests.post(
            f"{BASE_URL}/api/retrieval", json=payload, timeout=30
        )

        if response.status_code == 200:
            results = response.json()
            print_result(
                f"Retrieval '{collection_name}'",
                len(results) > 0,
                f"Trovati {len(results)} documenti",
            )
            return True
        else:
            print_result(
                f"Retrieval '{collection_name}'",
                False,
                f"Status code: {response.status_code}",
            )
            return False
    except Exception as e:
        print_result(f"Retrieval '{collection_name}'", False, str(e))
        return False


def main():
    """Main test runner."""
    print("=" * 60)
    print("Test API DataPizzaRouge")
    print("=" * 60)
    print(f"Base URL: {BASE_URL}")
    print()

    # Test 1: Health
    if not test_health():
        print("\n❌ API non disponibile o Qdrant non connesso!")
        print("Assicurati che:")
        print("  1. API sia avviata: uvicorn api:app --reload")
        print("  2. Qdrant sia in esecuzione: docker run -p 6333:6333 qdrant/qdrant")
        sys.exit(1)

    print()

    # Test 2: Lista Collection
    collections = test_list_collections()
    if not collections:
        print("\n⚠️  Nessuna collection trovata!")
        print("Esegui prima:")
        print("  python cli.py crawl <URL>")
        print("  python cli.py ingest --domain <domain> --collection test_latest")
        sys.exit(0)

    print()

    # Test 3-5: Per ogni collection
    for collection in collections[:3]:  # Test max 3 collection
        test_collection_info(collection)
        test_retrieval(collection)
        test_query(collection)
        print()

    print("=" * 60)
    print("✓ Tutti i test completati!")
    print("=" * 60)
    print("\nAPI pronta per l'uso!")
    print("Documentazione: http://localhost:8000/docs")


if __name__ == "__main__":
    main()

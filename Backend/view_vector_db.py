"""
Inspect the CyberLaw Bot vector database.

The store is a NumPy embeddings matrix (vector_db/embeddings.npy) plus a JSON
document list (vector_db/law_kb.json). This replaces the old ChromaDB/OpenAI
based inspector, which no longer matched the storage format and crashed on
import because `chromadb` is not a project dependency.

Usage:
    python view_vector_db.py                    # summary + sample chunks
    python view_vector_db.py --samples 5        # show 5 sample chunks
    python view_vector_db.py --search "bail"    # semantic search (needs GEMINI_API_KEY)
"""
import json
import argparse
from pathlib import Path
from collections import Counter

import numpy as np

# Resolve the vector_db directory relative to the project root (parent of Backend/).
BACKEND_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = BACKEND_DIR.parent
DEFAULT_DB_DIR = PROJECT_ROOT / "vector_db"


def load_store(db_dir):
    """Load documents (JSON) and embeddings (.npy) from the vector_db directory."""
    db_path = Path(db_dir)
    db_file = db_path / "law_kb.json"
    emb_file = db_path / "embeddings.npy"

    if not db_file.exists():
        raise FileNotFoundError(f"Documents file not found: {db_file}")

    with open(db_file, "r", encoding="utf-8") as f:
        documents = json.load(f)

    embeddings = np.load(emb_file) if emb_file.exists() else None
    return documents, embeddings, db_file, emb_file


def summarize(documents, embeddings, db_file, emb_file, samples=3, max_text=200):
    """Print dataset stats and a few sample chunks (no API key required)."""
    print("=" * 60)
    print("CyberLaw Bot - Vector DB Inspector")
    print("=" * 60)
    print(f"Documents file : {db_file}")
    print(f"Embeddings file: {emb_file if embeddings is not None else 'MISSING'}")
    print(f"Total documents: {len(documents)}")

    if embeddings is not None:
        print(f"Embeddings     : shape={embeddings.shape}, dtype={embeddings.dtype}")
        print(f"                 {embeddings.nbytes / (1024 * 1024):.2f} MB in memory")
        if len(documents) != embeddings.shape[0]:
            print(f"[WARN] document count ({len(documents)}) != embedding rows ({embeddings.shape[0]})")
    print()

    law_counts = Counter(d.get("metadata", {}).get("law", "Unknown") for d in documents)
    print("Documents by law:")
    for law, count in law_counts.most_common():
        print(f"  - {law}: {count}")
    print()

    src_counts = Counter(d.get("metadata", {}).get("source", "Unknown") for d in documents)
    print("Documents by source file:")
    for src, count in src_counts.most_common():
        print(f"  - {src}: {count}")
    print()

    if documents:
        avg_len = sum(len(d.get("text", "")) for d in documents) / len(documents)
        print(f"Average chunk length: {avg_len:.0f} characters")
        print()

    print(f"Sample chunks (first {min(samples, len(documents))}):")
    for d in documents[:samples]:
        md = d.get("metadata", {})
        text = d.get("text", "")
        preview = text[:max_text] + ("..." if len(text) > max_text else "")
        print("-" * 60)
        print(f"id={d.get('id')}  law={md.get('law')}  section={md.get('section')}  page={md.get('page')}")
        print(f"  {preview}")
    print("=" * 60)


def search(query, db_dir, top_k=5):
    """Semantic search using the same pipeline as the app (requires GEMINI_API_KEY)."""
    import sys
    sys.path.insert(0, str(BACKEND_DIR))
    # Imported lazily so plain inspection works without an API key.
    from rag_pipeline import load_vector_db, get_query_embedding, search_similar_documents

    documents, embeddings = load_vector_db(str(db_dir))
    query_embedding = get_query_embedding(query)
    results = search_similar_documents(query_embedding, embeddings, documents, top_k=top_k)

    print(f"\nSearch: '{query}' (top {top_k})")
    print("=" * 60)
    for i, r in enumerate(results, 1):
        md = r["metadata"]
        print(f"{i}. [{md.get('law')} - {md.get('section')}] (page {md.get('page')}) sim={r['similarity']:.4f}")
        print(f"   {r['text'][:200]}...")
        print("-" * 60)


def main():
    parser = argparse.ArgumentParser(description="Inspect the CyberLaw Bot vector database (NumPy + JSON).")
    parser.add_argument("--db-dir", default=str(DEFAULT_DB_DIR), help="Path to the vector_db directory")
    parser.add_argument("--samples", type=int, default=3, help="Number of sample chunks to show")
    parser.add_argument("--max-length", type=int, default=200, help="Max characters per sample preview")
    parser.add_argument("--search", type=str, help="Run a semantic search (requires GEMINI_API_KEY)")
    parser.add_argument("--top-k", type=int, default=5, help="Number of results for --search")
    args = parser.parse_args()

    db_dir = Path(args.db_dir)

    if args.search:
        search(args.search, db_dir, args.top_k)
        return

    try:
        documents, embeddings, db_file, emb_file = load_store(db_dir)
    except FileNotFoundError as e:
        print(f"[ERROR] {e}")
        print("Run build_vector_db.py first to create the database.")
        return

    summarize(documents, embeddings, db_file, emb_file, samples=args.samples, max_text=args.max_length)


if __name__ == "__main__":
    main()

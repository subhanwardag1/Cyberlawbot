import os
import json
import time
import numpy as np
from pathlib import Path
import google.generativeai as genai

# Load .env for local runs (real environment variables take precedence).
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def build_vector_db_from_chunks(chunks, db_dir="vector_db", gemini_api_key=None, batch_size=50):
    """
    Build a vector database using NumPy binary storage for embeddings
    and JSON for text/metadata. Uses Google Gemini API for generating embeddings.
    
    Optimizations:
    - Batch embedding API calls (send list of texts in one call)
    - Save embeddings as .npy for 10x faster loading
    - Save text/metadata as separate compact JSON (no embeddings bloat)
    - Filter out failed embeddings instead of inserting zero-vectors
    """
    # Create database directory
    db_path = Path(db_dir)
    db_path.mkdir(exist_ok=True)
    
    texts = [c["text"] for c in chunks]
    metadatas = [{"law": c["law_name"], "section": c["section"], "page": c.get("page"), "source": Path(c["source_path"]).name} for c in chunks]
    
    if gemini_api_key:
        genai.configure(api_key=gemini_api_key)
    else:
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    
    print(f"[*] Generating embeddings using Gemini API (gemini-embedding-001)...")
    print(f"    Total documents: {len(texts)}, Batch size: {batch_size}")
    
    all_embeddings = []
    failed_indices = []
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(texts) - 1) // batch_size + 1
        print(f"   Batch {batch_num}/{total_batches} ({len(batch)} docs)...")
        
        max_retries = 5
        for attempt in range(max_retries):
            try:
                # Batch embedding: send entire list in ONE API call
                result = genai.embed_content(
                    model="models/gemini-embedding-001",
                    content=batch,
                    task_type="retrieval_document"
                )
                all_embeddings.extend(result['embedding'])
                print(f"      [OK] Embedded {min(i + batch_size, len(texts))}/{len(texts)} documents")
                time.sleep(1)  # One delay per batch, not per document
                break
            except Exception as e:
                error_str = str(e)
                if "429" in error_str and attempt < max_retries - 1:
                    wait_time = 30 * (attempt + 1)
                    print(f"   [RATE LIMIT] Waiting {wait_time}s before retry ({attempt+1}/{max_retries})...")
                    time.sleep(wait_time)
                elif attempt < max_retries - 1:
                    print(f"   [WARNING] Batch error: {e}, retrying...")
                    time.sleep(5)
                else:
                    print(f"   [ERROR] Batch {batch_num} failed after {max_retries} retries: {e}")
                    # Track failed indices so we can exclude them
                    for j in range(len(batch)):
                        failed_indices.append(i + j)
                    break
    
    # Remove failed documents
    if failed_indices:
        print(f"   [WARNING] {len(failed_indices)} documents failed embedding, excluding from DB")
        failed_set = set(failed_indices)
        valid = [(t, m, e) for idx, (t, m, e) in enumerate(zip(texts, metadatas, all_embeddings)) if idx not in failed_set]
        if valid:
            texts, metadatas, all_embeddings = zip(*valid)
            texts, metadatas, all_embeddings = list(texts), list(metadatas), list(all_embeddings)
        else:
            print("[ERROR] All embeddings failed!")
            return str(db_path), "law_kb"
    
    # Save embeddings as NumPy binary (.npy) — fast to load
    embeddings_array = np.array(all_embeddings, dtype=np.float32)
    embeddings_file = db_path / "embeddings.npy"
    np.save(embeddings_file, embeddings_array)
    print(f"[OK] Saved embeddings: {embeddings_file} ({embeddings_array.shape})")
    
    # Save text + metadata as compact JSON (no embeddings — much smaller)
    documents_data = []
    for i, (text, metadata) in enumerate(zip(texts, metadatas)):
        documents_data.append({
            "id": f"doc-{i}",
            "text": text,
            "metadata": metadata
        })
    
    db_file = db_path / "law_kb.json"
    with open(db_file, 'w', encoding='utf-8') as f:
        json.dump(documents_data, f, ensure_ascii=False, indent=2)
    
    print(f"[OK] Saved {len(documents_data)} documents to {db_file}")
    print(f"     Embeddings: {embeddings_file} ({embeddings_array.nbytes / 1024:.0f} KB)")
    print(f"     Documents:  {db_file}")
    
    return str(db_path), "law_kb"


if __name__ == "__main__":
    from extract_text import extract_and_chunk_pdf
    
    # Define your PDF files and their law names
    pdf_files = [
        ("CrPC.pdf", "Criminal Procedure Code"),
        ("PECA 2016.pdf", "PECA 2016"),
        ("PECA 2025 Amendment.pdf", "PECA 2025 Amendment"),
        ("PPC.pdf", "Pakistan Penal Code")
    ]
    
    print("[*] Starting to extract text from PDFs...")
    all_chunks = []
    
    for pdf_path, law_name in pdf_files:
        pdf_full_path = Path(__file__).parent / pdf_path
        if pdf_full_path.exists():
            print(f"\n[*] Processing: {law_name} ({pdf_full_path.name})")
            chunks = extract_and_chunk_pdf(str(pdf_full_path), law_name)
            all_chunks.extend(chunks)
            print(f"   [OK] Extracted {len(chunks)} chunks")
        else:
            print(f"   [WARNING] {pdf_full_path} not found, skipping...")
    
    print(f"\n[*] Total chunks extracted: {len(all_chunks)}")
    
    if len(all_chunks) == 0:
        print("[ERROR] No chunks extracted! Please check your PDF paths.")
    else:
        print("\n[*] Building vector database...")
        
        # API key is read from the GEMINI_API_KEY environment variable (see load_dotenv above).
        
        db_path, collection_name = build_vector_db_from_chunks(
            all_chunks,
            db_dir="vector_db",
        )
        print(f"[OK] Vector database built successfully!")
        print(f"   Collection: {collection_name}")
        print(f"   Location: {Path(db_path).absolute()}")
        print(f"\n[INFO] Database saved in {db_path}/")
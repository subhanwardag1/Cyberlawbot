import sys
import os
from rag_pipeline import query_and_answer, load_vector_db

def main():
    print("\n" + "="*60)
    print("[*] Interactive Legal Assistant (RAG System)")
    print("="*60)
    print("Type 'exit', 'quit', or 'q' to stop.")
    print("-" * 60)

    db_dir = "vector_db"
    
    # Check if DB exists
    if not os.path.exists(db_dir):
        print(f"[ERROR] Vector database directory '{db_dir}' not found.")
        print("Please run 'build_vector_db.py' first.")
        return

    # Pre-load the vector database once at startup (cached for all queries)
    
    try:
        documents, embeddings = load_vector_db(db_dir)
    except Exception as e:
        print(f"[ERROR] Failed to load database: {e}")
        return

    while True:
        try:
            question = input("\n[?] Enter your legal question: ").strip()
            
            if not question:
                continue
                
            if question.lower() in ['exit', 'quit', 'q']:
                print("\n[*] Exiting. Goodbye!")
                break
            
            print("\n[*] Generating answer...")
            
            result = query_and_answer(question, db_dir=db_dir, top_k=6)
            
            print("\n" + "="*60)
            print("[*] ANSWER:")
            print("="*60)
            print(result["answer"])
            
            if result["references"]:
                print("\n" + "-"*60)
                print("[*] REFERENCES:")
                print("-"*60)
                for i, ref in enumerate(result["references"], 1):
                    print(f"{i}. {ref['label']} (Page {ref['page']})")

        except KeyboardInterrupt:
            print("\n\n[*] Exiting. Goodbye!")
            break
        except Exception as e:
            print(f"\n[ERROR] An error occurred: {e}")

if __name__ == "__main__":
    main()

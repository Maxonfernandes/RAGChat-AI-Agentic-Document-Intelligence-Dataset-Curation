import os
import sys
from pathlib import Path

# Set up paths
backend_dir = str(Path(__file__).resolve().parent.parent)
agentify_dir = str(Path(__file__).resolve().parent.parent / "agentify")
for p in [backend_dir, agentify_dir]:
    if p not in sys.path:
        sys.path.insert(0, p)

from file_processor import FileProcessor
from embedder import VectorEmbedder
from utils import ensure_dir
from config import INPUT_DIR, OUTPUT_DIR

def main():
    ensure_dir(INPUT_DIR)
    ensure_dir(OUTPUT_DIR)

    print("=== RAGChat Document Structurisation Pipeline ===")
    embedder = VectorEmbedder()

    # Report Astra DB status
    status = embedder.vector_db.status()
    print(f"Vector DB Status: {status.get('message')}")
    print(f"Existing document chunks in store: {status.get('document_chunks')}")

    # Process all files in INPUT_DIR
    files = [f for f in os.listdir(INPUT_DIR) if os.path.isfile(os.path.join(INPUT_DIR, f))]
    if not files:
        print(f"No files found in {INPUT_DIR}. Add documents to embed.")
        return

    print(f"Found {len(files)} file(s) to process in {INPUT_DIR}:")
    total_chunks = 0
    for filename in files:
        file_path = os.path.join(INPUT_DIR, filename)
        print(f"-> Processing and embedding {filename}...")
        chunks_embedded = embedder.embed_file(file_path)
        total_chunks += chunks_embedded
        print(f"   Successfully embedded {chunks_embedded} chunks.")

    print(f"\nCompleted! Total new chunks embedded: {total_chunks}")
    print(f"Total chunks in database: {embedder.vector_db.count()}")

if __name__ == "__main__":
    main()
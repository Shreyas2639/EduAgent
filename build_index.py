"""
Run this ONCE to build the FAISS vector index from your knowledge base.
Command: python build_index.py
"""
from rag.loader import load_text_files
from rag.embedder import build_index

if __name__ == "__main__":
    print("Loading knowledge base...")
    documents = load_text_files()
    if documents:
        print(f"Building FAISS index from {len(documents)} chunks...")
        index, docs = build_index(documents)
        print(f"Index built! {index.ntotal} vectors stored.")
    else:
        print("No documents found! Add .txt files to knowledge_base/notes/")

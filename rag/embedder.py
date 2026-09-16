import os
import faiss
import pickle
import numpy as np
from typing import List
from langchain_core.documents import Document
from sentence_transformers import SentenceTransformer

INDEX_DIR = os.path.join(os.path.dirname(__file__), '..', 'vector_store', 'faiss_index')
INDEX_FILE = os.path.join(INDEX_DIR, 'index.faiss')
DOCS_FILE = os.path.join(INDEX_DIR, 'documents.pkl')
_model = None

def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer('all-MiniLM-L6-v2')
    return _model

def build_index(documents: List[Document]):
    os.makedirs(INDEX_DIR, exist_ok=True)
    model = get_model()
    texts = [doc.page_content for doc in documents]
    embeddings = model.encode(texts, show_progress_bar=True)
    embeddings = np.array(embeddings).astype('float32')
    dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)
    faiss.write_index(index, INDEX_FILE)
    with open(DOCS_FILE, 'wb') as f:
        pickle.dump(documents, f)
    print(f"FAISS index built with {len(documents)} documents.")
    return index, documents

def load_index():
    if not os.path.exists(INDEX_FILE):
        return None, []
    index = faiss.read_index(INDEX_FILE)
    with open(DOCS_FILE, 'rb') as f:
        documents = pickle.load(f)
    return index, documents

def embed_text(text: str) -> np.ndarray:
    model = get_model()
    embedding = model.encode([text])
    return np.array(embedding).astype('float32')
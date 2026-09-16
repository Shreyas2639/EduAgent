from rag.embedder import load_index, embed_text, build_index
from rag.loader import load_text_files
from typing import List

_index = None
_documents = None

def get_retriever():
    global _index, _documents
    if _index is None:
        _index, _documents = load_index()
        if _index is None:
            print("No FAISS index found. Building from knowledge base...")
            docs = load_text_files()
            if docs:
                _index, _documents = build_index(docs)
    return _index, _documents

def retrieve(query: str, top_k: int = 3) -> List[str]:
    index, documents = get_retriever()
    if index is None or not documents:
        return ["No course materials found. Using general knowledge."]
    query_embedding = embed_text(query)
    distances, indices = index.search(query_embedding, top_k)
    results = []
    for i, idx in enumerate(indices[0]):
        if idx < len(documents) and distances[0][i] < 2.0:
            doc = documents[idx]
            results.append(f"[Source: {doc.metadata.get('source', 'notes')}]\n{doc.page_content}")
    return results if results else ["No relevant notes found for this topic."]
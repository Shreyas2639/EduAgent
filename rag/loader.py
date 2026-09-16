import os
from typing import List
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

NOTES_DIR = os.path.join(os.path.dirname(__file__), '..', 'knowledge_base', 'notes')

def load_text_files() -> List[Document]:
    documents = []
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    if not os.path.exists(NOTES_DIR):
        print(f"Notes directory not found: {NOTES_DIR}")
        return documents
    for filename in os.listdir(NOTES_DIR):
        filepath = os.path.join(NOTES_DIR, filename)
        if filename.endswith('.txt'):
            with open(filepath, 'r', encoding='utf-8') as f:
                text = f.read()
            chunks = splitter.split_text(text)
            for i, chunk in enumerate(chunks):
                documents.append(Document(
                    page_content=chunk,
                    metadata={"source": filename, "topic": filename.replace('.txt','').replace('_',' '), "chunk": i}
                ))
        elif filename.endswith('.pdf'):
            try:
                from pypdf import PdfReader
                reader = PdfReader(filepath)
                text = "\n".join(page.extract_text() for page in reader.pages if page.extract_text())
                chunks = splitter.split_text(text)
                for i, chunk in enumerate(chunks):
                    documents.append(Document(page_content=chunk, metadata={"source": filename, "chunk": i}))
            except Exception as e:
                print(f"Error loading PDF {filename}: {e}")
    print(f"Loaded {len(documents)} chunks from knowledge base.")
    return documents
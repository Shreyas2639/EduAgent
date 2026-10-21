"""Small, inspectable information-source tool for the Project 1 curriculum.

No embeddings, model downloads, or untrusted serialized indexes are needed.
The original FAISS implementation remains available in rag/retriever.py.
"""
import re
from pathlib import Path

NOTES_DIR = Path(__file__).resolve().parents[1] / "knowledge_base" / "notes"


def retrieve(query: str, top_k: int = 3) -> list[str]:
    terms = set(re.findall(r"[a-z]+", query.lower())) - {"python", "explain", "me", "on"}
    ranked = []
    for path in sorted(NOTES_DIR.glob("*.txt")):
        text = path.read_text(encoding="utf-8")
        title_terms = set(re.findall(r"[a-z]+", path.stem.lower()))
        words = set(re.findall(r"[a-z]+", text.lower()))
        score = 3 * len(terms & title_terms) + len(terms & words)
        if score:
            ranked.append((score, path.name, text))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    return [f"[Source: {name}]\n{text}" for _, name, text in ranked[:top_k]]

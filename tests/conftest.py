import pytest
from agents import llm
from memory import long_term_db as db
from demo_support import SimulatedGroq


@pytest.fixture
def tutor(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "memory.db"))
    db.init_db()
    db.get_or_create_student("learner", "Simulated Learner")
    monkeypatch.setenv("GROQ_API_KEY", "offline-test-placeholder")
    monkeypatch.setattr(llm, "Groq", SimulatedGroq)
    SimulatedGroq.prompts = []
    llm.get_client.cache_clear()
    from graph.workflow import build_workflow
    yield build_workflow()
    llm.get_client.cache_clear()


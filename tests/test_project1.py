import json
import sqlite3
from types import SimpleNamespace

import pytest
from langgraph.types import Command

from graph.workflow import request_state
from memory import long_term_db as db
from demo_support import SimulatedGroq


def cfg(thread):
    return {"configurable": {"thread_id": thread}}


def ask(graph, thread="a", message="Explain Python loops", changes=None, submission=None):
    return graph.invoke(request_state("learner", message, memory_changes=changes,
                                      quiz_submission=submission), cfg(thread))


def approve(graph, thread="a", decision=True):
    return graph.invoke(Command(resume={"approved": decision}), cfg(thread))


def seed(graph):
    ask(graph, changes={"preferred_style": "bullet_points", "level": "intermediate"})
    approve(graph)


def test_normal_request_uses_real_notes_and_pauses_before_write(tutor):
    result = ask(tutor)
    assert "[Source:" in result["source_chunks"][0]
    assert result["response"]
    assert result["__interrupt__"]
    assert db.get_memory_records("learner") == []
    assert result["steps"][:6] == ["start", "load_memory", "safety", "coordinator", "retrieve_course_notes", "tutor"]
    assert approve(tutor)["memory_status"] == "saved"
    assert db.get_learner_profile("learner")["last_topic"] == "loops"


def test_two_records_retrieved_in_new_thread_and_used_by_tutor(tutor):
    seed(tutor)
    result = ask(tutor, thread="new-thread")
    assert {record["key"] for record in result["retrieved_memories"]} == {"level", "preferred_style"}
    assert result["chat_history"] == ""
    assert result["profile"]["level"] == "intermediate"
    assert result["response"].startswith("- SIMULATION:")
    assert "Student Level: intermediate" in SimulatedGroq.prompts[-1]
    assert "Preferred format: bullet_points" in SimulatedGroq.prompts[-1]
    assert all(record["source_thread"] == "a" for record in result["retrieved_memories"])


def test_correction_replaces_record_and_later_prompt_uses_it(tutor):
    seed(tutor)
    ask(tutor, thread="correction", changes={"preferred_style": "worked_examples"})
    assert db.get_learner_profile("learner")["preferred_style"] == "bullet_points"
    approve(tutor, "correction")
    record = next(r for r in db.get_memory_records("learner") if r["key"] == "preferred_style")
    assert record["revision"] == 2
    result = ask(tutor, thread="after-correction")
    assert result["response"].startswith("SIMULATION: Worked example:")


def test_rejection_preserves_all_records(tutor):
    seed(tutor)
    before = db.get_memory_records("learner")
    ask(tutor, thread="reject", changes={"level": "advanced"})
    result = approve(tutor, "reject", False)
    assert result["memory_status"] == "rejected"
    assert "commit_memory" not in result["steps"]
    assert db.get_memory_records("learner") == before


@pytest.mark.parametrize("value", ["no", "False", 0, 1, None, {}])
def test_approval_rejects_non_boolean_values(tutor, value):
    ask(tutor)
    with pytest.raises(ValueError, match="boolean"):
        approve(tutor, decision=value)
    assert db.get_memory_records("learner") == []


def test_irrelevant_or_sensitive_memory_is_not_retained(tutor):
    for changes in ({"password": "secret"}, {"preferred_style": "my private information"}):
        with pytest.raises(ValueError, match="Unsupported"):
            ask(tutor, thread=str(changes), changes=changes)
    assert db.get_memory_records("learner") == []


def test_other_learner_does_not_receive_saved_records(tutor):
    seed(tutor)
    db.get_or_create_student("other", "Other Simulated Learner")
    result = tutor.invoke(request_state("other", "Explain Python loops"), cfg("other-thread"))
    assert result["retrieved_memories"] == []
    assert result["profile"]["preferred_style"] == "simple"


def test_fresh_workflow_recovers_approved_memory(tutor):
    seed(tutor)
    from graph.workflow import build_workflow
    result = ask(build_workflow(), thread="fresh-workflow")
    assert len(result["retrieved_memories"]) == 2


def test_new_thread_does_not_inherit_pending_quiz_or_request(tutor):
    quiz = ask(tutor, message="Quiz me on loops")
    assert quiz["active_quiz"]["questions"]
    result = ask(tutor, thread="empty-new-thread")
    assert not result.get("active_quiz")
    assert result["chat_history"] == ""


def test_off_topic_request_routes_without_memory_write(tutor):
    result = ask(tutor, message="Explain astronomy")
    assert "outside" in result["response"]
    assert not result.get("__interrupt__")
    assert db.get_memory_records("learner") == []


def test_quiz_progress_written_only_after_approval(tutor):
    quiz = ask(tutor, message="Quiz me on loops")["quiz_data"]
    submission = {"topic": quiz["topic"], "questions": quiz["questions"],
                  "answers": [question["answer"] for question in quiz["questions"]]}
    result = ask(tutor, message="Evaluate my practice quiz", submission=submission)
    assert result["quiz_result"]["score"] == 3
    assert not db.get_learner_profile("learner")["recent_quiz_attempts"]
    approve(tutor, decision=False)
    assert not db.get_learner_profile("learner")["recent_quiz_attempts"]
    quiz = ask(tutor, message="Quiz me on loops")["quiz_data"]
    submission["questions"] = quiz["questions"]
    ask(tutor, submission=submission)
    approve(tutor)
    assert db.get_learner_profile("learner")["recent_quiz_attempts"][0]["score"] == 3


def test_forged_quiz_from_another_thread_is_refused(tutor):
    quiz = ask(tutor, message="Quiz me on loops")["quiz_data"]
    with pytest.raises(ValueError, match="does not belong"):
        ask(tutor, thread="another", submission={"topic": quiz["topic"], "questions": quiz["questions"],
                                                 "answers": ["A. for"] * 3})


def test_quiz_grading_compares_whole_option_not_first_15_characters(tutor):
    from agents.feedback_agent import evaluate_quiz_results
    a, b = "A. identical prefix WRONG", "A. identical prefix RIGHT"
    result = evaluate_quiz_results("learner", "loops", [{"question": "Q", "answer": b}], [a])
    assert result["score"] == 0


def test_invalid_model_quiz_output_is_not_offered(tutor, monkeypatch):
    from agents import concept_quiz_agent as agent
    client = SimulatedGroq()
    monkeypatch.setattr(client, "create", lambda **kwargs: SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps({"questions": []})))])
    )
    monkeypatch.setattr(agent, "get_client", lambda: client)
    result = ask(tutor, message="Quiz me on loops")
    assert not result["quiz_data"]["questions"]
    assert "invalid quiz" in result["response"]
    assert not result.get("__interrupt__")


def test_missing_source_does_not_invent_notes(tutor, monkeypatch):
    import graph.workflow as workflow
    monkeypatch.setattr(workflow, "retrieve", lambda query: [])
    result = ask(tutor)
    assert "No permitted course notes" in result["response"]
    assert not result.get("__interrupt__")


def test_database_commit_is_atomic_on_invalid_quiz(tutor):
    with pytest.raises(ValueError):
        db.commit_approved_memory("learner", "a", {"last_topic": "loops"}, True,
                                  {"topic": "loops", "score": 5, "total": 3})
    assert db.get_memory_records("learner") == []


def test_provider_failure_does_not_pass_safety_or_write_memory(tutor, monkeypatch):
    from safety import guard
    def fail():
        raise RuntimeError("simulated provider unavailable")
    monkeypatch.setattr(guard, "get_client", fail)
    result = ask(tutor)
    assert result["safe"] is False
    assert "unavailable" in result["response"]
    assert db.get_memory_records("learner") == []


def test_unknown_safety_output_does_not_pass_validation(tutor, monkeypatch):
    from safety import guard
    client = SimulatedGroq()
    monkeypatch.setattr(client, "create", lambda **kwargs: SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="MAYBE"))]))
    monkeypatch.setattr(guard, "get_client", lambda: client)
    result = ask(tutor)
    assert result["safe"] is False
    assert not result.get("__interrupt__")

"""One logical tutor with explicit tools, thread checkpoints, and approved memory."""
import os
from typing import TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import StateGraph, END
from langgraph.types import interrupt

from agents.coordinator import classify_intent, resolve_topic_with_groq
from agents.concept_quiz_agent import explain_concept, generate_quiz, solve_problem
from agents.feedback_agent import evaluate_quiz_results, generate_progress_report
from agents.llm import get_client
from course_map import COURSE_TOPICS, get_off_topic_redirect_message, get_course_summary
from memory.long_term_db import (
    get_learner_profile, get_memory_records, validate_memory_changes, commit_approved_memory,
)
from rag.local_retriever import retrieve
from safety.guard import is_safe


class AgentState(TypedDict, total=False):
    student_id: str
    message: str
    intent: str
    response: str
    quiz_data: dict | None
    quiz_submission: dict | None
    active_quiz: dict | None
    quiz_result: dict | None
    memory_changes: dict
    profile: dict
    retrieved_memories: list[dict]
    chat_history: str
    safe: bool
    safety_message: str
    resolved_topic: str
    source_chunks: list[str]
    proposal: dict
    approved: bool | None
    memory_status: str
    steps: list[str]


def step(state, name):
    return {"steps": state.get("steps", []) + [name]}


def start_node(state):
    # Reset request-local outputs when continuing an existing conversation thread.
    return {"steps": ["start"], "response": "", "quiz_data": None, "quiz_result": None,
            "proposal": {}, "approved": None, "memory_status": "no_change", "source_chunks": [],
            "resolved_topic": "", "intent": ""}


def load_memory_node(state):
    return {**step(state, "load_memory"), "profile": get_learner_profile(state["student_id"]),
            "retrieved_memories": get_memory_records(state["student_id"])}


def safety_node(state):
    # Structured preference controls accept only fixed learning-related values.
    if state.get("memory_changes"):
        validate_memory_changes(state["memory_changes"])
        safe, message = True, ""
    elif state.get("quiz_submission"):
        safe, message = True, ""
    else:
        safe, message = is_safe(state["message"])
    return {**step(state, "safety"), "safe": safe, "safety_message": message}


def coordinator_node(state):
    if state.get("memory_changes"):
        return {**step(state, "coordinator"), "intent": "PREFERENCE"}
    if state.get("quiz_submission"):
        return {**step(state, "coordinator"), "intent": "QUIZ_RESULT"}
    intent = classify_intent(state["message"], state.get("chat_history", ""))
    topic = ""
    if intent in {"EXPLAIN", "QUIZ", "SOLVE"}:
        topic = resolve_topic_with_groq(state["message"], state.get("chat_history", ""),
                                        state["profile"].get("last_topic") or "")
        if topic == "unknown":
            topic = state["profile"].get("last_topic") or ""
        if topic not in COURSE_TOPICS:
            topic = "off_topic"
    return {**step(state, "coordinator"), "intent": intent, "resolved_topic": topic}


def route_by_intent(state):
    if state["resolved_topic"] == "off_topic":
        return "off_topic_response"
    return {"PREFERENCE": "propose_memory", "QUIZ_RESULT": "quiz_result", "EXPLAIN": "retrieve",
            "QUIZ": "retrieve", "SOLVE": "solve", "FEEDBACK": "memory",
            "MEMORY": "memory"}.get(state["intent"], "general")


def retrieval_node(state):
    chunks = retrieve(state["resolved_topic"])
    return {**step(state, "retrieve_course_notes"), "source_chunks": chunks}


def tutor_node(state):
    chunks = state["source_chunks"]
    if not chunks:
        return {**step(state, "tutor"), "response": "No permitted course notes were found. Please choose another topic."}
    if state["intent"] == "QUIZ":
        quiz = generate_quiz(state["resolved_topic"], state["profile"], context_chunks=chunks)
        response = (f"Practice quiz on {state['resolved_topic']} is ready."
                    if quiz.get("questions") else "The model returned an invalid quiz. Please try again.")
        return {**step(state, "tutor"), "response": response, "quiz_data": quiz, "active_quiz": quiz}
    response = explain_concept(state["message"], state["profile"], state.get("chat_history", ""),
                               context_chunks=chunks)
    return {**step(state, "tutor"), "response": response}


def quiz_result_node(state):
    submission = state["quiz_submission"]
    active = state.get("active_quiz") or {}
    if (submission.get("questions") != active.get("questions") or
            submission.get("topic") != active.get("topic")):
        raise ValueError("The quiz does not belong to this thread.")
    if submission["topic"] not in COURSE_TOPICS:
        raise ValueError("Unsupported quiz topic.")
    result = evaluate_quiz_results(state["student_id"], submission["topic"],
                                   submission["questions"], submission["answers"])
    feedback = "\n\n".join(item["feedback"] for item in result["feedback_items"])
    return {**step(state, "evaluate_quiz"), "quiz_result": result, "active_quiz": None,
            "response": f"Quiz result: {result['score']}/{result['total']} ({result['percentage']}%).\n\n{feedback}"}


def solve_node(state):
    return {**step(state, "solve"), "response": solve_problem(state["message"], state["profile"],
                                                              state.get("chat_history", ""))}


def memory_node(state):
    summary = get_course_summary(state["profile"].get("completed_topics", []),
                                 state["profile"].get("weak_topics", []))
    return {**step(state, "memory_report"), "response":
            f"Course completion: {summary['completion_percent']}%.\n\n" + generate_progress_report(state["student_id"])}


def general_node(state):
    result = get_client().chat.completions.create(
        model=os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile"),
        messages=[{"role": "system", "content": "You are EduAgent, a Python Fundamentals tutor. Keep responses brief."},
                  {"role": "user", "content": state["message"]}], max_tokens=300,
    )
    return {**step(state, "general"), "response": result.choices[0].message.content.strip()}


def propose_memory_node(state):
    changes = state.get("memory_changes") or {}
    quiz_result = state.get("quiz_result")
    if not changes and (state["intent"] == "EXPLAIN" or quiz_result):
        topic = quiz_result["topic"] if quiz_result else state["resolved_topic"]
        if state["source_chunks"] or quiz_result:
            changes = {"last_topic": topic}
    # Do not ask to save failed results or unchanged preferences. Quiz attempts are new records.
    changes = {key: value for key, value in changes.items()
               if state["profile"].get(key) != value or quiz_result or
               key not in {r["key"] for r in state["retrieved_memories"]}}
    proposal = {}
    if changes:
        validate_memory_changes(changes)
        proposal = {"changes": changes, "previous": {key: state["profile"].get(key) for key in changes},
                    "reason": "Reuse learning preferences or recent course progress in later threads."}
        if quiz_result:
            proposal["quiz_result"] = {key: quiz_result[key] for key in ("topic", "score", "total")}
    return {**step(state, "propose_memory"), "proposal": proposal,
            "response": state["response"] or "Review the proposed learning preferences."}


def approval_node(state):
    decision = interrupt({"action": "Save or correct reusable learner memory", **state["proposal"]})
    if (not isinstance(decision, dict) or set(decision) != {"approved"} or
            type(decision["approved"]) is not bool):
        raise ValueError("Approval must contain the boolean True or False in 'approved'.")
    return {**step(state, "human_approval"), "approved": decision["approved"]}


def commit_node(state, config):
    proposal = state["proposal"]
    commit_approved_memory(state["student_id"], config["configurable"]["thread_id"],
                           proposal["changes"], state["approved"], proposal.get("quiz_result"))
    return {**step(state, "commit_memory"), "memory_status": "saved"}


def reject_node(state):
    return {**step(state, "reject_memory"), "memory_status": "rejected"}


def build_workflow():
    workflow = StateGraph(AgentState)
    nodes = {"start": start_node, "load_memory": load_memory_node, "safety": safety_node,
             "coordinator": coordinator_node, "retrieve": retrieval_node, "tutor": tutor_node,
             "quiz_result": quiz_result_node, "solve": solve_node, "memory": memory_node,
             "general": general_node, "propose_memory": propose_memory_node, "approval": approval_node,
             "commit": commit_node, "reject": reject_node,
             "safety_response": lambda state: {"response": state["safety_message"]},
             "off_topic_response": lambda state: {"response": get_off_topic_redirect_message()}}
    for name, function in nodes.items():
        workflow.add_node(name, function)
    workflow.set_entry_point("start")
    workflow.add_edge("start", "load_memory")
    workflow.add_edge("load_memory", "safety")
    workflow.add_conditional_edges("safety", lambda state: "coordinator" if state["safe"] else "safety_response",
                                   {name: name for name in ("coordinator", "safety_response")})
    routes = ("off_topic_response", "propose_memory", "quiz_result", "retrieve", "solve", "memory", "general")
    workflow.add_conditional_edges("coordinator", route_by_intent, {name: name for name in routes})
    workflow.add_edge("retrieve", "tutor")
    for name in ("tutor", "quiz_result"):
        workflow.add_edge(name, "propose_memory")
    workflow.add_conditional_edges("propose_memory", lambda state: "approval" if state["proposal"] else END,
                                   {"approval": "approval", END: END})
    workflow.add_conditional_edges("approval", lambda state: "commit" if state["approved"] is True else "reject",
                                   {"commit": "commit", "reject": "reject"})
    for name in ("commit", "reject", "solve", "memory", "general", "safety_response", "off_topic_response"):
        workflow.add_edge(name, END)
    return workflow.compile(checkpointer=InMemorySaver())


def request_state(student_id, message, chat_history="", memory_changes=None, quiz_submission=None):
    return {"student_id": student_id, "message": message, "chat_history": chat_history,
            "memory_changes": memory_changes or {}, "quiz_submission": quiz_submission}

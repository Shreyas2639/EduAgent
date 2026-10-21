"""Streamlit interface for the Project 1 tutor and its approval checkpoint."""
from uuid import uuid4

import streamlit as st
from langgraph.types import Command

from graph.workflow import build_workflow, request_state
from memory.short_term import ShortTermMemory
from memory.long_term_db import init_db, get_or_create_student, get_learner_profile, get_memory_records

st.set_page_config(page_title="EduAgent — AI Tutor", page_icon="🎓", layout="wide")
init_db()
for key, default in {"messages": [], "student_id": None, "thread_id": None,
                     "current_quiz": None, "quiz_id": None, "pending_approval": None, "last_trace": []}.items():
    if key not in st.session_state:
        st.session_state[key] = default
if "memory" not in st.session_state:
    st.session_state.memory = ShortTermMemory()
if "workflow" not in st.session_state:
    st.session_state.workflow = build_workflow()


def config():
    return {"configurable": {"thread_id": st.session_state.thread_id}}


def add_message(role, text):
    st.session_state.messages.append({"role": role, "content": text})
    st.session_state.memory.add_message(role, text)


def new_thread(student_id):
    st.session_state.student_id = student_id
    st.session_state.thread_id = str(uuid4())
    st.session_state.messages = []
    st.session_state.memory.clear()
    st.session_state.current_quiz = None
    st.session_state.quiz_id = None
    st.session_state.pending_approval = None
    st.session_state.last_trace = []
    for key in ("pending_message", "pending_preferences"):
        st.session_state.pop(key, None)


def run_request(message, changes=None, submission=None):
    history = st.session_state.memory.get_context_string()
    add_message("user", message)
    try:
        result = st.session_state.workflow.invoke(
            request_state(st.session_state.student_id, message, history, changes, submission), config())
    except Exception:
        # Pending state can still be rejected if a later memory commit failed.
        add_message("assistant", "This request could not finish. Check your API configuration or try a new thread.")
        return
    add_message("assistant", result["response"])
    st.session_state.last_trace = result.get("steps", [])
    if (result.get("quiz_data") or {}).get("questions"):
        st.session_state.current_quiz = result["quiz_data"]
        st.session_state.quiz_id = str(uuid4())
    if submission:
        st.session_state.current_quiz = None
    st.session_state.quiz_id = None
    st.session_state.pending_approval = (result["__interrupt__"][0].value
                                         if result.get("__interrupt__") else None)


with st.sidebar:
    st.title("🎓 EduAgent")
    st.caption("Python Fundamentals tutor · Project 1")
    student_name = st.text_input("Demo learner name", placeholder="Use a simulated learner")
    if st.button("Start session", type="primary") and student_name.strip():
        student_id = student_name.strip().lower().replace(" ", "_")
        get_or_create_student(student_id, student_name.strip())
        new_thread(student_id)
        st.rerun()
    if st.session_state.student_id:
        if st.button("New thread — keep approved memory"):
            new_thread(st.session_state.student_id)
            st.rerun()
        st.caption(f"Thread: {st.session_state.thread_id}")
        profile = get_learner_profile(st.session_state.student_id)
        st.write("Level:", profile["level"])
        st.write("Format:", profile["preferred_style"])
        st.write("Last topic:", profile.get("last_topic") or "None")
        with st.expander("Approved memory records", expanded=True):
            st.json(get_memory_records(st.session_state.student_id))
        with st.form("learning_preferences"):
            st.write("Learning preferences / corrections")
            styles = ["simple", "bullet_points", "worked_examples"]
            levels = ["beginner", "intermediate", "advanced"]
            style = st.selectbox("Preferred format", styles, index=styles.index(profile["preferred_style"]))
            level = st.selectbox("Level", levels, index=levels.index(profile["level"]))
            if st.form_submit_button("Review memory changes", disabled=bool(st.session_state.pending_approval)):
                st.session_state.pending_preferences = {"preferred_style": style, "level": level}
                st.session_state.pending_message = "Update my learning preferences."
        for prompt in ("Explain Python loops", "Quiz me on loops", "Show my progress"):
            if st.button(prompt, disabled=bool(st.session_state.pending_approval)):
                st.session_state.pending_message = prompt
    st.caption("SQLite memory stays local. Prompts, relevant preferences and notes are sent to Groq. "
               "Use authorized sample data. Learner names are simulated identities, not authentication.")

st.title("🎓 EduAgent — Personalized AI Tutor")
if not st.session_state.student_id:
    st.info("Enter a simulated learner name and start a session.")
    st.stop()

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if st.session_state.pending_approval:
    st.subheader("Save this for later interactions?")
    st.write("Review the proposed changes. Rejecting keeps the current answer and leaves reusable memory unchanged.")
    st.json(st.session_state.pending_approval)
    yes, no = st.columns(2)
    decision = None
    if yes.button("Approve memory update", type="primary"):
        decision = True
    if no.button("Reject memory update"):
        decision = False
    if decision is not None:
        try:
            result = st.session_state.workflow.invoke(Command(resume={"approved": decision}), config())
        except Exception:
            st.error("The decision could not finish. Try again or start a new thread.")
        else:
            st.session_state.pending_approval = None
            st.session_state.last_trace = result["steps"]
            add_message("assistant", "Memory saved." if result["memory_status"] == "saved"
                        else "Memory update rejected. No learning record was changed.")
            st.rerun()
    st.stop()

quiz = st.session_state.current_quiz
if quiz and quiz.get("questions"):
    with st.form("quiz_form"):
        answers = [st.radio(question["question"], question["options"], index=None,
                            key=f"{st.session_state.quiz_id}-q-{index}")
                   for index, question in enumerate(quiz["questions"])]
        if st.form_submit_button("Evaluate answers"):
            if any(answer is None for answer in answers):
                st.warning("Answer every question first.")
            else:
                run_request("Evaluate my practice quiz.", submission={"topic": quiz["topic"],
                            "questions": quiz["questions"], "answers": answers})
                st.rerun()

with st.expander("Last workflow steps"):
    st.write(" → ".join(st.session_state.last_trace))
pending = st.session_state.pop("pending_message", None)
user_input = st.chat_input("Ask for an explanation, practice quiz, or progress report")
message = pending or user_input
if message:
    changes = st.session_state.pop("pending_preferences", None)
    with st.spinner("Working..."):
        run_request(message, changes=changes)
    st.rerun()

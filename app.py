import streamlit as st
import os
from dotenv import load_dotenv
from graph.workflow import build_workflow
from memory.short_term import ShortTermMemory
from memory.long_term_db import init_db, get_or_create_student, get_learner_profile, save_session
from agents.feedback_agent import evaluate_quiz_results

load_dotenv()
init_db()

st.set_page_config(page_title="EduAgent — AI Tutor", page_icon="🎓", layout="wide")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "memory" not in st.session_state:
    st.session_state.memory = ShortTermMemory(max_messages=10)
if "workflow" not in st.session_state:
    st.session_state.workflow = build_workflow()
if "student_id" not in st.session_state:
    st.session_state.student_id = None
if "quiz_active" not in st.session_state:
    st.session_state.quiz_active = False
if "current_quiz" not in st.session_state:
    st.session_state.current_quiz = None

# SIDEBAR
with st.sidebar:
    st.title("🎓 EduAgent")
    st.caption("Your Personalized AI Tutor")
    st.divider()

    st.subheader("👤 Student Setup")
    student_name = st.text_input("Your Name", placeholder="Enter your name")

    if st.button("Start Session", type="primary", use_container_width=True):
        if student_name:
            student_id = student_name.lower().replace(" ", "_")
            get_or_create_student(student_id, student_name)
            st.session_state.student_id = student_id
            st.session_state.messages = []
            st.session_state.memory.clear()
            st.success(f"Welcome, {student_name}!")
            st.rerun()

    st.divider()

    if st.session_state.student_id:
        profile = get_learner_profile(st.session_state.student_id)

        st.subheader("📊 Your Profile")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Level", profile.get("level", "Beginner").title())
        with col2:
            attempts = profile.get("recent_quiz_attempts", [])
            avg_score = 0
            if attempts:
                scores = [a["score"]/a["total"]*100 for a in attempts if a.get("total")]
                avg_score = round(sum(scores)/len(scores)) if scores else 0
            st.metric("Avg Score", f"{avg_score}%")

        if profile.get("weak_topics"):
            st.subheader("⚠️ Needs Work")
            for t in profile["weak_topics"][-3:]:
                st.warning(f"• {t}", icon="📌")

        if profile.get("strong_topics"):
            st.subheader("✅ Strengths")
            for t in profile["strong_topics"][-3:]:
                st.success(f"• {t}", icon="⭐")

        if profile.get("last_topic"):
            st.info(f"📚 Last studied: **{profile['last_topic']}**")

    st.divider()
    st.subheader("💡 Quick Actions")
    for action in ["Explain Python loops", "Explain recursion", "Quiz me on loops",
                   "Explain data structures", "Show my progress"]:
        if st.button(action, use_container_width=True, key=f"qa_{action}"):
            st.session_state["pending_message"] = action

    st.divider()
    st.caption("🔒 Data stored locally | ⚡ Groq · Llama-3.3-70B")

# MAIN AREA
st.title("🎓 EduAgent — Personalized AI Tutor")

if not st.session_state.student_id:
    st.info("👈 Enter your name in the sidebar and click **Start Session** to begin!")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**📖 Explain Concepts**\nRAG-grounded explanations from your notes")
    with c2:
        st.markdown("**📝 Generate Quizzes**\nPersonalized questions based on your weak areas")
    with c3:
        st.markdown("**📊 Track Progress**\nLong-term memory of your learning journey")
else:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Quiz mode
    if st.session_state.quiz_active and st.session_state.current_quiz:
        quiz = st.session_state.current_quiz
        questions = quiz.get("questions", [])
        if questions:
            st.subheader(f"📝 Quiz: {quiz.get('topic', 'General')}")
            with st.form("quiz_form"):
                answers = {}
                for i, q in enumerate(questions):
                    st.markdown(f"**Q{i+1}: {q['question']}**")
                    answers[i] = st.radio(
                        f"Q{i+1}",
                        options=q.get("options", []),
                        key=f"q_{i}",
                        index=None,
                        label_visibility="collapsed"
                    )
                if st.form_submit_button("Submit Answers", type="primary"):
                    unanswered = [str(i + 1) for i in range(len(questions)) if answers[i] is None]

                    if unanswered:
                        st.warning(f"Please answer all questions before submitting. Missing: {', '.join(unanswered)}")
                    else:
                        student_answers = [answers[i] for i in range(len(questions))]
                        results = evaluate_quiz_results(
                            st.session_state.student_id,
                            quiz.get("topic", "general"),
                            questions,
                            student_answers
                        )
                        score_pct = results["percentage"]
                        emoji = "🎉" if score_pct >= 70 else "💪"
                        result_msg = f"{emoji} **Quiz Results: {results['score']}/{results['total']} ({score_pct}%)**\n\n"
                        for fb in results["feedback_items"]:
                            icon = "✅" if fb["correct"] else "❌"
                            result_msg += f"{icon} {fb['feedback']}\n\n"

                        st.session_state.messages.append({"role": "assistant", "content": result_msg})
                        st.session_state.memory.add_message("assistant", result_msg)
                        st.session_state.quiz_active = False
                        st.session_state.current_quiz = None
                        st.rerun()

    pending = st.session_state.pop("pending_message", None)
    user_input = pending or st.chat_input("Ask me anything — explain a concept, request a quiz, or check your progress...")

    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        st.session_state.memory.add_message("user", user_input)
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                state = {
                    "student_id": st.session_state.student_id,
                    "message": user_input,
                    "intent": "",
                    "response": "",
                    "quiz_data": None,
                    "profile": get_learner_profile(st.session_state.student_id),
                    "chat_history": st.session_state.memory.get_context_string(),
                    "safe": True,
                    "safety_message": ""
                }
                result = st.session_state.workflow.invoke(state)
                response = result.get("response", "I encountered an issue. Please try again.")
                quiz_data = result.get("quiz_data")
                if quiz_data and quiz_data.get("questions"):
                    st.session_state.quiz_active = True
                    st.session_state.current_quiz = quiz_data
                    save_session(st.session_state.student_id, quiz_data.get("topic", "quiz"),
                                 f"Quiz generated on {quiz_data.get('topic')}")
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
                st.session_state.memory.add_message("assistant", response)
                st.rerun()

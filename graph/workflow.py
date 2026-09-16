from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END
from agents.coordinator import classify_intent, resolve_topic_with_groq 
from agents.concept_quiz_agent import explain_concept, generate_quiz, solve_problem, extract_topic_from_message
from agents.feedback_agent import generate_progress_report
from memory.long_term_db import get_learner_profile
from safety.guard import is_safe
from course_map import is_course_topic, get_off_topic_redirect_message, get_course_summary

class AgentState(TypedDict):
    student_id: str
    message: str
    intent: str
    response: str
    quiz_data: Optional[dict]
    profile: dict
    chat_history: str
    safe: bool
    safety_message: str
    off_topic: bool
    resolved_topic: str

def off_topic_response_node(state: AgentState) -> AgentState:
    print("[NODE] off_topic_response")
    return {**state, "response": get_off_topic_redirect_message()}

def safety_node(state: AgentState) -> AgentState:
    safe, msg = is_safe(state["message"])
    print(f"[SAFETY] message={state['message']!r} -> safe={safe}")
    return {**state, "safe": safe, "safety_message": msg}

def coordinator_node(state: AgentState) -> AgentState:
    if not state.get("safe", True):
        print("[COORDINATOR] skipped because request is unsafe")
        return state

    intent = classify_intent(state["message"], state.get("chat_history", ""))
    profile = get_learner_profile(state["student_id"])

    resolved_topic = ""
    off_topic = False

    if intent in ["EXPLAIN", "QUIZ", "SOLVE"]:
        resolved_topic = resolve_topic_with_groq(
            state["message"],
            state.get("chat_history", ""),
            profile.get("last_topic", "")
        )

        if resolved_topic == "unknown":
            resolved_topic = profile.get("last_topic", "")

        # Strict off-topic blocking only for QUIZ and SOLVE
        if intent in ["QUIZ", "SOLVE"] and resolved_topic == "off_topic":
            off_topic = True

    print(
        f"[COORDINATOR] intent={intent} | "
        f"last_topic={profile.get('last_topic')} | "
        f"resolved_topic={resolved_topic} | "
        f"off_topic={off_topic}"
    )

    return {
        **state,
        "intent": intent,
        "profile": profile,
        "off_topic": off_topic,
        "resolved_topic": resolved_topic
    }

def concept_node(state: AgentState) -> AgentState:
    print("[NODE] concept")

    message_for_explanation = state["message"]

    resolved_topic = state.get("resolved_topic")

    if resolved_topic and resolved_topic not in ["off_topic", "unknown"]:
        message_for_explanation = f"Explain {resolved_topic}"

    response = explain_concept(
        message_for_explanation,
        state["profile"],
        state["chat_history"],
        state["student_id"]
    )

    return {**state, "response": response}

def quiz_node(state: AgentState) -> AgentState:
    print("[NODE] quiz")
    profile = state["profile"]

    
    if state.get("off_topic", False):
        print("[QUIZ] off-topic request detected -> redirecting to last valid course topic")
        topic = profile.get("last_topic", "python loops")

        quiz_data = generate_quiz(topic, profile)

        if quiz_data.get("questions"):
            q_text = (
                "That topic is outside the current Python Fundamentals course, "
                f"so let's continue with a course topic instead.\n\n"
                f"Here's your quiz on **{topic}**!\n\n"
            )
            for i, q in enumerate(quiz_data["questions"]):
                q_text += f"**Q{i+1}:** {q['question']}\n"
                for opt in q.get("options", []):
                    q_text += f"  {opt}\n"
                q_text += "\n"
            response = q_text
        else:
            response = (
                f"That topic is outside the course. I also couldn't generate a quiz right now. "
                f"Try: 'Quiz me on {profile.get('last_topic', 'Python loops')}'"
            )

        quiz_data["topic"] = topic
        return {**state, "response": response, "quiz_data": quiz_data}

    # Normal in-course quiz flow
    topic = state.get("resolved_topic") or profile.get("last_topic", "python loops")

    print(f"[QUIZ] resolved_topic={topic}")
    quiz_data = generate_quiz(topic, profile)

    if quiz_data.get("questions"):
        q_text = f"Here's your quiz on **{topic}**!\n\n"
        for i, q in enumerate(quiz_data["questions"]):
            q_text += f"**Q{i+1}:** {q['question']}\n"
            for opt in q.get("options", []):
                q_text += f"  {opt}\n"
            q_text += "\n"
        response = q_text
    else:
        response = f"I couldn't generate a quiz right now. Try: 'Quiz me on {profile.get('last_topic', 'Python loops')}'"

    quiz_data["topic"] = topic
    return {**state, "response": response, "quiz_data": quiz_data}

def solve_node(state: AgentState) -> AgentState:
    print("[NODE] solve")
    response = solve_problem(state["message"], state["profile"], state["chat_history"])
    return {**state, "response": response}


def memory_node(state: AgentState) -> AgentState:
    print("[NODE] memory")

    profile = state["profile"]

    completed = profile.get("completed_topics", [])
    weak = profile.get("weak_topics", [])

    
    summary = get_course_summary(completed, weak)

    structured_part = f"""
📘 Course: {summary['course_name']}

📊 Completion: {summary['completion_percent']}%

✅ Completed Topics:
{', '.join(summary['completed_topics']) if summary['completed_topics'] else "None yet"}

⚠️ Needs Work:
{', '.join(summary['weak_topics']) if summary['weak_topics'] else "None"}

📚 Remaining Topics:
{', '.join(summary['remaining_topics'])}

➡️ Recommended Next Topic:
{summary['recommended_next_topic']}
"""

    # 🔹 LLM-generated personalized feedback
    llm_feedback = generate_progress_report(state["student_id"])

    response = structured_part + "\n\n💡 Feedback:\n" + llm_feedback

    return {**state, "response": response}

def general_node(state: AgentState) -> AgentState:
    print("[NODE] general")
    import os
    from groq import Groq
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You are EduAgent, a friendly educational tutor. Keep responses brief."},
            {"role": "user", "content": state["message"]}
        ],
        max_tokens=300
    )
    return {**state, "response": response.choices[0].message.content.strip()}

def safety_response_node(state: AgentState) -> AgentState:
    print("[NODE] safety_response")
    return {**state, "response": state["safety_message"]}

def route_by_intent(state: AgentState) -> str:
    if not state.get("safe", True):
        print("[ROUTE] -> safety_response")
        return "safety_response"

    if state.get("off_topic", False):
        print("[ROUTE] -> off_topic_response")
        return "off_topic_response"

    intent = state.get("intent", "GENERAL")
    routes = {
        "EXPLAIN": "concept",
        "QUIZ": "quiz",
        "SOLVE": "solve",
        "FEEDBACK": "memory",
        "MEMORY": "memory",
        "GENERAL": "general"
    }
    selected = routes.get(intent, "general")
    print(f"[ROUTE] intent={intent} -> {selected}")
    return selected

def build_workflow():
    workflow = StateGraph(AgentState)

    workflow.add_node("safety", safety_node)
    workflow.add_node("coordinator", coordinator_node)
    workflow.add_node("concept", concept_node)
    workflow.add_node("quiz", quiz_node)
    workflow.add_node("solve", solve_node)
    workflow.add_node("memory", memory_node)
    workflow.add_node("general", general_node)
    workflow.add_node("safety_response", safety_response_node)
    workflow.add_node("off_topic_response", off_topic_response_node)

    workflow.set_entry_point("safety")
    workflow.add_conditional_edges(
        "safety",
        lambda state: "safe" if state["safe"] else "unsafe",
        {
            "safe": "coordinator",
            "unsafe": "safety_response"
        }
    )

    workflow.add_conditional_edges(
    "coordinator",
    route_by_intent,
    {
        "concept": "concept",
        "quiz": "quiz",
        "solve": "solve",
        "memory": "memory",
        "general": "general",
        "safety_response": "safety_response",
        "off_topic_response": "off_topic_response"
    }
)

    for node in ["concept", "quiz", "solve", "memory", "general", "safety_response", "off_topic_response"]:
        workflow.add_edge(node, END)

    return workflow.compile()
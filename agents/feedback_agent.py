import os
import re
from groq import Groq
from course_map import COURSE_TOPICS
from dotenv import load_dotenv
from memory.long_term_db import (
    get_learner_profile, update_weak_topics,
    update_strong_topics, remove_weak_topic,
    remove_strong_topic, save_quiz_attempt,
    add_completed_topic
)

load_dotenv()
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def clean_topic(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    prefixes = [
        "i would like to have a quiz on ",
        "i would like to have a quiz ",
        "i would like a quiz on ",
        "i would like a quiz ",
        "i would like a ",
        "i would like ",
        "i want to have a quiz on ",
        "i want a quiz on ",
        "i want to ",
        "i want ",
        "can you please ",
        "could you please ",
        "can you ",
        "could you ",
        "please ",
        "would you ",
        "quiz me on ",
        "test me on ",
        "quiz me ",
        "test me ",
        "explain ",
        "teach me ",
        "what is ",
        "help me understand ",
        "tell me about "
    ]
    for p in prefixes:
        if text.startswith(p):
            text = text[len(p):].strip()
            break

    text = re.sub(r"\s+", " ", text).strip()
    return text.strip(" .?!")

def evaluate_answer(student_id: str, topic: str, question: str,
                    student_answer: str, correct_answer: str, explanation: str) -> str:
    topic = clean_topic(topic)
    is_correct = student_answer.strip().lower()[:15] == correct_answer.strip().lower()[:15]

    tone = "positive and encouraging" if is_correct else "constructive and helpful"
    prompt = f"""You are EduAgent providing {tone} feedback.
Question: {question}
Student's Answer: {student_answer}
Correct Answer: {correct_answer}
Explanation: {explanation}
Is Correct: {is_correct}

Give brief feedback (2-3 sentences).
If correct: praise and reinforce the concept.
If wrong: explain what was incorrect, give the right concept, encourage them.

Feedback:"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=150,
        temperature=0.6
    )
    return response.choices[0].message.content.strip()

def generate_progress_report(student_id: str) -> str:
    profile = get_learner_profile(student_id)
    if not profile:
        return "No learning data found yet. Start a session to track your progress!"

    prompt = f"""You are EduAgent creating a personalized progress report.
Student: {profile.get('name', 'Student')}
Level: {profile.get('level', 'beginner')}
Strong Topics: {', '.join(profile.get('strong_topics', [])) or 'None yet'}
Weak Topics: {', '.join(profile.get('weak_topics', [])) or 'None identified yet'}
Last Topic: {profile.get('last_topic', 'N/A')}
Recent Quizzes: {profile.get('recent_quiz_attempts', [])}

Write a friendly progress report (3-4 sentences) that:
1. Highlights strengths
2. Identifies areas to improve
3. Suggests what to study next
4. Explains that course completion is approximate and based on how many topics have been practiced
5. Encourages the student to keep practicing and reassures them progress is gradual

Progress Report:"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=250,
        temperature=0.7
    )
    return response.choices[0].message.content.strip()

def evaluate_quiz_results(student_id: str, topic: str, questions: list,
                          student_answers: list) -> dict:
    topic = clean_topic(topic)
    score = 0
    feedback_items = []
    mistakes = []

    for q, student_ans in zip(questions, student_answers):
        correct = q.get("answer", "")
        is_correct = student_ans.strip()[:15].lower() == correct.strip()[:15].lower()

        if is_correct:
            score += 1
        else:
            mistakes.append(q.get("question", ""))

        fb = evaluate_answer(
            student_id, topic,
            q.get("question", ""),
            student_ans, correct,
            q.get("explanation", "")
        )
        feedback_items.append({
            "question": q.get("question"),
            "correct": is_correct,
            "feedback": fb
        })

    save_quiz_attempt(student_id, topic, score, len(questions), mistakes)

    if questions:
        if score >= len(questions) * 0.7:
            remove_weak_topic(student_id, topic)
            update_strong_topics(student_id, topic)
            add_completed_topic(student_id, topic)
        else:
            remove_strong_topic(student_id, topic)
            update_weak_topics(student_id, topic)

    return {
        "score": score,
        "total": len(questions),
        "percentage": round(score / len(questions) * 100) if questions else 0,
        "feedback_items": feedback_items
    }

def resolve_topic_with_groq(message: str, chat_history: str = "", last_topic: str = "") -> str:
    topics_text = ", ".join(COURSE_TOPICS)

    prompt = f"""You are a topic resolver for a Python tutoring system.

Valid course topics:
{topics_text}

Recent chat:
{chat_history or "No recent chat"}

Last studied topic:
{last_topic or "None"}

Student message:
{message}

Instructions:
1. If the student clearly refers to one valid course topic, return that topic exactly.
2. If the student uses a vague phrase like "this", "this topic", "that", "it", "yes please", or "quiz me on this",
   resolve it to the last studied topic if appropriate.
3. If the request is outside the Python course, return OFF_TOPIC.
4. If the message is not about a course topic, return UNKNOWN.

Reply with only one of:
- one valid course topic
- OFF_TOPIC
- UNKNOWN
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=20,
            temperature=0
        )
        result = (response.choices[0].message.content or "").strip().lower()
        return result
    except Exception as e:
        print(f"Topic resolver error: {e}")
        return "unknown"
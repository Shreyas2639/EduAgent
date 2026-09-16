import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

UNSAFE_KEYWORDS = [
    "cheat", "cheating", "exam answers", "test answers",
    "hack", "bypass", "plagiarize", "plagiarism",
    "harm", "weapon", "illegal", "drug",
    "password", "private data", "credit card",
    "answers", "answer key"
]

ACADEMIC_CHEATING_PHRASES = [
    "give me the answers to",
    "solve my assignment for me without explanation",
    "write my essay",
    "do my homework",
    "answers to the test",
    "answers to the exam",
    "all the answers to my upcoming",
    "give me all the answers",
    "help me cheat",
    "upcoming exam",
    "upcoming test",
    "my exam",
    "my test",
    "my next quiz",
    "answers for my next quiz",
    "get the answers for my next quiz",
    "could i get the answers",
    "can i get the answers",
    "give me the answers",
    "tell me what to write in the test",
    "do my assignment",
    "solve my assignment for me",
    "write my assignment",
    "answer key"
]

def llm_safety_check(message: str) -> tuple:
    prompt = f"""
You are a safety classifier for an educational AI tutor.

Classify the student's request as either SAFE or UNSAFE.

UNSAFE means:
- asking for direct answers to quizzes, exams, tests, homework, or assignments
- asking to cheat
- asking to complete academic work dishonestly
- asking for harmful or illegal help

SAFE means:
- asking for explanations
- asking for tutoring
- asking for practice questions
- asking for study help
- asking for step-by-step learning support

Student message:
{message}

Reply with exactly one word:
SAFE
or
UNSAFE
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=5,
            temperature=0
        )
        label = response.choices[0].message.content.strip().upper()

        if label == "UNSAFE":
            return False, (
                "I can't help with direct answers for quizzes, exams, or assignments. "
                "I can help you study with explanations, practice questions, and worked examples."
            )

        return True, ""
    except Exception as e:
        print(f"LLM safety check error: {e}")
        return True, ""

def is_safe(message: str) -> tuple:
    message_lower = message.lower().strip()

    # Fast rule-based check for direct cheating attempts
    for phrase in ACADEMIC_CHEATING_PHRASES:
        if phrase in message_lower:
            return False, (
                "I can't help with quiz, exam, or assignment cheating. "
                "I can help you study by explaining the topic, giving practice questions, "
                "or walking through similar examples."
            )

    assessment_words = ["quiz", "exam", "test", "assignment", "homework", "assessment"]
    cheating_words = [
        "answer", "answers", "answer key", "cheat",
        "solve for me", "do for me", "write for me",
        "complete for me"
    ]

    if any(a in message_lower for a in assessment_words) and any(c in message_lower for c in cheating_words):
        return False, (
            "I can't provide direct answers for quizzes, exams, or assignments. "
            "I can help you prepare with explanations, practice questions, and step-by-step guidance."
        )

    harmful = ["how to hurt", "how to harm", "how to kill", "how to hack"]
    for h in harmful:
        if h in message_lower:
            return False, "I can't help with that request. I'm an educational tutor focused on learning support."

    # Fallback LLM-based safety check for paraphrased unsafe requests
    return llm_safety_check(message)
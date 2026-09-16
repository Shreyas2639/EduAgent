import os
from groq import Groq
from dotenv import load_dotenv
from course_map import COURSE_TOPICS

load_dotenv()
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

INTENT_PROMPT = """You are an intent classifier for an educational tutor system.

Classify the student's message into EXACTLY ONE of these intents:
- EXPLAIN: student wants to learn or understand a concept
- QUIZ: student wants a quiz, practice questions, or to test themselves
- SOLVE: student wants a math or coding problem solved step by step
- FEEDBACK: student submitted answers for evaluation
- MEMORY: student is asking about past sessions, weak areas, progress history, or what to study next
- GENERAL: general question or greeting

Important rules:
- If the student says "yes", "yes please", "sure", "okay", "go ahead", and the recent chat shows the tutor just offered a quiz, classify as QUIZ.
- If the student asks "what am I weak at", "show my progress", "what should I study next", "how am I doing", classify as MEMORY.
- If the student is asking for exam answers, cheating help, or direct assignment answers, still classify the intent normally; safety will handle refusal later.

Reply with ONLY the intent word.

Recent chat:
{chat_history}

Student message:
{message}

Intent:"""

def classify_intent(message: str, chat_history: str = "") -> str:
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{
                "role": "user",
                "content": INTENT_PROMPT.format(
                    message=message,
                    chat_history=chat_history or "No recent chat."
                )
            }],
            max_tokens=10,
            temperature=0
        )
        intent = response.choices[0].message.content.strip().upper()
        valid_intents = ["EXPLAIN", "QUIZ", "SOLVE", "FEEDBACK", "MEMORY", "GENERAL"]
        return intent if intent in valid_intents else "GENERAL"
    except Exception as e:
        print(f"Intent classification error: {e}")
        return "GENERAL"
    
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
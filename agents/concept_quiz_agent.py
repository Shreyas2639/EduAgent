import os
import json
import re
from groq import Groq
from dotenv import load_dotenv
from rag.retriever import retrieve
from tools.wikipedia_tool import search_wikipedia
from tools.sympy_tool import solve_math
from memory.long_term_db import update_last_topic

load_dotenv()
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

VAGUE_PHRASES = {
    "yes", "yes please", "sure", "okay", "go ahead", "my learning", "that", "this"
}

def clean_topic(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    prefixes = [
        "i would like to have a quiz on ",
        "i would like to have a quiz ",
        "i would like to have a practice quiz on ",
        "i would like to have a quiz ",
        "i would like to have a ",
        "i would like a quiz on ",
        "i would like a quiz ",
        "i would like a ",
        "i would like ",
        "i want to have a quiz on ",
        "i want to have a quiz ",
        "i want a quiz on ",
        "i want a quiz ",
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
        "tell me about ",
        "give me 3 practice questions on ",
        "give me practice questions on ",
        "practice questions on ",
        "practice questions for ",
        "on "
    ]
    for p in prefixes:
        if text.startswith(p):
            text = text[len(p):].strip()
            break

    endings = [
        "to me then give me 3 practice questions",
        "to me then give me practice questions",
        "then give me 3 practice questions",
        "then give me practice questions",
        "give me 3 practice questions",
        "give me practice questions",
        "to me"
    ]
    for e in endings:
        if text.endswith(e):
            text = text[: -len(e)].strip()
            break

    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\b(to me|please|now|today|thanks|thank you)\b$", "", text).strip()
    if text in VAGUE_PHRASES:
        return ""
    return text.strip()

def extract_topic_from_message(message: str) -> str:
    topic = clean_topic(message)
    if topic in VAGUE_PHRASES:
        return ""
    return topic

def explain_concept(message: str, student_profile: dict, chat_history: str, student_id: str = None) -> str:
    context_chunks = retrieve(message, top_k=3)
    rag_context = "\n\n".join(context_chunks)
    wiki_info = ""

    if context_chunks and "No relevant" in context_chunks[0]:
        topic_words = clean_topic(message)
        if topic_words:
            wiki_info = search_wikipedia(topic_words)

    level = student_profile.get("level", "beginner")
    weak_topics = student_profile.get("weak_topics", [])
    weak_note = f"Note: This student struggled with: {', '.join(weak_topics)}. Be extra clear." if weak_topics else ""

    prompt = f"""You are EduAgent, a friendly and patient educational tutor.
Student Level: {level}
{weak_note}

Recent Chat History:
{chat_history}

Course Notes (PRIMARY source):
{rag_context}

Additional Context (Wikipedia):
{wiki_info}

Student's Question: {message}

Instructions:
1. Explain clearly at the {level} level
2. Use course notes as primary source
3. Give 1-2 concrete examples
4. End with "Want me to quiz you on this?" if relevant
5. Keep response under 400 words

Response:"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=700,
        temperature=0.7
    )

    final_response = (response.choices[0].message.content or "").strip()

    if student_id:
        topic = extract_topic_from_message(message)
        INVALID_TOPICS = {"off topic", "off_topic", "unknown", "", None}

        if topic not in INVALID_TOPICS and topic not in VAGUE_PHRASES:
            update_last_topic(student_id, topic)

    return final_response

def generate_quiz(topic: str, student_profile: dict, num_questions: int = 3) -> dict:
    topic = clean_topic(topic)
    level = student_profile.get("level", "beginner")
    weak_topics = student_profile.get("weak_topics", [])
    context_chunks = retrieve(topic, top_k=3)
    related_notes = any(topic.lower() in chunk.lower() for chunk in context_chunks)
    rag_context = "\n\n".join(context_chunks) if related_notes else ""
    context_hint = "Note: Course Notes do not appear to contain the requested topic, so use the requested topic as the primary focus." if not related_notes else ""
    weak_focus = f"Focus extra questions on weak areas: {', '.join(weak_topics)}" if weak_topics else ""

    prompt = f"""You are EduAgent quiz generator.
Topic: {topic}
Student Level: {level}
{weak_focus}

{context_hint}
Course Notes:
{rag_context}

Instructions:
1. Generate exactly {num_questions} multiple choice questions about {topic}.
2. Use Course Notes only if they are clearly about the requested topic.
3. If Course Notes are unrelated or do not mention the topic, ignore them and create questions from the topic itself.
4. Each question must have 4 options labeled A-D, a single correct answer, and a short explanation.
5. Do not generate questions about unrelated concepts such as loops or functions when the topic is classes in Python.

Return ONLY valid JSON array:
[
  {{
    "question": "...",
    "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
    "answer": "A. ...",
    "explanation": "..."
  }}
]"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1000,
        temperature=0.5
    )

    try:
        content = response.choices[0].message.content.strip()
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        questions = json.loads(content)
        return {"questions": questions, "topic": topic}
    except Exception as e:
        return {"questions": [], "topic": topic, "error": str(e), "raw": response.choices[0].message.content.strip()}

def solve_problem(message: str, student_profile: dict, chat_history: str) -> str:
    math_keywords = ["derivative", "integral", "solve", "factor", "simplify", "equation"]
    is_math = any(kw in message.lower() for kw in math_keywords)
    math_result = ""

    if is_math:
        expressions = [w for w in message.split() if any(c.isdigit() or c in '+-*/^()=' for c in w)]
        if expressions:
            math_result = solve_math(" ".join(expressions))

    context_chunks = retrieve(message, top_k=2)
    rag_context = "\n\n".join(context_chunks)

    prompt = f"""You are EduAgent, a step-by-step problem solver.
Student Level: {student_profile.get("level", "beginner")}

Recent Chat:
{chat_history}

Course Notes:
{rag_context}

SymPy Computation (if available):
{math_result}

Student's Problem: {message}

Solve step by step:
1. Identify what is being asked
2. Show each step clearly with explanation
3. Verify the answer
4. Point out common mistakes to avoid

Response:"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=800,
        temperature=0.3
    )
    return response.choices[0].message.content.strip()
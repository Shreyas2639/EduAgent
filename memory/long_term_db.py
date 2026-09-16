import sqlite3
import json
import os
import re
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'database', 'eduagent.db')

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            student_id TEXT PRIMARY KEY,
            name TEXT,
            level TEXT DEFAULT 'beginner',
            preferred_style TEXT DEFAULT 'simple',
            created_at TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS learning_profile (
            student_id TEXT PRIMARY KEY,
            weak_topics TEXT DEFAULT '[]',
            strong_topics TEXT DEFAULT '[]',
            completed_topics TEXT DEFAULT '[]',
            last_topic TEXT,
            last_updated TEXT,
            FOREIGN KEY (student_id) REFERENCES students(student_id)
        )
    ''')

    # Migration for older databases that do not yet have completed_topics
    try:
        cursor.execute("ALTER TABLE learning_profile ADD COLUMN completed_topics TEXT DEFAULT '[]'")
    except sqlite3.OperationalError:
        pass

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS quiz_attempts (
            attempt_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT,
            topic TEXT,
            score INTEGER,
            total INTEGER,
            mistakes TEXT DEFAULT '[]',
            timestamp TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            session_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT,
            topic TEXT,
            summary TEXT,
            timestamp TEXT
        )
    ''')

    conn.commit()
    conn.close()
    _normalize_existing_topics()

def get_or_create_student(student_id: str, name: str = "Student"):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM students WHERE student_id = ?', (student_id,))
    student = cursor.fetchone()

    if not student:
        cursor.execute(
            'INSERT INTO students VALUES (?, ?, ?, ?, ?)',
            (student_id, name, 'beginner', 'simple', datetime.now().isoformat())
        )

        cursor.execute(
            '''
            INSERT INTO learning_profile
            (student_id, weak_topics, strong_topics, completed_topics, last_topic, last_updated)
            VALUES (?, ?, ?, ?, ?, ?)
            ''',
            (student_id, '[]', '[]', '[]', None, datetime.now().isoformat())
        )

        conn.commit()

    conn.close()
    return student_id

def get_learner_profile(student_id: str) -> dict:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM students WHERE student_id = ?', (student_id,))
    student = cursor.fetchone()

    cursor.execute('''
        SELECT weak_topics, strong_topics, completed_topics, last_topic, last_updated
        FROM learning_profile
        WHERE student_id = ?
    ''', (student_id,))
    profile = cursor.fetchone()

    cursor.execute(
        'SELECT topic, score, total FROM quiz_attempts WHERE student_id = ? ORDER BY timestamp DESC LIMIT 5',
        (student_id,)
    )
    recent_attempts = cursor.fetchall()

    conn.close()

    if not student:
        return {}

    return {
        "name": student[1],
        "level": student[2],
        "preferred_style": student[3],
        "weak_topics": json.loads(profile[0]) if profile and profile[0] else [],
        "strong_topics": json.loads(profile[1]) if profile and profile[1] else [],
        "completed_topics": json.loads(profile[2]) if profile and profile[2] else [],
        "last_topic": profile[3] if profile else None,
        "recent_quiz_attempts": [
            {"topic": a[0], "score": a[1], "total": a[2]} for a in recent_attempts
        ]
    }

def add_completed_topic(student_id: str, topic: str):
    topic = normalize_topic(topic)
    if not topic:
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT completed_topics FROM learning_profile WHERE student_id = ?', (student_id,))
    row = cursor.fetchone()

    if row:
        completed = json.loads(row[0]) if row[0] else []
        if topic not in completed:
            completed.append(topic)
            cursor.execute(
                'UPDATE learning_profile SET completed_topics = ?, last_updated = ? WHERE student_id = ?',
                (json.dumps(completed), datetime.now().isoformat(), student_id)
            )

    conn.commit()
    conn.close()

def normalize_topic(text: str) -> str:
    if not text:
        return ""
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    prefixes = [
        "i would like to have a quiz on ",
        "i would like to have a quiz ",
        "i would like to have a practice quiz on ",
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
    return text


def update_weak_topics(student_id: str, topic: str):
    topic = normalize_topic(topic)
    if not topic:
        return
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT weak_topics FROM learning_profile WHERE student_id = ?', (student_id,))
    row = cursor.fetchone()
    if row:
        weak = json.loads(row[0])
        if topic not in weak:
            weak.append(topic)
        cursor.execute(
            'UPDATE learning_profile SET weak_topics = ?, last_updated = ? WHERE student_id = ?',
            (json.dumps(weak), datetime.now().isoformat(), student_id)
        )
    conn.commit()
    conn.close()

def update_strong_topics(student_id: str, topic: str):
    topic = normalize_topic(topic)
    if not topic:
        return
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT strong_topics FROM learning_profile WHERE student_id = ?', (student_id,))
    row = cursor.fetchone()
    if row:
        strong = json.loads(row[0])
        if topic not in strong:
            strong.append(topic)
        cursor.execute(
            'UPDATE learning_profile SET strong_topics = ?, last_updated = ? WHERE student_id = ?',
            (json.dumps(strong), datetime.now().isoformat(), student_id)
        )
    conn.commit()
    conn.close()

def remove_strong_topic(student_id: str, topic: str):
    topic = normalize_topic(topic)
    if not topic:
        return
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT strong_topics FROM learning_profile WHERE student_id = ?', (student_id,))
    row = cursor.fetchone()
    if row:
        strong = json.loads(row[0])
        if topic in strong:
            strong = [t for t in strong if t != topic]
            cursor.execute(
                'UPDATE learning_profile SET strong_topics = ?, last_updated = ? WHERE student_id = ?',
                (json.dumps(strong), datetime.now().isoformat(), student_id)
            )
    conn.commit()
    conn.close()

def save_quiz_attempt(student_id: str, topic: str, score: int, total: int, mistakes: list):
    topic = normalize_topic(topic)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO quiz_attempts (student_id, topic, score, total, mistakes, timestamp) VALUES (?, ?, ?, ?, ?, ?)',
        (student_id, topic, score, total, json.dumps(mistakes), datetime.now().isoformat())
    )
    cursor.execute(
        'UPDATE learning_profile SET last_topic = ?, last_updated = ? WHERE student_id = ?',
        (topic, datetime.now().isoformat(), student_id)
    )
    conn.commit()
    conn.close()

def remove_weak_topic(student_id: str, topic: str):
    topic = normalize_topic(topic)
    if not topic:
        return
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT weak_topics FROM learning_profile WHERE student_id = ?', (student_id,))
    row = cursor.fetchone()
    if row:
        weak = json.loads(row[0])
        if topic in weak:
            weak = [t for t in weak if t != topic]
            cursor.execute(
                'UPDATE learning_profile SET weak_topics = ?, last_updated = ? WHERE student_id = ?',
                (json.dumps(weak), datetime.now().isoformat(), student_id)
            )
    conn.commit()
    conn.close()

def save_session(student_id: str, topic: str, summary: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO sessions (student_id, topic, summary, timestamp) VALUES (?, ?, ?, ?)',
        (student_id, topic, summary, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def _normalize_existing_topics():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT student_id, weak_topics, strong_topics, last_topic FROM learning_profile')
    rows = cursor.fetchall()
    for student_id, weak_json, strong_json, last_topic in rows:
        weak = [t for t in {normalize_topic(t) for t in json.loads(weak_json) if normalize_topic(t)}]
        strong = [t for t in {normalize_topic(t) for t in json.loads(strong_json) if normalize_topic(t)}]
        last_topic_clean = normalize_topic(last_topic)
        cursor.execute(
            'UPDATE learning_profile SET weak_topics = ?, strong_topics = ?, last_topic = ? WHERE student_id = ?',
            (json.dumps(weak), json.dumps(strong), last_topic_clean, student_id)
        )
    conn.commit()
    conn.close()


def update_last_topic(student_id: str, topic: str):
    topic = normalize_topic(topic)
    if not topic:
        return
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE learning_profile SET last_topic = ?, last_updated = ? WHERE student_id = ?',
        (topic, datetime.now().isoformat(), student_id)
    )
    conn.commit()
    conn.close()
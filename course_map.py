"""
Course Structure Definition
Defines the Python Fundamentals course curriculum with prerequisites and learning path
"""

COURSE_NAME = "Python Fundamentals"

COURSE_TOPICS = [
    "variables and data types",
    "operators",
    "conditionals",
    "loops",
    "functions",
    "lists",
    "dictionaries",
    "debugging basics",
    "searching basics",
    "sorting basics",
    "recursion",
    "data structures"
]

# Course structure with prerequisites for guided learning
COURSE_STRUCTURE = [
    {"topic": "variables and data types", "prerequisites": []},
    {"topic": "operators", "prerequisites": ["variables and data types"]},
    {"topic": "conditionals", "prerequisites": ["operators"]},
    {"topic": "loops", "prerequisites": ["conditionals"]},
    {"topic": "functions", "prerequisites": ["conditionals"]},
    {"topic": "lists", "prerequisites": ["loops"]},
    {"topic": "dictionaries", "prerequisites": ["lists"]},
    {"topic": "debugging basics", "prerequisites": ["functions"]},
    {"topic": "searching basics", "prerequisites": ["loops", "lists"]},
    {"topic": "sorting basics", "prerequisites": ["loops", "lists"]},
    {"topic": "recursion", "prerequisites": ["functions"]},
    {"topic": "data structures", "prerequisites": ["lists", "dictionaries"]}
]


def normalize_topic(text: str) -> str:
    """Normalize topic name for matching against course topics"""
    return text.lower().strip()


def is_course_topic(topic: str) -> bool:
    """
    Check if a requested topic belongs to the course curriculum
    
    Args:
        topic: User-requested topic (raw or normalized)
    
    Returns:
        True if topic is in course curriculum, False otherwise
    """
    normalized = normalize_topic(topic)
    course_topics_normalized = [normalize_topic(t) for t in COURSE_TOPICS]
    return normalized in course_topics_normalized


def get_remaining_topics(completed_topics: list) -> list:
    """
    Compute remaining topics given completed ones
    
    Args:
        completed_topics: List of topics already completed by student
    
    Returns:
        List of topics not yet completed
    """
    completed_normalized = [normalize_topic(t) for t in completed_topics]
    remaining = [t for t in COURSE_TOPICS if normalize_topic(t) not in completed_normalized]
    return remaining


def get_course_completion_percent(completed_topics: list) -> int:
    """
    Calculate course completion percentage
    
    Args:
        completed_topics: List of completed topics
    
    Returns:
        Percentage (0-100) of course completed
    """
    if not COURSE_TOPICS:
        return 0
    return round((len(completed_topics) / len(COURSE_TOPICS)) * 100)


def get_recommended_next_topic(completed_topics: list) -> str:
    """
    Get recommended next topic based on prerequisites and completion status
    
    Args:
        completed_topics: List of completed topics
    
    Returns:
        Recommended next topic or None if course complete
    """
    completed_normalized = [normalize_topic(t) for t in completed_topics]
    
    for topic_info in COURSE_STRUCTURE:
        topic = topic_info["topic"]
        prerequisites = topic_info["prerequisites"]
        
        # Check if topic not yet completed
        if normalize_topic(topic) not in completed_normalized:
            # Check if all prerequisites are met
            if all(normalize_topic(p) in completed_normalized for p in prerequisites):
                return topic
    
    return None  # Course complete or no eligible topics


def get_topic_prerequisites(topic: str) -> list:
    """
    Get prerequisites for a given topic
    
    Args:
        topic: Topic name
    
    Returns:
        List of prerequisite topics
    """
    normalized = normalize_topic(topic)
    
    for topic_info in COURSE_STRUCTURE:
        if normalize_topic(topic_info["topic"]) == normalized:
            return topic_info["prerequisites"]
    
    return []


def get_off_topic_redirect_message() -> str:
    """Generate helpful redirect message for off-topic requests"""
    available_topics = ", ".join(COURSE_TOPICS[:5])
    return f"That topic is outside your current {COURSE_NAME} course. I can help with topics like {available_topics}, and more. What would you like to learn?"


def get_course_summary(completed_topics: list, weak_topics: list) -> dict:
    """
    Generate a comprehensive course summary for progress reports
    
    Args:
        completed_topics: List of completed topics
        weak_topics: List of topics needing more practice
    
    Returns:
        Dictionary with course summary information
    """
    remaining = get_remaining_topics(completed_topics)
    completion_percent = get_course_completion_percent(completed_topics)
    next_topic = get_recommended_next_topic(completed_topics)
    
    return {
        "course_name": COURSE_NAME,
        "total_topics": len(COURSE_TOPICS),
        "completed_topics": completed_topics,
        "completed_count": len(completed_topics),
        "remaining_topics": remaining,
        "remaining_count": len(remaining),
        "weak_topics": weak_topics,
        "completion_percent": completion_percent,
        "recommended_next_topic": next_topic,
        "course_complete": completion_percent == 100
    }

import wikipediaapi

def search_wikipedia(topic: str) -> str:
    try:
        wiki = wikipediaapi.Wikipedia(
            language='en',
            user_agent='EduAgent/1.0 (educational-tutor-project)'
        )
        page = wiki.page(topic)
        if page.exists():
            return f"Wikipedia - {page.title}:\n{page.summary[:1000]}"
        search_term = topic.split()[0] if ' ' in topic else topic
        page = wiki.page(search_term)
        if page.exists():
            return f"Wikipedia - {page.title}:\n{page.summary[:800]}"
        return f"No Wikipedia article found for '{topic}'."
    except Exception as e:
        return f"Wikipedia lookup failed: {str(e)}"

"""Create the provider client only when a live model call is needed."""
import os
from functools import lru_cache

from dotenv import load_dotenv
from groq import Groq

load_dotenv()


@lru_cache(maxsize=1)
def get_client():
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        raise RuntimeError("Set GROQ_API_KEY in .env before making live LLM requests.")
    return Groq(api_key=key, timeout=30, max_retries=1)

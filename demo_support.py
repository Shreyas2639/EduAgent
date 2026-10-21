"""Explicit simulation backend for offline tests. It never calls an LLM."""
import json
from types import SimpleNamespace


class SimulatedGroq:
    prompts = []

    def __init__(self, **kwargs):
        self.chat = SimpleNamespace(completions=self)

    def create(self, messages, **kwargs):
        prompt = "\n".join(message["content"] for message in messages)
        self.prompts.append(prompt)
        if "safety classifier" in prompt:
            text = "SAFE"
        elif "intent classifier" in prompt:
            message = prompt.rsplit("Student message:\n", 1)[-1].lower()
            text = "QUIZ" if "quiz" in message else "MEMORY" if "progress" in message else "EXPLAIN"
        elif "topic resolver" in prompt:
            message = prompt.rsplit("Student message:\n", 1)[-1].split("Instructions:")[0].lower()
            text = "functions" if "function" in message else "loops" if "loop" in message else "OFF_TOPIC"
        elif "quiz generator" in prompt:
            text = json.dumps([{"question": f"Practice question {i + 1}: choose the loop keyword.",
                                "options": ["A. for", "B. def", "C. class", "D. return"],
                                "answer": "A. for", "explanation": "A for loop repeats over items."}
                               for i in range(3)])
        elif "Preferred format: bullet_points" in prompt:
            text = "- SIMULATION: A loop repeats work.\n- Example: for item in items: print(item)."
        elif "Preferred format: worked_examples" in prompt:
            text = "SIMULATION: Worked example: for n in [1, 2]: print(n). This prints 1 and 2."
        elif "feedback" in prompt.lower():
            text = "SIMULATION: Review the explanation and keep practicing."
        else:
            text = "SIMULATION: A loop repeats work for each item in a sequence."
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=text))])

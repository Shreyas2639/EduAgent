from typing import List, Dict

class ShortTermMemory:
    def __init__(self, max_messages: int = 10):
        self.history: List[Dict] = []
        self.max_messages = max_messages

    def add_message(self, role: str, content: str):
        self.history.append({"role": role, "content": content})
        if len(self.history) > self.max_messages * 2:
            self.history = self.history[-self.max_messages * 2:]

    def get_history(self) -> List[Dict]:
        return self.history

    def get_context_string(self) -> str:
        if not self.history:
            return "No previous conversation."
        lines = []
        for msg in self.history[-6:]:
            role = "Student" if msg["role"] == "user" else "Tutor"
            lines.append(f"{role}: {msg['content']}")
        return "\n".join(lines)

    def clear(self):
        self.history = []
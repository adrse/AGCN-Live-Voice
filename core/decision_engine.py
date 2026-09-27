from __future__ import annotations


class DecisionEngine:
    """Escolhe a próxima missão de fala com base em prioridade e contexto."""

    def decide(self, group: dict, memory_snapshot: dict) -> dict:
        primary = dict(group["primary"])
        intent = primary.get("intent")
        priority = int(group.get("priority", primary.get("priority", 0)))

        interrupt = priority >= 90
        speech_length = "short"

        if intent in {"objection", "safety_or_critical"}:
            speech_length = "medium"
        elif intent in {"engagement", "purchase_confirmation"}:
            speech_length = "micro"

        return {
            "type": "reactive",
            "intent": intent,
            "topic": primary.get("topic"),
            "label": primary.get("label"),
            "priority": priority,
            "user": primary.get("user"),
            "comment": primary.get("comment"),
            "items": group.get("items", []),
            "users": group.get("users", []),
            "topics": group.get("topics", []),
            "interrupt": interrupt,
            "speech_length": speech_length,
            "resume_topic": memory_snapshot.get("current_topic"),
        }

    def proactive(self, topic: str, priority: int = 30) -> dict:
        return {
            "type": "proactive",
            "intent": "proactive",
            "topic": topic,
            "label": "Fala proativa",
            "priority": priority,
            "user": None,
            "comment": None,
            "items": [],
            "users": [],
            "topics": [topic],
            "interrupt": False,
            "speech_length": "short",
            "resume_topic": None,
        }

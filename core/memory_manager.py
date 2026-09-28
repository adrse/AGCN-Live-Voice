from __future__ import annotations

import time
from collections import deque


class MemoryManager:
    """Memória operacional curta da LIVE."""

    def __init__(self):
        self.speeches = deque(maxlen=30)
        self.responded_users = deque(maxlen=40)
        self.topics = deque(maxlen=30)
        self.ctas = deque(maxlen=20)
        self.tactics = deque(maxlen=40)
        self.purchase_confirmations = deque(maxlen=30)
        self.live_started_at = time.time()
        self.last_speech_at = 0.0
        self.proactive_turns = 0
        self.last_newcomer_recap_at = 0.0
        self.current_topic = None
        self.current_pitch_topic = None
        self.interrupted_topic = None

    def remember_speech(self, item: dict) -> None:
        now = time.time()
        record = {
            "at": now,
            "speech": item.get("speech", ""),
            "topic": item.get("topic"),
            "intent": item.get("intent") or item.get("category"),
            "cta": item.get("cta"),
            "user": item.get("user"),
            "type": item.get("type"),
        }
        self.speeches.append(record)
        self.last_speech_at = now

        if record["user"]:
            self.responded_users.append({
                "user": record["user"],
                "at": now,
            })

        if record["topic"]:
            self.topics.append({
                "topic": record["topic"],
                "at": now,
            })
            self.current_topic = record["topic"]

            if record["type"] == "proactive":
                self.current_pitch_topic = record["topic"]
                self.proactive_turns += 1
                if record["topic"] == "newcomer_recap":
                    self.last_newcomer_recap_at = now

        if record["cta"]:
            self.ctas.append({
                "cta": record["cta"],
                "at": now,
            })

        if record["intent"] == "purchase_confirmation":
            self.purchase_confirmations.append({
                "user": record["user"],
                "at": now,
            })

        resume_topic = item.get("resume_topic")
        if record["type"] == "reactive" and resume_topic:
            self.interrupted_topic = resume_topic

    def seconds_since_speech(self) -> float:
        if not self.last_speech_at:
            return 9999.0
        return max(0.0, time.time() - self.last_speech_at)

    def recently_said_topic(self, topic: str, within: float = 45.0) -> bool:
        now = time.time()
        return any(
            x.get("topic") == topic and now - x.get("at", 0) <= within
            for x in self.topics
        )

    def recently_used_cta(self, cta: str, within: float = 30.0) -> bool:
        now = time.time()
        return any(
            x.get("cta") == cta and now - x.get("at", 0) <= within
            for x in self.ctas
        )

    def newcomer_recap_due(
        self,
        *,
        min_since_start: float = 300.0,
        cooldown: float = 420.0,
    ) -> bool:
        now = time.time()
        if now - self.live_started_at < min_since_start:
            return False
        if not self.last_newcomer_recap_at:
            return True
        return now - self.last_newcomer_recap_at >= cooldown

    def proactive_cursor(self) -> int:
        return self.proactive_turns

    def remember_tactic(self, tactic: str) -> None:
        tactic = str(tactic or "").strip()
        if not tactic:
            return
        self.tactics.append({
            "tactic": tactic,
            "at": time.time(),
        })

    def recently_used_tactic(
        self,
        tactic: str,
        within: float = 35.0,
    ) -> bool:
        now = time.time()
        target = str(tactic or "")
        return any(
            x.get("tactic") == target
            and now - x.get("at", 0) <= within
            for x in self.tactics
        )

    def recent_purchase_count(self, within: float = 180.0) -> int:
        now = time.time()
        return sum(
            1
            for x in self.purchase_confirmations
            if now - x.get("at", 0) <= within
        )

    def consume_interrupted_topic(self) -> str | None:
        topic = self.interrupted_topic
        self.interrupted_topic = None
        return topic

    def recently_answered_user(self, user: str, within: float = 20.0) -> bool:
        now = time.time()
        target = str(user or "").casefold()
        return any(
            str(x.get("user") or "").casefold() == target
            and now - x.get("at", 0) <= within
            for x in self.responded_users
        )

    def last_topics(self, limit: int = 6) -> list[str]:
        return [
            x["topic"]
            for x in list(self.topics)[-limit:]
            if x.get("topic")
        ]

    def last_speeches(self, limit: int = 5) -> list[str]:
        return [
            x["speech"]
            for x in list(self.speeches)[-limit:]
            if x.get("speech")
        ]

    def snapshot(self) -> dict:
        return {
            "seconds_since_speech": round(self.seconds_since_speech(), 1),
            "live_seconds": round(max(0.0, time.time() - self.live_started_at), 1),
            "proactive_turns": self.proactive_turns,
            "newcomer_recap_due": self.newcomer_recap_due(),
            "current_topic": self.current_topic,
            "current_pitch_topic": self.current_pitch_topic,
            "interrupted_topic": self.interrupted_topic,
            "recent_topics": self.last_topics(),
            "recent_speeches": self.last_speeches(),
            "recent_purchase_count": self.recent_purchase_count(),
            "recent_tactics": [
                x.get("tactic")
                for x in list(self.tactics)[-8:]
                if x.get("tactic")
            ],
        }

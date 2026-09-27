from __future__ import annotations


class SilenceWatchdog:
    """Mantém a apresentação contínua sem ultrapassar o limite de silêncio."""

    def __init__(self, target_seconds: float = 8.0, hard_seconds: float = 10.0):
        self.target_seconds = target_seconds
        self.hard_seconds = hard_seconds

    def should_trigger(self, seconds_since_speech: float, queue_empty: bool) -> bool:
        return queue_empty and seconds_since_speech >= self.target_seconds

    def urgency(self, seconds_since_speech: float) -> str:
        if seconds_since_speech >= self.hard_seconds:
            return "hard"
        if seconds_since_speech >= self.target_seconds:
            return "target"
        return "ok"

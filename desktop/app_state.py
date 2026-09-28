from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PresenterState(str, Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"


class TikTokState(str, Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    LIVE = "live"
    ENDED = "ended"
    ERROR = "error"


@dataclass(slots=True)
class AppState:
    presenter: PresenterState = PresenterState.STOPPED
    tiktok: TikTokState = TikTokState.DISCONNECTED
    username: str = ""
    viewers: int = 0
    likes: int = 0
    active_product: dict[str, Any] = field(default_factory=dict)
    speaking_now: str = ""
    brain_provider: str = "qwen_local"
    tts_provider: str = "local"
    output_device: str = ""

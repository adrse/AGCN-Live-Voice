"""Contratos neutros para a camada desktop/providers do AGCN Live Voice.

Este arquivo não altera o runtime atual. Ele define interfaces estáveis para que
providers locais/API e a UI PySide6 possam ser implementados sem acoplar o core
a um fornecedor específico.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, Sequence


@dataclass(slots=True)
class CommentPayload:
    id: str = ""
    username: str = ""
    text: str = ""


@dataclass(slots=True)
class BrainContext:
    mode: str  # "comment_reply" | "proactive"
    product: dict[str, Any] = field(default_factory=dict)
    live_conditions: dict[str, Any] = field(default_factory=dict)
    comment: CommentPayload | None = None
    recent_comments: list[CommentPayload] = field(default_factory=list)
    recent_speeches: list[str] = field(default_factory=list)
    recent_facts: list[str] = field(default_factory=list)
    sales_thread: str = ""
    planner_topic: str = ""
    allowed_facts: list[str] = field(default_factory=list)


@dataclass(slots=True)
class BrainResult:
    speech: str
    topic: str = ""
    used_facts: list[str] = field(default_factory=list)
    needs_fact: bool = False
    next_sales_thread: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AudioChunk:
    data: bytes
    sample_rate: int
    channels: int = 1
    sample_width: int = 2
    format: str = "pcm_s16le"


@dataclass(slots=True)
class MediaClip:
    path: str
    title: str = ""
    enabled: bool = True
    loop: bool = True
    muted: bool = True
    tags: list[str] = field(default_factory=list)


class BrainProvider(Protocol):
    """Gera fala natural usando somente o contexto/fatos autorizados."""

    @property
    def name(self) -> str:
        ...

    def healthcheck(self) -> tuple[bool, str]:
        ...

    def generate(self, context: BrainContext) -> BrainResult:
        ...


class TTSProvider(Protocol):
    """Converte uma fala pronta em áudio reproduzível."""

    @property
    def name(self) -> str:
        ...

    def healthcheck(self) -> tuple[bool, str]:
        ...

    def synthesize(self, text: str, *, voice: str | None = None) -> AudioChunk:
        ...


class AudioSink(Protocol):
    """Reproduz áudio no dispositivo de saída selecionado."""

    def list_devices(self) -> Sequence[str]:
        ...

    def select_device(self, device_name: str) -> None:
        ...

    def play(self, chunk: AudioChunk) -> None:
        ...

    def stop(self) -> None:
        ...


class MediaController(Protocol):
    """Controla a playlist da janela 9:16."""

    def set_playlist(self, clips: Sequence[MediaClip]) -> None:
        ...

    def play(self) -> None:
        ...

    def pause(self) -> None:
        ...

    def next(self) -> None:
        ...

    def previous(self) -> None:
        ...

    def current(self) -> MediaClip | None:
        ...

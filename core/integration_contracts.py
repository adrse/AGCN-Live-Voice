"""Contratos neutros para a camada desktop/providers do AGCN Live Voice.

A regra importante é separar PresenterBrain de TextModelTransport.
Assim nenhum provider pode esquecer as instruções comerciais do AGCN.
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
    mode: str
    product: dict[str, Any] = field(default_factory=dict)
    live_conditions: dict[str, Any] = field(default_factory=dict)
    comment: CommentPayload | None = None
    decision: dict[str, Any] = field(default_factory=dict)
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


class TextModelTransport(Protocol):
    """Camada fina do fornecedor. Nao contem a politica comercial."""

    @property
    def name(self) -> str:
        ...

    def healthcheck(self) -> tuple[bool, str]:
        ...

    def complete(self, *, system_instruction: str, user_payload: str) -> str:
        ...


class BrainProvider(Protocol):
    """Interface de alto nivel consumida pelo runtime."""

    @property
    def name(self) -> str:
        ...

    def healthcheck(self) -> tuple[bool, str]:
        ...

    def generate(self, context: BrainContext) -> BrainResult:
        ...


class TTSProvider(Protocol):
    @property
    def name(self) -> str:
        ...

    def healthcheck(self) -> tuple[bool, str]:
        ...

    def synthesize(self, text: str, *, voice: str | None = None) -> AudioChunk:
        ...


class AudioSink(Protocol):
    def list_devices(self) -> Sequence[str]:
        ...

    def select_device(self, device_name: str) -> None:
        ...

    def play(self, chunk: AudioChunk) -> None:
        ...

    def stop(self) -> None:
        ...

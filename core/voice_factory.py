"""Monta TTS + saída de áudio + fila de voz a partir da configuração."""

from __future__ import annotations

from typing import Any

from core.audio_output import SoundDeviceAudioSink
from core.tts_providers import build_tts_provider
from core.voice_service import VoiceService


def build_voice_service(
    config: dict[str, Any] | None = None,
) -> VoiceService:
    config = dict(config or {})
    tts_cfg = dict(config.get("tts") or {})
    audio_cfg = dict(config.get("audio") or {})

    tts = build_tts_provider(config)
    sink = SoundDeviceAudioSink(
        device_name=str(audio_cfg.get("output_device") or ""),
        volume=float(audio_cfg.get("volume", 1.0)),
    )

    return VoiceService(
        tts,
        sink,
        default_voice=str(tts_cfg.get("voice") or "") or None,
        max_queue=int(tts_cfg.get("max_queue", 30)),
    )

"""Neural TTS providers independentes das vozes do Windows."""

from __future__ import annotations

from typing import Any

import requests

from core.integration_contracts import AudioChunk


class NeuralTTSError(RuntimeError):
    pass


class ElevenLabsTTSProvider:
    """ElevenLabs TTS usando PCM 24 kHz para playback direto."""

    def __init__(
        self,
        *,
        api_key: str,
        voice_id: str,
        model: str = "eleven_v3_conversational",
        base_url: str = "https://api.elevenlabs.io/v1",
        timeout_seconds: float = 45,
        speed: float = 1.15,
        stability: float = 0.45,
        similarity_boost: float = 0.80,
        style: float = 0.20,
        use_speaker_boost: bool = True,
        session=None,
    ) -> None:
        self.api_key = str(api_key or "").strip()
        self.voice_id = str(voice_id or "").strip()
        self.model = str(model or "").strip()
        self.base_url = str(base_url or "").rstrip("/")
        self.timeout_seconds = float(timeout_seconds)
        self.speed = max(0.7, min(1.2, float(speed)))
        self.stability = max(0.0, min(1.0, float(stability)))
        self.similarity_boost = max(
            0.0, min(1.0, float(similarity_boost))
        )
        self.style = max(0.0, min(1.0, float(style)))
        self.use_speaker_boost = bool(use_speaker_boost)
        self.session = session or requests.Session()

        if not self.api_key:
            raise ValueError("api_key da ElevenLabs é obrigatória")
        if not self.voice_id:
            raise ValueError("voice_id da ElevenLabs é obrigatório")

    @property
    def name(self) -> str:
        return f"ElevenLabs/{self.model}"

    def _headers(self) -> dict[str, str]:
        return {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
        }

    def healthcheck(self) -> tuple[bool, str]:
        try:
            response = self.session.get(
                f"{self.base_url}/voices/{self.voice_id}",
                headers=self._headers(),
                timeout=min(self.timeout_seconds, 8.0),
            )
            response.raise_for_status()
            payload = response.json()
            name = str(payload.get("name") or self.voice_id)
            return (
                True,
                f"ElevenLabs disponível; voz: {name}; "
                f"modelo: {self.model}; velocidade: {self.speed:.2f}x.",
            )
        except Exception as exc:
            return False, f"ElevenLabs indisponível: {exc}"

    def synthesize(
        self,
        text: str,
        *,
        voice: str | None = None,
    ) -> AudioChunk:
        text = str(text or "").strip()
        if not text:
            raise NeuralTTSError("texto vazio para TTS")

        voice_id = str(voice or self.voice_id).strip()
        body: dict[str, Any] = {
            "text": text,
            "model_id": self.model,
            "voice_settings": {
                "stability": self.stability,
                "similarity_boost": self.similarity_boost,
                "style": self.style,
                "use_speaker_boost": self.use_speaker_boost,
                "speed": self.speed,
            },
        }

        try:
            response = self.session.post(
                f"{self.base_url}/text-to-speech/{voice_id}",
                params={"output_format": "pcm_24000"},
                headers=self._headers(),
                json=body,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise NeuralTTSError(
                f"falha no TTS ElevenLabs: {exc}"
            ) from exc

        raw = bytes(response.content)
        if not raw:
            raise NeuralTTSError("ElevenLabs retornou áudio vazio")

        return AudioChunk(
            data=raw,
            sample_rate=24000,
            channels=1,
            sample_width=2,
            format="pcm_s16le",
        )

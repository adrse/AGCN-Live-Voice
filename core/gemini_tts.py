"""Gemini 3.8 TTS provider for AGCN Live Voice.

Uses the Gemini Interactions API for exact-text recitation with structured
speech_metadata.style. It never decides what to say; the Presenter already
approved the speech before this provider receives it.
"""

from __future__ import annotations

import base64
import io
import subprocess
import tempfile
import wave
from pathlib import Path

import requests

from core.integration_contracts import AudioChunk
from core.voice_expression import build_voice_instructions
from core.voice_profiles import get_voice_profile


GEMINI_PROFILE_VOICES = {
    "female_fast": "Kore",
    "male_fast": "Puck",
}


class GeminiTTSError(RuntimeError):
    pass


def _wav_bytes_to_chunk(data: bytes) -> AudioChunk:
    try:
        with wave.open(io.BytesIO(data), "rb") as wav:
            channels = wav.getnchannels()
            sample_width = wav.getsampwidth()
            sample_rate = wav.getframerate()
            frames = wav.readframes(wav.getnframes())
    except Exception as exc:
        raise GeminiTTSError("Gemini retornou áudio WAV inválido") from exc

    return AudioChunk(
        data=frames,
        sample_rate=sample_rate,
        channels=channels,
        sample_width=sample_width,
        format="pcm_s16le" if sample_width == 2 else "pcm",
    )


def _chunk_to_wav_bytes(chunk: AudioChunk) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(chunk.channels)
        wav.setsampwidth(chunk.sample_width)
        wav.setframerate(chunk.sample_rate)
        wav.writeframes(chunk.data)
    return buffer.getvalue()


def _ffmpeg_exe() -> str | None:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def _adjust_speed(chunk: AudioChunk, speed: float) -> AudioChunk:
    speed = max(0.80, min(1.60, float(speed)))
    if abs(speed - 1.0) < 0.01:
        return chunk

    ffmpeg = _ffmpeg_exe()
    if not ffmpeg:
        return chunk

    with tempfile.TemporaryDirectory(prefix="agcn_gemini_speed_") as tmp:
        src = Path(tmp) / "in.wav"
        dst = Path(tmp) / "out.wav"
        src.write_bytes(_chunk_to_wav_bytes(chunk))

        completed = subprocess.run(
            [
                ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(src),
                "-filter:a",
                f"atempo={speed:.4f}",
                str(dst),
            ],
            capture_output=True,
            timeout=30,
            check=False,
        )
        if completed.returncode != 0 or not dst.exists():
            return chunk
        return _wav_bytes_to_chunk(dst.read_bytes())


class GeminiTTSProvider:
    def __init__(
        self,
        *,
        api_key: str,
        model: str = "gemini-3.8-flash-lite-tts",
        profile_id: str = "female_fast",
        voice_override: str = "",
        base_url: str = "https://generativelanguage.googleapis.com",
        timeout_seconds: float = 45,
        speed: float = 1.28,
        expressive: bool = True,
        expression_strength: float = 1.0,
        session=None,
    ) -> None:
        self.api_key = str(api_key or "").strip()
        self.model = str(model or "gemini-3.8-flash-lite-tts").strip()
        self.profile_id = (
            profile_id
            if profile_id in GEMINI_PROFILE_VOICES
            else "female_fast"
        )
        self.voice = str(
            voice_override or GEMINI_PROFILE_VOICES[self.profile_id]
        ).strip()
        self.base_url = str(base_url or "").rstrip("/")
        self.timeout_seconds = float(timeout_seconds)
        self.speed = max(0.80, min(1.60, float(speed)))
        self.expressive = bool(expressive)
        self.expression_strength = max(
            0.0, min(1.5, float(expression_strength))
        )
        profile = get_voice_profile(self.profile_id)
        self.base_instructions = str(
            profile.get("qwen_style") or ""
        ).strip()
        self.active_style = "sales_energy"
        self.active_instructions = self.base_instructions
        self.session = session or requests.Session()

    @property
    def name(self) -> str:
        return f"Gemini Premium TTS/{self.model}/{self.voice}"

    def configure_for_job(self, metadata: dict | None = None) -> str:
        if not self.expressive:
            self.active_style = "sales_energy"
            self.active_instructions = self.base_instructions
            return self.active_style

        style_id, instructions = build_voice_instructions(
            self.base_instructions,
            metadata,
            strength=self.expression_strength,
        )
        self.active_style = style_id
        self.active_instructions = instructions
        return style_id

    def _headers(self) -> dict[str, str]:
        return {
            "x-goog-api-key": self.api_key,
            "Content-Type": "application/json",
        }

    def healthcheck(self) -> tuple[bool, str]:
        if not self.api_key:
            return False, "GEMINI_API_KEY não configurada"
        try:
            response = self.session.get(
                f"{self.base_url}/v1beta/models/{self.model}",
                headers=self._headers(),
                timeout=min(self.timeout_seconds, 8.0),
            )
            response.raise_for_status()
            return (
                True,
                f"Gemini TTS pronto; modelo={self.model}; voz={self.voice}; "
                f"velocidade={self.speed:.2f}x.",
            )
        except Exception as exc:
            return False, f"Gemini TTS indisponível: {exc}"

    @staticmethod
    def _extract_audio(payload: dict) -> bytes:
        steps = payload.get("steps") if isinstance(payload, dict) else None
        for step in reversed(steps or []):
            if not isinstance(step, dict) or step.get("type") != "model_output":
                continue
            for item in reversed(step.get("content") or []):
                if not isinstance(item, dict) or item.get("type") != "audio":
                    continue
                data = str(item.get("data") or "").strip()
                if data:
                    try:
                        return base64.b64decode(data)
                    except Exception as exc:
                        raise GeminiTTSError(
                            "Gemini retornou áudio base64 inválido"
                        ) from exc
        raise GeminiTTSError("Gemini não retornou bloco de áudio")

    def synthesize(
        self,
        text: str,
        *,
        voice: str | None = None,
    ) -> AudioChunk:
        text = str(text or "").strip()
        if not text:
            raise GeminiTTSError("texto vazio para TTS")
        if not self.api_key:
            raise GeminiTTSError("GEMINI_API_KEY não configurada")

        selected_voice = str(voice or self.voice).strip()
        body = {
            "model": self.model,
            "input": [{
                "type": "user_input",
                "content": [{
                    "type": "text",
                    "text": text,
                    "annotations": [{
                        "type": "speech_metadata",
                        "style": self.active_instructions,
                    }],
                }],
            }],
            "response_format": {
                "type": "audio",
            },
            "generation_config": {
                "speech_config": [
                    {"voice": selected_voice},
                ],
            },
        }

        try:
            response = self.session.post(
                f"{self.base_url}/v1beta/interactions",
                headers=self._headers(),
                json=body,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            raise GeminiTTSError(f"falha no Gemini TTS: {exc}") from exc
        except ValueError as exc:
            raise GeminiTTSError("resposta JSON inválida do Gemini TTS") from exc

        chunk = _wav_bytes_to_chunk(self._extract_audio(payload))
        return _adjust_speed(chunk, self.speed)

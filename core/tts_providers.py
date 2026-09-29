"""Providers de texto-para-voz do AGCN Live Voice."""

from __future__ import annotations

import io
import os
import tempfile
import wave
from pathlib import Path
from typing import Any

import requests

from core.integration_contracts import AudioChunk, TTSProvider


class TTSError(RuntimeError):
    pass


def wav_bytes_to_chunk(data: bytes) -> AudioChunk:
    try:
        with wave.open(io.BytesIO(data), "rb") as wav:
            channels = wav.getnchannels()
            sample_width = wav.getsampwidth()
            sample_rate = wav.getframerate()
            frames = wav.readframes(wav.getnframes())
    except Exception as exc:
        raise TTSError("áudio WAV inválido") from exc

    return AudioChunk(
        data=frames,
        sample_rate=sample_rate,
        channels=channels,
        sample_width=sample_width,
        format="pcm_s16le" if sample_width == 2 else "pcm",
    )


class LocalPyttsx3TTSProvider:
    """TTS offline simples usando o mecanismo de voz do Windows/SAPI."""

    def __init__(
        self,
        *,
        rate: int = 190,
        volume: float = 1.0,
    ) -> None:
        self.rate = int(rate)
        self.volume = max(0.0, min(1.0, float(volume)))

    @property
    def name(self) -> str:
        return "Local Windows TTS/pyttsx3"

    @staticmethod
    def _engine():
        try:
            import pyttsx3
        except ImportError as exc:
            raise TTSError(
                "pyttsx3 não instalado. Instale requirements-desktop.txt"
            ) from exc
        return pyttsx3.init()

    def healthcheck(self) -> tuple[bool, str]:
        try:
            engine = self._engine()
            voices = engine.getProperty("voices") or []
            engine.stop()
            return True, f"TTS local disponível ({len(voices)} voz(es))."
        except Exception as exc:
            return False, f"TTS local indisponível: {exc}"

    def list_voices(self) -> list[dict[str, str]]:
        engine = self._engine()
        try:
            result = []
            for item in engine.getProperty("voices") or []:
                result.append({
                    "id": str(getattr(item, "id", "") or ""),
                    "name": str(getattr(item, "name", "") or ""),
                })
            return result
        finally:
            engine.stop()

    def _resolve_voice_id(self, engine, voice: str | None) -> str | None:
        target = str(voice or "").strip().casefold()
        if not target:
            return None
        for item in engine.getProperty("voices") or []:
            voice_id = str(getattr(item, "id", "") or "")
            name = str(getattr(item, "name", "") or "")
            if target in {voice_id.casefold(), name.casefold()}:
                return voice_id
            if target in name.casefold():
                return voice_id
        return None

    def synthesize(self, text: str, *, voice: str | None = None) -> AudioChunk:
        text = str(text or "").strip()
        if not text:
            raise TTSError("texto vazio para TTS")

        temp_path = None
        engine = self._engine()
        try:
            engine.setProperty("rate", self.rate)
            engine.setProperty("volume", self.volume)
            voice_id = self._resolve_voice_id(engine, voice)
            if voice_id:
                engine.setProperty("voice", voice_id)

            handle = tempfile.NamedTemporaryFile(
                suffix=".wav",
                delete=False,
            )
            temp_path = Path(handle.name)
            handle.close()

            engine.save_to_file(text, str(temp_path))
            engine.runAndWait()

            if not temp_path.exists() or temp_path.stat().st_size <= 44:
                raise TTSError("TTS local não gerou arquivo WAV válido")

            return wav_bytes_to_chunk(temp_path.read_bytes())
        finally:
            try:
                engine.stop()
            except Exception:
                pass
            if temp_path:
                try:
                    temp_path.unlink(missing_ok=True)
                except Exception:
                    pass


class OpenAITTSProvider:
    """TTS premium opcional via /v1/audio/speech."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "gpt-4o-mini-tts",
        default_voice: str = "coral",
        base_url: str = "https://api.openai.com/v1",
        timeout_seconds: float = 45,
        instructions: str = (
            "Fale em português brasileiro, ritmo ágil de LIVE commerce, "
            "natural, confiante e sem soar como locução publicitária exagerada."
        ),
        session=None,
    ) -> None:
        self.api_key = str(api_key or "").strip()
        self.model = str(model or "").strip()
        self.default_voice = str(default_voice or "coral").strip()
        self.base_url = str(base_url or "").rstrip("/")
        self.timeout_seconds = float(timeout_seconds)
        self.instructions = str(instructions or "").strip()
        self.session = session or requests.Session()

        if not self.api_key:
            raise ValueError("api_key da OpenAI é obrigatória para TTS")

    @property
    def name(self) -> str:
        return f"OpenAI TTS/{self.model}"

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def healthcheck(self) -> tuple[bool, str]:
        try:
            response = self.session.get(
                f"{self.base_url}/models/{self.model}",
                headers=self._headers(),
                timeout=min(self.timeout_seconds, 8.0),
            )
            response.raise_for_status()
            return True, f"TTS OpenAI disponível com {self.model}."
        except Exception as exc:
            return False, f"TTS OpenAI indisponível: {exc}"

    def synthesize(self, text: str, *, voice: str | None = None) -> AudioChunk:
        text = str(text or "").strip()
        if not text:
            raise TTSError("texto vazio para TTS")

        body: dict[str, Any] = {
            "model": self.model,
            "voice": str(voice or self.default_voice),
            "input": text,
            "response_format": "wav",
        }
        if self.instructions:
            body["instructions"] = self.instructions

        try:
            response = self.session.post(
                f"{self.base_url}/audio/speech",
                headers=self._headers(),
                json=body,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise TTSError(f"falha no TTS OpenAI: {exc}") from exc

        return wav_bytes_to_chunk(bytes(response.content))


class FallbackTTSProvider:
    def __init__(self, primary: TTSProvider, fallback: TTSProvider) -> None:
        self.primary = primary
        self.fallback = fallback
        self.last_provider = ""

    @property
    def name(self) -> str:
        return f"{self.primary.name} -> fallback {self.fallback.name}"

    def healthcheck(self) -> tuple[bool, str]:
        a, am = self.primary.healthcheck()
        b, bm = self.fallback.healthcheck()
        return a or b, f"primário: {am} | fallback: {bm}"

    def synthesize(self, text: str, *, voice: str | None = None) -> AudioChunk:
        try:
            chunk = self.primary.synthesize(text, voice=voice)
            self.last_provider = self.primary.name
            return chunk
        except Exception:
            chunk = self.fallback.synthesize(text, voice=voice)
            self.last_provider = self.fallback.name
            return chunk


def build_tts_provider(config: dict | None = None) -> TTSProvider:
    config = dict(config or {})
    cfg = dict(config.get("tts") or config)
    provider = str(cfg.get("provider") or "local").casefold()

    local_cfg = dict(cfg.get("local") or {})
    local = LocalPyttsx3TTSProvider(
        rate=int(local_cfg.get("rate", 190)),
        volume=float(local_cfg.get("volume", 1.0)),
    )

    if provider in {"local", "pyttsx3", "windows"}:
        return local

    if provider in {"openai", "premium", "api"}:
        api = dict(cfg.get("api") or {})
        key_env = str(api.get("api_key_env") or "OPENAI_API_KEY")
        try:
            premium = OpenAITTSProvider(
                api_key=str(os.getenv(key_env) or ""),
                model=str(api.get("model") or "gpt-4o-mini-tts"),
                default_voice=str(api.get("voice") or "coral"),
                base_url=str(
                    api.get("base_url")
                    or "https://api.openai.com/v1"
                ),
                timeout_seconds=float(api.get("timeout_seconds", 45)),
                instructions=str(api.get("instructions") or ""),
            )
        except Exception:
            if bool(cfg.get("fallback_local", True)):
                return local
            raise

        if bool(cfg.get("fallback_local", True)):
            return FallbackTTSProvider(premium, local)
        return premium

    raise ValueError(f"TTS provider desconhecido: {provider}")

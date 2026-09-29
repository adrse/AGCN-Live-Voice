"""Providers de texto-para-voz do AGCN Live Voice.

As vozes oficiais do produto são neurais e independentes das vozes instaladas
no Windows. O provider local/pyttsx3 permanece apenas como fallback legado
explicitamente selecionado.
"""

from __future__ import annotations

import io
import tempfile
import wave
from pathlib import Path
from typing import Any

import requests

from core.integration_contracts import AudioChunk, TTSProvider
from core.neural_tts import ElevenLabsTTSProvider
from core.secret_store import get_secret
from core.voice_profiles import get_voice_profile


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
    """Fallback legado. Não é uma das vozes oficiais do AGCN."""

    def __init__(
        self,
        *,
        rate: int = 235,
        volume: float = 1.0,
        preferred_voice_keywords: list[str] | None = None,
        profile_label: str = "",
    ) -> None:
        self.rate = int(rate)
        self.volume = max(0.0, min(1.0, float(volume)))
        self.preferred_voice_keywords = [
            str(x).strip().casefold()
            for x in (preferred_voice_keywords or [])
            if str(x).strip()
        ]
        self.profile_label = str(profile_label or "").strip()

    @property
    def name(self) -> str:
        suffix = f" / {self.profile_label}" if self.profile_label else ""
        return f"Local legado Windows/pyttsx3{suffix}"

    @staticmethod
    def _engine():
        try:
            import pyttsx3
        except ImportError as exc:
            raise TTSError(
                "pyttsx3 não instalado. Instale requirements-desktop.txt"
            ) from exc
        return pyttsx3.init()

    @staticmethod
    def _voice_data(item) -> tuple[str, str, str]:
        voice_id = str(getattr(item, "id", "") or "")
        name = str(getattr(item, "name", "") or "")
        languages = " ".join(
            str(x) for x in (getattr(item, "languages", None) or [])
        )
        return voice_id, name, languages

    def _profile_voice_id(self, engine) -> str | None:
        voices = list(engine.getProperty("voices") or [])
        if not voices:
            return None
        for keyword in self.preferred_voice_keywords:
            for item in voices:
                voice_id, name, languages = self._voice_data(item)
                haystack = f"{voice_id} {name} {languages}".casefold()
                if keyword in haystack:
                    return voice_id
        return str(getattr(voices[0], "id", "") or "") or None

    def healthcheck(self) -> tuple[bool, str]:
        try:
            engine = self._engine()
            voices = engine.getProperty("voices") or []
            engine.stop()
            return (
                bool(voices),
                f"Fallback local disponível ({len(voices)} voz(es)).",
            )
        except Exception as exc:
            return False, f"Fallback local indisponível: {exc}"

    def list_voices(self) -> list[dict[str, str]]:
        engine = self._engine()
        try:
            result = []
            for item in engine.getProperty("voices") or []:
                voice_id, name, languages = self._voice_data(item)
                result.append({
                    "id": voice_id,
                    "name": name,
                    "languages": languages,
                })
            return result
        finally:
            engine.stop()

    def _resolve_voice_id(self, engine, voice: str | None) -> str | None:
        target = str(voice or "").strip().casefold()
        if not target:
            return self._profile_voice_id(engine)
        for item in engine.getProperty("voices") or []:
            voice_id, name, _ = self._voice_data(item)
            if target in {voice_id.casefold(), name.casefold()}:
                return voice_id
            if target in name.casefold():
                return voice_id
        return self._profile_voice_id(engine)

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

            handle = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            temp_path = Path(handle.name)
            handle.close()

            engine.save_to_file(text, str(temp_path))
            engine.runAndWait()

            if not temp_path.exists() or temp_path.stat().st_size <= 44:
                raise TTSError("TTS local não gerou WAV válido")
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
    """Voz neural oficial via OpenAI Audio Speech API."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "gpt-4o-mini-tts",
        default_voice: str = "marin",
        base_url: str = "https://api.openai.com/v1",
        timeout_seconds: float = 45,
        instructions: str = "",
        speed: float = 1.28,
        profile_label: str = "",
        session=None,
    ) -> None:
        self.api_key = str(api_key or "").strip()
        self.model = str(model or "").strip()
        self.default_voice = str(default_voice or "marin").strip()
        self.base_url = str(base_url or "").rstrip("/")
        self.timeout_seconds = float(timeout_seconds)
        self.instructions = str(instructions or "").strip()
        self.speed = max(0.25, min(4.0, float(speed)))
        self.profile_label = str(profile_label or "").strip()
        self.session = session or requests.Session()

        if not self.api_key:
            raise ValueError("OPENAI_API_KEY não configurada")

    @property
    def name(self) -> str:
        suffix = f" / {self.profile_label}" if self.profile_label else ""
        return f"OpenAI Neural Voice/{self.model}{suffix}"

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
            return (
                True,
                f"OpenAI Voice disponível; {self.profile_label}; "
                f"{self.speed:.2f}x.",
            )
        except Exception as exc:
            return False, f"OpenAI Voice indisponível: {exc}"

    def synthesize(self, text: str, *, voice: str | None = None) -> AudioChunk:
        text = str(text or "").strip()
        if not text:
            raise TTSError("texto vazio para TTS")

        body: dict[str, Any] = {
            "model": self.model,
            "voice": str(voice or self.default_voice),
            "input": text,
            "response_format": "wav",
            "speed": self.speed,
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
            raise TTSError(f"falha no OpenAI Voice: {exc}") from exc

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


def _selected_speed(cfg: dict, profile: dict) -> float:
    value = cfg.get("speed")
    if value in (None, ""):
        return float(profile["openai_speed"])
    return float(value)


def _build_openai(cfg: dict, profile: dict) -> OpenAITTSProvider:
    api = dict(cfg.get("openai") or cfg.get("api") or {})
    return OpenAITTSProvider(
        api_key=get_secret(
            str(api.get("api_key_env") or "OPENAI_API_KEY")
        ),
        model=str(api.get("model") or "gpt-4o-mini-tts"),
        default_voice=str(
            cfg.get("voice_override")
            or api.get("voice_override")
            or profile["openai_voice"]
        ),
        base_url=str(
            api.get("base_url") or "https://api.openai.com/v1"
        ),
        timeout_seconds=float(api.get("timeout_seconds", 45)),
        instructions=str(
            api.get("instructions_override")
            or profile["openai_instructions"]
        ),
        speed=_selected_speed(cfg, profile),
        profile_label=profile["label"],
    )


def _build_elevenlabs(
    cfg: dict,
    profile: dict,
) -> ElevenLabsTTSProvider:
    api = dict(cfg.get("elevenlabs") or {})
    profile_ids = dict(api.get("voice_ids") or {})
    voice_id = str(
        api.get("voice_id_override")
        or profile_ids.get(profile["id"])
        or ""
    ).strip()
    return ElevenLabsTTSProvider(
        api_key=get_secret(
            str(api.get("api_key_env") or "ELEVENLABS_API_KEY")
        ),
        voice_id=voice_id,
        model=str(
            api.get("model") or "eleven_v3_conversational"
        ),
        base_url=str(
            api.get("base_url") or "https://api.elevenlabs.io/v1"
        ),
        timeout_seconds=float(api.get("timeout_seconds", 45)),
        speed=_selected_speed(cfg, profile),
        stability=float(api.get("stability", 0.45)),
        similarity_boost=float(api.get("similarity_boost", 0.80)),
        style=float(api.get("style", 0.20)),
        use_speaker_boost=bool(api.get("use_speaker_boost", True)),
    )


def build_tts_provider(config: dict | None = None) -> TTSProvider:
    config = dict(config or {})
    cfg = dict(config.get("tts") or config)
    provider = str(cfg.get("provider") or "openai").casefold()
    profile = get_voice_profile(cfg.get("profile"))

    if provider in {"openai", "neural", "premium"}:
        return _build_openai(cfg, profile)

    if provider in {"elevenlabs", "eleven"}:
        return _build_elevenlabs(cfg, profile)

    if provider in {"neural_auto", "auto"}:
        errors = []
        try:
            primary = _build_openai(cfg, profile)
        except Exception as exc:
            primary = None
            errors.append(str(exc))
        try:
            fallback = _build_elevenlabs(cfg, profile)
        except Exception as exc:
            fallback = None
            errors.append(str(exc))

        if primary and fallback:
            return FallbackTTSProvider(primary, fallback)
        if primary:
            return primary
        if fallback:
            return fallback
        raise TTSError(
            "Nenhum motor neural configurado. " + " | ".join(errors)
        )

    if provider in {"local_legacy", "pyttsx3", "windows"}:
        local_cfg = dict(cfg.get("local_legacy") or {})
        return LocalPyttsx3TTSProvider(
            rate=int(
                local_cfg.get("rate")
                or profile["local_rate"]
            ),
            volume=float(local_cfg.get("volume", 1.0)),
            preferred_voice_keywords=profile["local_keywords"],
            profile_label=profile["label"],
        )

    raise ValueError(f"TTS provider desconhecido: {provider}")

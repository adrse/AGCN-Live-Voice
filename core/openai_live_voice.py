"""OpenAI GPT-Live voice renderer for AGCN Live Voice.

Strict mode keeps AGCN in control:
- Presenter/Brain decides and validates WHAT to say;
- GPT-Live only performs the approved speech;
- returned transcript is checked before any audio reaches AudioSink;
- any mismatch/error raises and the outer fallback uses Qwen HQ/Kokoro.

This first implementation intentionally opens one short Live session per speech.
That avoids cross-turn prompt contamination and gives us deterministic lifecycle
control. A persistent full-duplex session can be added later for guided-agent
mode without changing the presenter scheduler.
"""

from __future__ import annotations

import base64
import json
import re
import time
import unicodedata
from typing import Any, Callable

import requests

from core.integration_contracts import AudioChunk
from core.voice_expression import build_voice_instructions
from core.voice_profiles import get_voice_profile


OPENAI_LIVE_PROFILE_VOICES = {
    "female_fast": "marin",
    "male_fast": "cedar",
}


class OpenAILiveVoiceError(RuntimeError):
    pass


def _normalize_transcript(text: str) -> str:
    text = unicodedata.normalize("NFKD", str(text or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.casefold()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


class OpenAILiveVoiceProvider:
    """GPT-Live 1 used as a controlled, expressive speech renderer."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "gpt-live-1",
        profile_id: str = "female_fast",
        voice_override: str = "",
        websocket_url: str = "wss://api.openai.com/v1/live/sessions",
        models_base_url: str = "https://api.openai.com/v1",
        timeout_seconds: float = 45,
        startup_timeout_seconds: float = 12,
        completion_grace_seconds: float = 0.70,
        expressive: bool = True,
        expression_strength: float = 1.0,
        ws_factory: Callable[..., Any] | None = None,
        session=None,
    ) -> None:
        self.api_key = str(api_key or "").strip()
        self.model = str(model or "gpt-live-1").strip()
        self.profile_id = (
            profile_id
            if profile_id in OPENAI_LIVE_PROFILE_VOICES
            else "female_fast"
        )
        self.voice = str(
            voice_override
            or OPENAI_LIVE_PROFILE_VOICES[self.profile_id]
        ).strip()
        self.websocket_url = str(websocket_url or "").strip()
        self.models_base_url = str(models_base_url or "").rstrip("/")
        self.timeout_seconds = float(timeout_seconds)
        self.startup_timeout_seconds = float(startup_timeout_seconds)
        self.completion_grace_seconds = max(
            0.0, float(completion_grace_seconds)
        )
        self.expressive = bool(expressive)
        self.expression_strength = max(
            0.0, min(1.5, float(expression_strength))
        )
        profile = get_voice_profile(self.profile_id)
        self.base_instructions = str(
            profile.get("openai_instructions")
            or profile.get("qwen_style")
            or ""
        ).strip()
        self.active_style = "sales_energy"
        self.active_instructions = self.base_instructions
        self.last_transcript = ""
        self.last_exact_match = False
        self.ws_factory = ws_factory
        self.session = session or requests.Session()

    @property
    def name(self) -> str:
        return f"OpenAI Live/{self.model}/{self.voice}/strict"

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

    def healthcheck(self) -> tuple[bool, str]:
        if not self.api_key:
            return False, "OPENAI_API_KEY não configurada"
        try:
            response = self.session.get(
                f"{self.models_base_url}/models/{self.model}",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=min(self.timeout_seconds, 8.0),
            )
            response.raise_for_status()
            return (
                True,
                f"OpenAI Live pronto; modelo={self.model}; "
                f"voz={self.voice}; modo=strict_speech.",
            )
        except Exception as exc:
            return False, f"OpenAI Live indisponível: {exc}"

    def _connect(self):
        if not self.api_key:
            raise OpenAILiveVoiceError("OPENAI_API_KEY não configurada")

        if self.ws_factory is not None:
            return self.ws_factory(
                self.websocket_url,
                header={
                    "Authorization": f"Bearer {self.api_key}",
                },
                timeout=self.startup_timeout_seconds,
            )

        try:
            import websocket
        except ImportError as exc:
            raise OpenAILiveVoiceError(
                "websocket-client não instalado"
            ) from exc

        return websocket.create_connection(
            self.websocket_url,
            header={
                "Authorization": f"Bearer {self.api_key}",
            },
            timeout=self.startup_timeout_seconds,
        )

    @staticmethod
    def _send(ws, payload: dict) -> None:
        ws.send(json.dumps(payload, ensure_ascii=False))

    @staticmethod
    def _decode_event(raw: Any) -> dict:
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", errors="replace")
        if isinstance(raw, dict):
            return raw
        try:
            payload = json.loads(str(raw))
        except Exception as exc:
            raise OpenAILiveVoiceError(
                "evento inválido recebido do OpenAI Live"
            ) from exc
        return payload if isinstance(payload, dict) else {}

    @staticmethod
    def _is_timeout(exc: Exception) -> bool:
        name = exc.__class__.__name__.casefold()
        return isinstance(exc, TimeoutError) or "timeout" in name

    def _receive_until_started(self, ws) -> None:
        deadline = time.monotonic() + self.startup_timeout_seconds
        while time.monotonic() < deadline:
            try:
                event = self._decode_event(ws.recv())
            except Exception as exc:
                if self._is_timeout(exc):
                    continue
                raise OpenAILiveVoiceError(
                    f"falha ao iniciar sessão OpenAI Live: {exc}"
                ) from exc

            kind = str(event.get("type") or "")
            if kind == "session.started":
                return
            if kind == "error":
                error = event.get("error") or {}
                raise OpenAILiveVoiceError(
                    str(error.get("message") or "erro do OpenAI Live")
                )

        raise OpenAILiveVoiceError(
            "OpenAI Live não confirmou session.started dentro do limite"
        )

    def _strict_instruction(self, text: str) -> str:
        return (
            "AGCN STRICT SPEECH MODE. "
            "Immediately speak exactly one approved line in Brazilian "
            "Portuguese. Do not answer a question, explain, improvise, add, "
            "remove, reorder, summarize, repeat, or replace any word. "
            "After the approved line, remain silent. "
            f"Performance direction: {self.active_instructions}\n"
            "APPROVED_SPEECH_BEGIN\n"
            f"{text}\n"
            "APPROVED_SPEECH_END"
        )

    @staticmethod
    def _silence_event() -> dict:
        # 20 ms of mono PCM16 silence at 24 kHz.
        silence = b"\x00\x00" * 480
        return {
            "type": "session.input_audio.append",
            "audio": base64.b64encode(silence).decode("ascii"),
        }

    def _collect_strict_audio(self, ws, expected_text: str) -> AudioChunk:
        expected = _normalize_transcript(expected_text)
        transcript_parts: list[str] = []
        audio_parts: list[bytes] = []
        started_audio = False
        transcript_matches = False
        last_audio_at = 0.0
        last_silence_at = 0.0
        deadline = time.monotonic() + self.timeout_seconds

        settimeout = getattr(ws, "settimeout", None)
        if callable(settimeout):
            try:
                settimeout(0.10)
            except Exception:
                pass

        while time.monotonic() < deadline:
            now = time.monotonic()
            if now - last_silence_at >= 0.05:
                try:
                    self._send(ws, self._silence_event())
                except Exception as exc:
                    raise OpenAILiveVoiceError(
                        f"falha enviando silêncio ao OpenAI Live: {exc}"
                    ) from exc
                last_silence_at = now

            try:
                raw = ws.recv()
            except Exception as exc:
                if not self._is_timeout(exc):
                    raise OpenAILiveVoiceError(
                        f"falha recebendo áudio do OpenAI Live: {exc}"
                    ) from exc

                if (
                    started_audio
                    and transcript_matches
                    and (
                        time.monotonic() - last_audio_at
                        >= self.completion_grace_seconds
                    )
                ):
                    break
                continue

            event = self._decode_event(raw)
            kind = str(event.get("type") or "")

            if kind == "session.output_audio.delta":
                delta = str(event.get("delta") or "")
                if delta:
                    try:
                        audio_parts.append(base64.b64decode(delta))
                    except Exception as exc:
                        raise OpenAILiveVoiceError(
                            "OpenAI Live retornou áudio base64 inválido"
                        ) from exc
                    started_audio = True
                    last_audio_at = time.monotonic()

            elif kind == "session.output_transcript.delta":
                transcript_parts.append(str(event.get("delta") or ""))
                transcript_matches = (
                    _normalize_transcript("".join(transcript_parts))
                    == expected
                )
                if (
                    started_audio
                    and transcript_matches
                    and self.completion_grace_seconds <= 0
                ):
                    break

            elif kind == "error":
                error = event.get("error") or {}
                raise OpenAILiveVoiceError(
                    str(error.get("message") or "erro do OpenAI Live")
                )

            elif kind == "session.closed":
                break

        transcript = "".join(transcript_parts).strip()
        self.last_transcript = transcript
        self.last_exact_match = (
            bool(transcript)
            and _normalize_transcript(transcript) == expected
        )

        if not audio_parts:
            raise OpenAILiveVoiceError(
                "OpenAI Live não retornou áudio"
            )
        if not self.last_exact_match:
            raise OpenAILiveVoiceError(
                "OpenAI Live alterou a fala aprovada; áudio bloqueado "
                "e fallback local será usado"
            )

        return AudioChunk(
            data=b"".join(audio_parts),
            sample_rate=24000,
            channels=1,
            sample_width=2,
            format="pcm_s16le",
        )

    def synthesize(
        self,
        text: str,
        *,
        voice: str | None = None,
    ) -> AudioChunk:
        text = str(text or "").strip()
        if not text:
            raise OpenAILiveVoiceError("texto vazio para voz OpenAI Live")

        selected_voice = str(voice or self.voice).strip()
        ws = self._connect()
        try:
            self._send(
                ws,
                {
                    "type": "session.start",
                    "event_id": "agcn_session_start",
                    "session": {
                        "model": self.model,
                        "instructions": (
                            "You are the vocal performance layer of AGCN Live "
                            "Voice. The AGCN application owns all decisions, "
                            "facts, sales tactics, queueing and turn order. "
                            "Never initiate a topic or invent content. Only "
                            "speak when the application sends an instruction "
                            "containing APPROVED_SPEECH_BEGIN/END, and render "
                            "that exact approved line once."
                        ),
                        "input": [],
                        "audio": {
                            "format": {
                                "type": "audio/pcm",
                                "rate": 24000,
                            },
                            "output": {
                                "voice": selected_voice,
                            },
                        },
                        "delegation": None,
                        "store": False,
                    },
                },
            )
            self._receive_until_started(ws)

            # GPT-Live is full-duplex. Feed a small amount of silent microphone
            # audio while asking it to perform the already-approved line.
            self._send(ws, self._silence_event())
            self._send(
                ws,
                {
                    "type": "session.instructions.append",
                    "event_id": "agcn_strict_speech",
                    "delegation_id": None,
                    "content": self._strict_instruction(text),
                },
            )

            chunk = self._collect_strict_audio(ws, text)

            try:
                self._send(ws, {"type": "session.close"})
            except Exception:
                pass
            return chunk
        finally:
            try:
                ws.close()
            except Exception:
                pass

    def close(self) -> None:
        # Sessions are intentionally short-lived in strict mode.
        return None

import base64
import json

import pytest

from core.openai_live_voice import (
    OpenAILiveVoiceError,
    OpenAILiveVoiceProvider,
    _normalize_transcript,
)
from core.tts_providers import FallbackTTSProvider, build_tts_provider


class FakeResponse:
    def __init__(self, status_code=200):
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"http {self.status_code}")


class FakeHTTPSession:
    def get(self, *args, **kwargs):
        return FakeResponse()


class FakeWebSocket:
    def __init__(self, events):
        self.events = list(events)
        self.sent = []
        self.closed = False
        self.timeout = None

    def send(self, raw):
        self.sent.append(json.loads(raw))

    def recv(self):
        if self.events:
            return json.dumps(self.events.pop(0))
        raise TimeoutError("fake timeout")

    def settimeout(self, value):
        self.timeout = value

    def close(self):
        self.closed = True


def test_normalize_transcript_ignores_case_accents_and_punctuation():
    assert (
        _normalize_transcript("Atenção: promoção!")
        == _normalize_transcript("ATENCAO promocao")
    )


def test_openai_live_strict_renders_only_validated_transcript():
    pcm = b"\x01\x00" * 240
    encoded = base64.b64encode(pcm).decode("ascii")
    fake = FakeWebSocket([
        {"type": "session.started", "session": {"id": "sess_1"}},
        {
            "type": "session.instructions.appended",
            "client_event_id": "agcn_strict_speech",
        },
        {"type": "session.output_audio.delta", "delta": encoded},
        {
            "type": "session.output_transcript.delta",
            "delta": "Oferta confirmada!",
            "start_ms": 0,
            "end_ms": 300,
        },
    ])

    provider = OpenAILiveVoiceProvider(
        api_key="test-key",
        profile_id="female_fast",
        completion_grace_seconds=0,
        ws_factory=lambda *args, **kwargs: fake,
        session=FakeHTTPSession(),
    )
    provider.configure_for_job({
        "type": "proactive",
        "topic": "price_value",
        "tactic": "price_anchor",
    })

    chunk = provider.synthesize("Oferta confirmada!")

    assert chunk.sample_rate == 24000
    assert chunk.channels == 1
    assert chunk.sample_width == 2
    assert chunk.data == pcm
    assert provider.last_exact_match is True
    assert provider.last_transcript == "Oferta confirmada!"
    assert fake.closed is True

    start = fake.sent[0]
    assert start["type"] == "session.start"
    assert start["session"]["model"] == "gpt-live-1"
    assert start["session"]["audio"]["output"]["voice"] == "marin"
    assert start["session"]["delegation"] is None

    strict = next(
        event
        for event in fake.sent
        if event.get("type") == "session.instructions.append"
    )
    assert "APPROVED_SPEECH_BEGIN" in strict["content"]
    assert "Oferta confirmada!" in strict["content"]
    assert "price" in provider.active_style


def test_openai_live_blocks_changed_transcript_before_playback():
    pcm = b"\x01\x00" * 20
    fake = FakeWebSocket([
        {"type": "session.started", "session": {"id": "sess_2"}},
        {"type": "session.output_audio.delta", "delta": base64.b64encode(pcm).decode("ascii")},
        {
            "type": "session.output_transcript.delta",
            "delta": "Texto diferente",
            "start_ms": 0,
            "end_ms": 200,
        },
    ])
    provider = OpenAILiveVoiceProvider(
        api_key="test-key",
        timeout_seconds=0.01,
        completion_grace_seconds=0,
        ws_factory=lambda *args, **kwargs: fake,
        session=FakeHTTPSession(),
    )

    with pytest.raises(OpenAILiveVoiceError, match="fala aprovada"):
        provider.synthesize("Texto aprovado")

    assert provider.last_exact_match is False


def test_openai_live_healthcheck_requires_key():
    provider = OpenAILiveVoiceProvider(api_key="")
    ok, message = provider.healthcheck()
    assert ok is False
    assert "OPENAI_API_KEY" in message


def test_openai_live_provider_has_qwen_local_fallback(monkeypatch):
    monkeypatch.setattr(
        "core.tts_providers.get_secret",
        lambda name: "key" if name == "OPENAI_API_KEY" else "",
    )
    provider = build_tts_provider({
        "tts": {
            "provider": "openai_live",
            "profile": "female_fast",
            "openai_live": {
                "model": "gpt-live-1",
                "api_key_env": "OPENAI_API_KEY",
            },
        },
    })

    assert isinstance(provider, FallbackTTSProvider)
    assert "OpenAI Live/gpt-live-1" in provider.primary.name

import base64
import io
import wave

from core.gemini_tts import GeminiTTSProvider
from core.tts_providers import FallbackTTSProvider, build_tts_provider


def make_wav_bytes():
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(24000)
        wav.writeframes(b"\x00\x00" * 100)
    return buffer.getvalue()


class FakeResponse:
    def __init__(self, payload=None, status_code=200):
        self._payload = payload or {}
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"http {self.status_code}")

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, payload=None):
        self.payload = payload or {}
        self.posts = []
        self.gets = []

    def get(self, url, **kwargs):
        self.gets.append((url, kwargs))
        return FakeResponse({"name": "ok"})

    def post(self, url, **kwargs):
        self.posts.append((url, kwargs))
        return FakeResponse(self.payload)


def test_gemini_tts_uses_structured_speech_metadata_and_wav():
    audio = base64.b64encode(make_wav_bytes()).decode("ascii")
    session = FakeSession({
        "steps": [{
            "type": "model_output",
            "content": [{
                "type": "audio",
                "data": audio,
            }],
        }],
    })
    provider = GeminiTTSProvider(
        api_key="test-key",
        model="gemini-3.8-flash-lite-tts",
        profile_id="female_fast",
        speed=1.0,
        session=session,
    )
    provider.configure_for_job({
        "type": "proactive",
        "topic": "scarcity",
        "tactic": "grounded_scarcity",
    })

    chunk = provider.synthesize("Corre que essa condição está boa.")

    assert chunk.sample_rate == 24000
    assert chunk.data
    url, kwargs = session.posts[-1]
    assert url.endswith("/v1beta/interactions")
    body = kwargs["json"]
    assert body["model"] == "gemini-3.8-flash-lite-tts"
    content = body["input"][0]["content"][0]
    assert content["text"] == "Corre que essa condição está boa."
    annotation = content["annotations"][0]
    assert annotation["type"] == "speech_metadata"
    assert "urgency" in annotation["style"].casefold()
    assert body["generation_config"]["speech_config"][0]["voice"] == "Kore"


def test_gemini_healthcheck_reports_missing_key_without_network():
    provider = GeminiTTSProvider(api_key="")
    ok, message = provider.healthcheck()
    assert ok is False
    assert "GEMINI_API_KEY" in message


def test_gemini_provider_is_wrapped_with_local_fallback(monkeypatch):
    monkeypatch.setattr(
        "core.tts_providers.get_secret",
        lambda name: "key" if name == "GEMINI_API_KEY" else "",
    )
    provider = build_tts_provider({
        "tts": {
            "provider": "gemini_premium",
            "profile": "female_fast",
            "speed": 1.0,
            "gemini": {
                "model": "gemini-3.8-flash-lite-tts",
                "api_key_env": "GEMINI_API_KEY",
            },
        },
    })
    assert isinstance(provider, FallbackTTSProvider)
    assert "Gemini Premium TTS" in provider.primary.name

import io
import wave

from core.local_qwen3_tts import (
    CODEC_FILE,
    QWEN_PROFILE_SPEAKERS,
    TALKER_FILE,
    Qwen3HQLocalTTSProvider,
)
from core.tts_providers import FallbackTTSProvider, build_tts_provider


def make_wav():
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(24000)
        wav.writeframes(b"\x00\x00" * 100)
    return buffer.getvalue()


class FakeResponse:
    def __init__(self, *, status_code=200, payload=None, content=b""):
        self.status_code = status_code
        self._payload = payload or {}
        self.content = content

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self):
        self.posts = []

    def get(self, url, **kwargs):
        if url.endswith("/health"):
            return FakeResponse()
        if url.endswith("/v1/audio/voices"):
            return FakeResponse(
                payload={
                    "data": [
                        {"id": "vivian"},
                        {"id": "ryan"},
                    ]
                }
            )
        return FakeResponse()

    def post(self, url, **kwargs):
        self.posts.append((url, kwargs))
        return FakeResponse(content=make_wav())


def make_pack(tmp_path):
    pack = tmp_path / "voice_hq"
    (pack / "bin").mkdir(parents=True)
    (pack / "models").mkdir(parents=True)
    (pack / "bin" / "tts-server.exe").write_bytes(b"fake")
    (pack / "models" / TALKER_FILE).write_bytes(b"fake")
    (pack / "models" / CODEC_FILE).write_bytes(b"fake")
    return pack


def test_qwen_profiles_are_vivian_and_ryan():
    assert QWEN_PROFILE_SPEAKERS["female_fast"] == "vivian"
    assert QWEN_PROFILE_SPEAKERS["male_fast"] == "ryan"


def test_qwen_hq_sends_portuguese_and_selected_speaker(tmp_path):
    session = FakeSession()
    provider = Qwen3HQLocalTTSProvider(
        profile_id="male_fast",
        speed=1.0,
        pack_dir=make_pack(tmp_path),
        session=session,
    )

    ok, message = provider.healthcheck()
    assert ok is True
    assert "ryan" in message.casefold()

    chunk = provider.synthesize("Essa oferta está muito boa.")
    assert chunk.sample_rate == 24000

    _, kwargs = session.posts[0]
    body = kwargs["json"]
    assert body["voice"] == "ryan"
    assert body["language"] == "Portuguese"
    assert "Brazilian Portuguese" in body["instructions"]
    assert "live-commerce" in body["instructions"]
    assert body["response_format"] == "wav"


def test_factory_prefers_qwen_hq_and_keeps_kokoro_fallback():
    provider = build_tts_provider({
        "tts": {
            "provider": "qwen3_hq_auto",
            "profile": "female_fast",
            "speed": 1.28,
        }
    })
    assert isinstance(provider, FallbackTTSProvider)
    assert isinstance(provider.primary, Qwen3HQLocalTTSProvider)
    assert provider.primary.speaker == "vivian"
    assert "Kokoro" in provider.fallback.name

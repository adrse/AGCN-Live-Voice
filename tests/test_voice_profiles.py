import io
import wave

from core.local_kokoro_tts import (
    KokoroLocalTTSProvider,
    PROFILE_VOICES,
)
from core.neural_tts import ElevenLabsTTSProvider
from core.tts_providers import OpenAITTSProvider, build_tts_provider
from core.voice_profiles import get_voice_profile, list_voice_profiles


def wav_bytes():
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(24000)
        wav.writeframes(b"\x00\x00" * 100)
    return buffer.getvalue()


class FakeResponse:
    def __init__(self, *, content=b"", payload=None):
        self.content = content
        self._payload = payload or {}

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, *, raw_pcm=False):
        self.calls = []
        self.raw_pcm = raw_pcm

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return FakeResponse(
            content=(
                b"\x00\x00" * 100
                if self.raw_pcm
                else wav_bytes()
            )
        )

    def get(self, url, **kwargs):
        return FakeResponse(payload={"id": "model", "name": "Voice"})


def test_two_required_fast_voice_profiles_exist():
    profiles = {item["id"]: item for item in list_voice_profiles()}
    assert "female_fast" in profiles
    assert "male_fast" in profiles
    assert profiles["female_fast"]["default_speed"] > 1.0
    assert profiles["male_fast"]["default_speed"] > 1.0


def test_official_local_ptbr_voices_are_distinct():
    assert PROFILE_VOICES["female_fast"] == "pf_dora"
    assert PROFILE_VOICES["male_fast"] == "pm_alex"
    assert PROFILE_VOICES["female_fast"] != PROFILE_VOICES["male_fast"]


def test_default_tts_is_local_kokoro_without_api():
    provider = build_tts_provider({
        "tts": {
            "provider": "kokoro_local",
            "profile": "male_fast",
            "speed": 1.31,
        }
    })
    assert isinstance(provider, KokoroLocalTTSProvider)
    assert provider.voice_id == "pm_alex"
    assert provider.speed == 1.31


def test_kokoro_healthcheck_reports_missing_assets(tmp_path):
    provider = KokoroLocalTTSProvider(
        profile_id="female_fast",
        model_dir=tmp_path,
    )
    ok, detail = provider.healthcheck()
    assert ok is False
    assert "ausentes" in detail


def test_openai_tts_sends_speed_and_fast_sales_instructions():
    session = FakeSession()
    provider = OpenAITTSProvider(
        api_key="test",
        model="gpt-4o-mini-tts",
        default_voice="marin",
        speed=1.28,
        instructions="Fale rápido e com energia de vendas.",
        session=session,
    )
    chunk = provider.synthesize("Oferta rápida.")
    assert chunk.sample_rate == 24000

    _, kwargs = session.calls[0]
    body = kwargs["json"]
    assert body["voice"] == "marin"
    assert body["speed"] == 1.28
    assert "rápido" in body["instructions"]


def test_elevenlabs_tts_uses_pcm_and_clamps_speed():
    session = FakeSession(raw_pcm=True)
    provider = ElevenLabsTTSProvider(
        api_key="test",
        voice_id="voice-1",
        speed=1.50,
        session=session,
    )
    chunk = provider.synthesize("Oferta rápida.")
    assert chunk.sample_rate == 24000
    assert chunk.format == "pcm_s16le"

    _, kwargs = session.calls[0]
    assert kwargs["params"]["output_format"] == "pcm_24000"
    assert kwargs["json"]["voice_settings"]["speed"] == 1.2

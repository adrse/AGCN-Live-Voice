import io
import wave

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
    def __init__(self):
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return FakeResponse(content=wav_bytes())

    def get(self, url, **kwargs):
        return FakeResponse(payload={"id": "model"})


def test_two_required_fast_voice_profiles_exist():
    profiles = {item["id"]: item for item in list_voice_profiles()}
    assert "female_fast" in profiles
    assert "male_fast" in profiles
    assert profiles["female_fast"]["local_rate"] >= 220
    assert profiles["male_fast"]["local_rate"] >= 220
    assert profiles["female_fast"]["openai_speed"] > 1.0
    assert profiles["male_fast"]["openai_speed"] > 1.0


def test_profiles_have_distinct_premium_base_voices():
    female = get_voice_profile("female_fast")
    male = get_voice_profile("male_fast")
    assert female["openai_voice"] != male["openai_voice"]
    assert "feminina" in female["openai_instructions"].casefold()
    assert "masculina" in male["openai_instructions"].casefold()


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


def test_local_factory_uses_selected_profile_rate():
    provider = build_tts_provider({
        "tts": {
            "provider": "local",
            "profile": "male_fast",
            "local": {"volume": 1.0},
        }
    })
    profile = get_voice_profile("male_fast")
    assert provider.rate == profile["local_rate"]
    assert provider.profile_label == profile["label"]

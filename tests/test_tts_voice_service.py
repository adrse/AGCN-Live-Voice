import io
import wave

from core.integration_contracts import AudioChunk
from core.tts_providers import FallbackTTSProvider, wav_bytes_to_chunk
from core.voice_service import VoiceService


def make_wav_bytes():
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(24000)
        wav.writeframes(b"\x00\x00" * 100)
    return buffer.getvalue()


class FakeTTS:
    def __init__(self, name="fake", error=None):
        self._name = name
        self.error = error
        self.calls = []

    @property
    def name(self):
        return self._name

    def healthcheck(self):
        return True, "ok"

    def synthesize(self, text, *, voice=None):
        self.calls.append((text, voice))
        if self.error:
            raise self.error
        return AudioChunk(
            data=b"\x00\x00" * 10,
            sample_rate=24000,
        )


class FakeSink:
    def list_devices(self):
        return ["fake"]

    def select_device(self, device_name):
        pass

    def play(self, chunk):
        pass

    def stop(self):
        pass


def test_wav_bytes_to_audio_chunk():
    chunk = wav_bytes_to_chunk(make_wav_bytes())
    assert chunk.sample_rate == 24000
    assert chunk.channels == 1
    assert chunk.sample_width == 2
    assert chunk.data


def test_fallback_tts_uses_local_when_primary_fails():
    premium = FakeTTS("premium", error=RuntimeError("down"))
    local = FakeTTS("local")
    provider = FallbackTTSProvider(premium, local)
    chunk = provider.synthesize("teste")
    assert chunk.sample_rate == 24000
    assert provider.last_provider == "local"


def test_voice_queue_prioritizes_reactive_over_proactive():
    service = VoiceService(FakeTTS(), FakeSink())
    service.enqueue(
        "fala proativa",
        priority=30,
        metadata={"type": "proactive"},
    )
    service.enqueue(
        "resposta de compra",
        priority=98,
        metadata={"type": "reactive"},
    )

    first = service.queue.get_nowait()
    assert first.text == "resposta de compra"

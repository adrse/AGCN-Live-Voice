"""Motor de voz local de alta qualidade do AGCN.

Qwen3-TTS 1.7B CustomVoice via qwentts.cpp/GGML.
- roda totalmente local;
- não usa API externa;
- mantém o modelo quente em um servidor localhost;
- Vivian = perfil feminino;
- Ryan = perfil masculino;
- Kokoro fica como fallback em máquinas sem o pacote HQ.
"""

from __future__ import annotations

import io
import os
import subprocess
import sys
import tempfile
import time
import wave
from pathlib import Path

import requests

from core.integration_contracts import AudioChunk
from core.voice_profiles import get_voice_profile


QWEN_PROFILE_SPEAKERS = {
    "female_fast": "vivian",
    "male_fast": "ryan",
}

TALKER_FILE = "qwen-talker-1.7b-customvoice-Q8_0.gguf"
CODEC_FILE = "qwen-tokenizer-12hz-Q8_0.gguf"


def _resource_root() -> Path:
    frozen = getattr(sys, "_MEIPASS", None)
    if frozen:
        return Path(frozen)
    return Path(__file__).resolve().parents[1]


def _local_appdata() -> Path:
    base = os.getenv("LOCALAPPDATA") or os.getenv("APPDATA")
    if base:
        return Path(base) / "AGCN Live Voice"
    return Path.home() / ".agcn-live-voice"


def default_hq_pack_dir() -> Path:
    bundled = _resource_root() / "voice_hq"
    if bundled.exists():
        return bundled
    return _local_appdata() / "voice_hq"


def _wav_bytes_to_chunk(data: bytes) -> AudioChunk:
    with wave.open(io.BytesIO(data), "rb") as wav:
        channels = wav.getnchannels()
        sample_width = wav.getsampwidth()
        sample_rate = wav.getframerate()
        frames = wav.readframes(wav.getnframes())

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
    """Ajusta velocidade preservando pitch via FFmpeg atempo."""
    speed = max(0.80, min(1.60, float(speed)))
    if abs(speed - 1.0) < 0.01:
        return chunk

    ffmpeg = _ffmpeg_exe()
    if not ffmpeg:
        return chunk

    with tempfile.TemporaryDirectory(prefix="agcn_voice_speed_") as tmp:
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


class Qwen3HQLocalTTSProvider:
    """Qwen3-TTS 1.7B local, usando servidor GGML residente."""

    def __init__(
        self,
        *,
        profile_id: str = "female_fast",
        speed: float = 1.28,
        pack_dir: str | Path | None = None,
        port: int = 18765,
        startup_timeout_seconds: float = 120,
        request_timeout_seconds: float = 60,
        session=None,
    ) -> None:
        self.profile_id = (
            profile_id
            if profile_id in QWEN_PROFILE_SPEAKERS
            else "female_fast"
        )
        self.speaker = QWEN_PROFILE_SPEAKERS[self.profile_id]
        self.instructions = str(
            get_voice_profile(self.profile_id).get("qwen_style") or ""
        ).strip()
        self.speed = max(0.80, min(1.60, float(speed)))
        self.pack_dir = (
            Path(pack_dir) if pack_dir else default_hq_pack_dir()
        ).expanduser().resolve()
        self.bin_dir = self.pack_dir / "bin"
        self.models_dir = self.pack_dir / "models"
        self.server_exe = self.bin_dir / "tts-server.exe"
        self.talker_path = self.models_dir / TALKER_FILE
        self.codec_path = self.models_dir / CODEC_FILE
        self.port = int(port)
        self.base_url = f"http://127.0.0.1:{self.port}"
        self.startup_timeout_seconds = float(startup_timeout_seconds)
        self.request_timeout_seconds = float(request_timeout_seconds)
        self.session = session or requests.Session()
        self.process: subprocess.Popen | None = None

    @property
    def name(self) -> str:
        label = (
            "Feminina — Vivian"
            if self.profile_id == "female_fast"
            else "Masculina — Ryan"
        )
        return f"AGCN Qwen3-TTS 1.7B HQ / {label}"

    def assets_status(self) -> tuple[bool, str]:
        missing = [
            path
            for path in (
                self.server_exe,
                self.talker_path,
                self.codec_path,
            )
            if not path.exists()
        ]
        if missing:
            names = ", ".join(str(path) for path in missing)
            return False, f"Voice Pack HQ ausente/incompleto: {names}"
        return True, f"Voice Pack HQ instalado em {self.pack_dir}"

    def _server_healthy(self) -> bool:
        try:
            response = self.session.get(
                f"{self.base_url}/health",
                timeout=1.5,
            )
            return int(response.status_code) == 200
        except Exception:
            return False

    def _start_server(self) -> None:
        if self._server_healthy():
            return

        ok, message = self.assets_status()
        if not ok:
            raise RuntimeError(message)

        flags = 0
        if os.name == "nt":
            flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

        env = os.environ.copy()
        env.setdefault("GGML_BACKEND", "")

        self._stderr_path = (
            _local_appdata() / "logs" / "qwen3-tts-server.log"
        )
        self._stderr_path.parent.mkdir(parents=True, exist_ok=True)
        self._stderr_handle = self._stderr_path.open("ab")

        self.process = subprocess.Popen(
            [
                str(self.server_exe),
                "--model",
                str(self.talker_path),
                "--codec",
                str(self.codec_path),
                "--alias",
                "agcn-qwen3-tts-hq",
                "--host",
                "127.0.0.1",
                "--port",
                str(self.port),
                "--lang",
                "Portuguese",
            ],
            cwd=str(self.bin_dir),
            stdout=subprocess.DEVNULL,
            stderr=self._stderr_handle,
            creationflags=flags,
            env=env,
        )

        deadline = time.monotonic() + self.startup_timeout_seconds
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                try:
                    self._stderr_handle.flush()
                    tail = self._stderr_path.read_text(
                        encoding="utf-8",
                        errors="replace",
                    )[-2000:]
                except Exception:
                    tail = ""
                raise RuntimeError(
                    "Qwen3-TTS local encerrou ao iniciar "
                    f"(code={self.process.returncode}). "
                    f"Log: {tail.strip()}"
                )
            if self._server_healthy():
                return
            time.sleep(0.5)

        self.close()
        raise RuntimeError(
            "Qwen3-TTS local não ficou pronto dentro do tempo limite"
        )

    def healthcheck(self) -> tuple[bool, str]:
        try:
            ok, message = self.assets_status()
            if not ok:
                return False, message
            self._start_server()
            response = self.session.get(
                f"{self.base_url}/v1/audio/voices",
                timeout=5,
            )
            response.raise_for_status()
            payload = response.json()
            raw = payload.get("data") if isinstance(payload, dict) else payload
            voices = set()
            for item in raw or []:
                if isinstance(item, str):
                    voices.add(item.casefold())
                elif isinstance(item, dict):
                    voices.add(
                        str(
                            item.get("id")
                            or item.get("name")
                            or item.get("voice")
                            or ""
                        ).casefold()
                    )
            if voices and self.speaker.casefold() not in voices:
                return False, (
                    f"Qwen3-TTS carregou, mas speaker {self.speaker!r} "
                    "não apareceu na lista do modelo"
                )
            return True, (
                f"Qwen3-TTS 1.7B HQ pronto; speaker={self.speaker}; "
                f"Portuguese; velocidade={self.speed:.2f}x"
            )
        except Exception as exc:
            return False, f"Qwen3-TTS HQ indisponível: {exc}"

    def synthesize(
        self,
        text: str,
        *,
        voice: str | None = None,
    ) -> AudioChunk:
        text = str(text or "").strip()
        if not text:
            raise ValueError("texto vazio para TTS")

        self._start_server()
        speaker = str(voice or self.speaker).strip().casefold()

        response = self.session.post(
            f"{self.base_url}/v1/audio/speech",
            json={
                "model": "agcn-qwen3-tts-hq",
                "input": text,
                "voice": speaker,
                "language": "Portuguese",
                "instructions": self.instructions,
                "response_format": "wav",
                "seed": 42,
                "temperature": 0.75,
                "top_p": 0.90,
                "repetition_penalty": 1.05,
            },
            timeout=self.request_timeout_seconds,
        )
        response.raise_for_status()

        chunk = _wav_bytes_to_chunk(bytes(response.content))
        return _adjust_speed(chunk, self.speed)

    def close(self) -> None:
        if self.process is None:
            return
        try:
            if self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=4)
                except subprocess.TimeoutExpired:
                    self.process.kill()
        finally:
            self.process = None
            handle = getattr(self, "_stderr_handle", None)
            if handle is not None:
                try:
                    handle.close()
                except Exception:
                    pass
                self._stderr_handle = None

"""TTS neural local do AGCN Live Voice.

Kokoro-82M + ONNX + eSpeak NG embarcados no pacote.
Não usa API e não depende das vozes instaladas no Windows.
"""

from __future__ import annotations

import sys
import threading
from pathlib import Path

import numpy as np

from core.integration_contracts import AudioChunk


PROFILE_VOICES = {
    "female_fast": "pf_dora",
    "male_fast": "pm_alex",
}


def _resource_root() -> Path:
    frozen = getattr(sys, "_MEIPASS", None)
    if frozen:
        return Path(frozen)
    return Path(__file__).resolve().parents[1]


def default_kokoro_dir() -> Path:
    return _resource_root() / "models" / "kokoro"


class KokoroLocalTTSProvider:
    """Kokoro neural PT-BR totalmente local."""

    def __init__(
        self,
        *,
        profile_id: str = "female_fast",
        speed: float = 1.28,
        model_dir: str | Path | None = None,
    ) -> None:
        self.profile_id = (
            profile_id
            if profile_id in PROFILE_VOICES
            else "female_fast"
        )
        self.voice_id = PROFILE_VOICES[self.profile_id]
        self.speed = max(0.70, min(2.0, float(speed)))
        self.model_dir = (
            Path(model_dir)
            if model_dir
            else default_kokoro_dir()
        )
        self.model_path = self.model_dir / "kokoro-v1.0.onnx"
        self.voices_path = self.model_dir / "voices-v1.0.bin"
        self._kokoro = None
        self._lock = threading.RLock()

    @property
    def name(self) -> str:
        label = (
            "Feminina — Dora"
            if self.profile_id == "female_fast"
            else "Masculina — Alex"
        )
        return f"AGCN Local Neural / Kokoro / {label}"

    def _check_assets(self) -> None:
        missing = [
            str(path)
            for path in (self.model_path, self.voices_path)
            if not path.exists()
        ]
        if missing:
            raise RuntimeError(
                "Arquivos da voz neural local ausentes: "
                + ", ".join(missing)
            )

    def _load(self) -> None:
        if self._kokoro is not None:
            return

        with self._lock:
            if self._kokoro is not None:
                return

            self._check_assets()

            import espeakng_loader
            from kokoro_onnx import EspeakConfig, Kokoro

            espeak_config = EspeakConfig(
                lib_path=espeakng_loader.get_library_path(),
                data_path=espeakng_loader.get_data_path(),
            )
            self._kokoro = Kokoro(
                str(self.model_path),
                str(self.voices_path),
                espeak_config=espeak_config,
            )

    def healthcheck(self) -> tuple[bool, str]:
        try:
            self._load()
            voices = set(self._kokoro.get_voices())
            required = {"pf_dora", "pm_alex"}
            if not required.issubset(voices):
                return (
                    False,
                    "Modelo Kokoro carregou, mas as vozes PT-BR "
                    "Dora/Alex não foram encontradas.",
                )
            return (
                True,
                f"Kokoro PT-BR local pronto; voz={self.voice_id}; "
                f"velocidade={self.speed:.2f}x.",
            )
        except Exception as exc:
            return False, f"Kokoro local indisponível: {exc}"

    def synthesize(
        self,
        text: str,
        *,
        voice: str | None = None,
    ) -> AudioChunk:
        text = str(text or "").strip()
        if not text:
            raise ValueError("texto vazio para TTS")

        self._load()
        voice_id = str(voice or self.voice_id).strip()

        with self._lock:
            samples, sample_rate = self._kokoro.create(
                text,
                voice=voice_id,
                speed=self.speed,
                lang="pt-br",
                trim=True,
                sentence_pause=0.12,
                clause_pause=0.05,
            )

        audio = np.asarray(samples, dtype=np.float32)
        if audio.size == 0:
            raise RuntimeError("Kokoro retornou áudio vazio")

        pcm = np.clip(audio, -1.0, 1.0)
        pcm = (pcm * 32767.0).astype(np.int16)

        return AudioChunk(
            data=pcm.tobytes(),
            sample_rate=int(sample_rate),
            channels=1,
            sample_width=2,
            format="pcm_s16le",
        )

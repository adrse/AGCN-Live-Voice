"""Saída de áudio do AGCN para speakers ou cabo virtual (VB-CABLE)."""

from __future__ import annotations

from typing import Sequence

from core.integration_contracts import AudioChunk


class AudioOutputError(RuntimeError):
    pass


class SoundDeviceAudioSink:
    def __init__(
        self,
        *,
        device_name: str = "",
        volume: float = 1.0,
    ) -> None:
        self.device_name = str(device_name or "")
        self.volume = max(0.0, min(1.0, float(volume)))
        self.device_index: int | None = None
        if self.device_name:
            self.select_device(self.device_name)

    @staticmethod
    def _modules():
        try:
            import numpy as np
            import sounddevice as sd
        except ImportError as exc:
            raise AudioOutputError(
                "numpy/sounddevice não instalados. "
                "Instale requirements-desktop.txt"
            ) from exc
        return np, sd

    def list_devices(self) -> Sequence[str]:
        _, sd = self._modules()
        devices = sd.query_devices()
        result = []
        for index, item in enumerate(devices):
            if int(item.get("max_output_channels") or 0) <= 0:
                continue
            result.append(f"{index}: {item.get('name', 'Audio')}")
        return result

    def select_device(self, device_name: str) -> None:
        _, sd = self._modules()
        target = str(device_name or "").strip()
        if not target:
            self.device_name = ""
            self.device_index = None
            return

        explicit_index = None
        prefix = target.split(":", 1)[0].strip()
        if prefix.isdigit():
            explicit_index = int(prefix)

        devices = sd.query_devices()
        candidates = []
        for index, item in enumerate(devices):
            if int(item.get("max_output_channels") or 0) <= 0:
                continue
            name = str(item.get("name") or "")
            if explicit_index == index:
                self.device_index = index
                self.device_name = name
                return
            if target.casefold() == name.casefold():
                self.device_index = index
                self.device_name = name
                return
            if target.casefold() in name.casefold():
                candidates.append((index, name))

        if len(candidates) == 1:
            self.device_index, self.device_name = candidates[0]
            return

        raise AudioOutputError(
            f"dispositivo de saída não encontrado/ambíguo: {target}"
        )

    def set_volume(self, volume: float) -> None:
        self.volume = max(0.0, min(1.0, float(volume)))

    def play(self, chunk: AudioChunk) -> None:
        np, sd = self._modules()

        if chunk.sample_width != 2:
            raise AudioOutputError(
                f"sample_width não suportado: {chunk.sample_width}"
            )

        data = np.frombuffer(chunk.data, dtype=np.int16)
        if chunk.channels > 1:
            if len(data) % chunk.channels:
                raise AudioOutputError("buffer PCM com canais inválidos")
            data = data.reshape((-1, chunk.channels))

        if self.volume != 1.0:
            scaled = data.astype(np.float32) * self.volume
            data = np.clip(scaled, -32768, 32767).astype(np.int16)

        sd.play(
            data,
            samplerate=chunk.sample_rate,
            device=self.device_index,
            blocking=True,
        )

    def stop(self) -> None:
        _, sd = self._modules()
        sd.stop()

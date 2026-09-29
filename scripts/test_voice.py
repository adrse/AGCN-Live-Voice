"""Teste manual da voz neural local e do dispositivo Windows.

Exemplos:
  python scripts/test_voice.py --list-devices
  python scripts/test_voice.py --profile female_fast
  python scripts/test_voice.py --profile male_fast --speed 1.35
  python scripts/test_voice.py --device "CABLE Input" --profile female_fast
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from core.audio_output import SoundDeviceAudioSink
from core.tts_providers import build_tts_provider


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "desktop" / "config.example.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument(
        "--profile",
        choices=["female_fast", "male_fast"],
    )
    parser.add_argument("--speed", type=float)
    parser.add_argument("--device", default="")
    parser.add_argument(
        "--text",
        default=(
            "Teste de voz do AGCN Live Voice. "
            "Essa apresentação é rápida, clara e funciona sem API."
        ),
    )
    parser.add_argument("--list-devices", action="store_true")
    args = parser.parse_args()

    config = json.loads(
        Path(args.config).read_text(encoding="utf-8")
    )
    tts_cfg = config.setdefault("tts", {})
    tts_cfg["provider"] = "kokoro_local"
    if args.profile:
        tts_cfg["profile"] = args.profile
    if args.speed is not None:
        tts_cfg["speed"] = args.speed

    sink = SoundDeviceAudioSink(
        volume=float(
            (config.get("audio") or {}).get("volume", 1.0)
        )
    )

    if args.list_devices:
        for item in sink.list_devices():
            print(item)
        return 0

    device = args.device or str(
        (config.get("audio") or {}).get("output_device") or ""
    )
    if device:
        sink.select_device(device)

    tts = build_tts_provider(config)
    ok, message = tts.healthcheck()
    print(f"TTS: {tts.name}")
    print(f"Healthcheck: {'OK' if ok else 'FALHOU'} - {message}")
    if not ok:
        return 2

    chunk = tts.synthesize(args.text)
    print(
        f"Áudio: {chunk.sample_rate} Hz, "
        f"{chunk.channels} canal(is), {len(chunk.data)} bytes PCM"
    )
    print(f"Saída: {sink.device_name or 'dispositivo padrão'}")
    sink.play(chunk)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

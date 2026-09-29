"""Teste manual de voz/dispositivo no Windows.

Exemplos:
  python scripts/test_voice.py --list-devices
  python scripts/test_voice.py --device "CABLE Input" --text "Teste da voz AGCN"
  python scripts/test_voice.py --provider openai --device "CABLE Input"
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
        "--provider",
        choices=["local", "openai"],
    )
    parser.add_argument("--device", default="")
    parser.add_argument("--voice", default="")
    parser.add_argument(
        "--text",
        default=(
            "Teste de voz do AGCN Live Voice. "
            "Essa fala deve chegar ao dispositivo selecionado."
        ),
    )
    parser.add_argument("--list-devices", action="store_true")
    args = parser.parse_args()

    config = json.loads(
        Path(args.config).read_text(encoding="utf-8")
    )
    if args.provider:
        config.setdefault("tts", {})["provider"] = args.provider

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

    chunk = tts.synthesize(
        args.text,
        voice=args.voice or (config.get("tts") or {}).get("voice") or None,
    )
    print(
        f"Áudio: {chunk.sample_rate} Hz, "
        f"{chunk.channels} canal(is), {len(chunk.data)} bytes PCM"
    )
    print(f"Saída: {sink.device_name or 'dispositivo padrão'}")
    sink.play(chunk)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

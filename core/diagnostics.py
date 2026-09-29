"""Diagnóstico do ambiente do AGCN Live Voice."""

from __future__ import annotations

import platform
import sys
from typing import Any

from core.audio_output import SoundDeviceAudioSink
from core.brain_factory import build_brain_provider
from core.local_qwen3_tts import Qwen3HQLocalTTSProvider
from core.product_store import ProductStore
from core.secret_store import has_secret
from core.tts_providers import build_tts_provider
from core.voice_profiles import list_voice_profiles


def run_diagnostics(
    config: dict[str, Any],
    *,
    product_store: ProductStore | None = None,
) -> dict[str, Any]:
    store = product_store or ProductStore()
    checks: list[dict[str, Any]] = []

    def add(name: str, ok: bool, detail: str) -> None:
        checks.append({
            "name": name,
            "ok": bool(ok),
            "detail": str(detail),
        })

    add(
        "Windows",
        platform.system().casefold() == "windows",
        f"{platform.system()} {platform.release()}",
    )
    add(
        "Python",
        sys.version_info >= (3, 11),
        platform.python_version(),
    )

    active = store.active_for_presenter() or {}
    add(
        "Produto ativo",
        bool(active.get("name")),
        active.get("name") or "Nenhum produto ativo",
    )

    try:
        brain = build_brain_provider(config)
        ok, detail = brain.healthcheck()
        add("Presenter Brain", ok, detail)
        close_brain = getattr(brain, "close", None)
        if callable(close_brain):
            close_brain()
    except Exception as exc:
        add("Presenter Brain", False, str(exc))

    brain_cfg = dict(config.get("brain") or {})
    if str(brain_cfg.get("provider") or "").casefold() in {
        "openai",
        "openai_responses",
    }:
        add(
            "API da inteligência",
            has_secret("OPENAI_API_KEY"),
            (
                "Chave OpenAI disponível"
                if has_secret("OPENAI_API_KEY")
                else "Chave não configurada"
            ),
        )

    profiles = {item["id"] for item in list_voice_profiles()}
    add(
        "Duas vozes AGCN",
        {"female_fast", "male_fast"}.issubset(profiles),
        "Vivian (feminina) + Ryan (masculina) no Qwen3-TTS HQ; Dora/Alex no fallback",
    )

    tts_cfg = dict(config.get("tts") or {})
    hq_cfg = dict(tts_cfg.get("qwen3_hq") or {})
    try:
        hq = Qwen3HQLocalTTSProvider(
            profile_id=str(tts_cfg.get("profile") or "female_fast"),
            speed=float(tts_cfg.get("speed") or 1.28),
            pack_dir=hq_cfg.get("pack_dir") or None,
            port=int(hq_cfg.get("port", 18765)),
        )
        hq_ok, hq_detail = hq.assets_status()
        add("Voice Pack HQ", hq_ok, hq_detail)
    except Exception as exc:
        add("Voice Pack HQ", False, str(exc))

    try:
        tts = build_tts_provider(config)
        ok, detail = tts.healthcheck()
        add("Motor de voz local", ok, detail)
    except Exception as exc:
        add("Motor de voz local", False, str(exc))

    try:
        sink = SoundDeviceAudioSink()
        devices = list(sink.list_devices())
        add(
            "Dispositivos de áudio",
            bool(devices),
            f"{len(devices)} saída(s) encontrada(s)",
        )
        cable = [
            item for item in devices
            if "cable" in item.casefold()
            or "vb-audio" in item.casefold()
        ]
        add(
            "VB-CABLE",
            bool(cable),
            cable[0] if cable else "Não detectado",
        )
    except Exception as exc:
        add("Dispositivos de áudio", False, str(exc))
        add("VB-CABLE", False, "Não foi possível verificar")

    required = [
        "Produto ativo",
        "Presenter Brain",
        "Duas vozes AGCN",
        "Voice Pack HQ",
        "Motor de voz local",
        "Dispositivos de áudio",
    ]
    by_name = {item["name"]: item for item in checks}
    ready = all(
        by_name.get(name, {}).get("ok")
        for name in required
    )

    return {
        "ready_for_live": ready,
        "checks": checks,
    }


def diagnostics_text(result: dict[str, Any]) -> str:
    lines = [
        "AGCN LIVE VOICE — DIAGNÓSTICO",
        "",
    ]
    for item in result.get("checks") or []:
        lines.append(
            f"{'OK' if item.get('ok') else 'PENDENTE'} - "
            f"{item.get('name')}: {item.get('detail')}"
        )
    lines += [
        "",
        (
            "PRONTO PARA TESTE DE LIVE"
            if result.get("ready_for_live")
            else "AINDA HÁ PENDÊNCIAS"
        ),
    ]
    return "\n".join(lines)

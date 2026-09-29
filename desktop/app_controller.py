"""Controller entre PySide6 e o core do AGCN Live Voice."""

from __future__ import annotations

from typing import Any

from core.audio_output import SoundDeviceAudioSink
from core.brain_factory import build_brain_provider
from core.diagnostics import diagnostics_text, run_diagnostics
from core.product_store import ProductStore
from core.runtime import AGCNVoiceRuntime
from core.secret_store import has_secret, set_secret
from core.tts_providers import build_tts_provider
from desktop.config_store import ConfigStore


class DesktopController:
    def __init__(self) -> None:
        self.config_store = ConfigStore()
        self.config = self.config_store.load()
        self.product_store = ProductStore()
        self.voice_init_error = ""
        self.runtime = self._build_runtime()

    def _build_runtime(self) -> AGCNVoiceRuntime:
        try:
            return AGCNVoiceRuntime(
                self.product_store,
                brain_config=self.config,
                voice_config=self.config,
            )
        except Exception as exc:
            # O programa deve abrir mesmo antes da primeira chave de voz.
            self.voice_init_error = str(exc)
            return AGCNVoiceRuntime(
                self.product_store,
                brain_config=self.config,
                voice_config=None,
            )

    def close(self) -> None:
        self.runtime.close()

    def snapshot(self) -> dict:
        return self.runtime.snapshot()

    def start_live(self, username: str) -> dict:
        return self.runtime.start(username)

    def stop_live(self) -> dict:
        return self.runtime.stop()

    def products(self) -> list[dict]:
        return self.product_store.list()

    def active_product(self) -> dict | None:
        return self.product_store.active()

    def save_product(
        self,
        payload: dict[str, Any],
        *,
        product_id: str | None = None,
        activate: bool = True,
    ) -> dict:
        manual_fields = [
            key
            for key, value in payload.items()
            if value not in (None, "", False)
        ]
        if product_id:
            result = self.runtime.update_product(
                product_id,
                {
                    **payload,
                    "manual_fields": manual_fields,
                },
            )
        else:
            result = self.runtime.add_product({
                **payload,
                "manual_fields": manual_fields,
            })

        product = result["product"]
        if activate and product.get("id"):
            self.runtime.activate_product(product["id"])
        return product

    def activate_product(self, product_id: str) -> dict:
        return self.runtime.activate_product(product_id)

    def delete_product(self, product_id: str) -> dict:
        return self.runtime.delete_product(product_id)

    def save_settings(
        self,
        patch: dict[str, Any],
        *,
        openai_key: str | None = None,
        gemini_key: str | None = None,
        elevenlabs_key: str | None = None,
    ) -> dict:
        if openai_key is not None:
            set_secret("OPENAI_API_KEY", openai_key)
        if gemini_key is not None:
            set_secret("GEMINI_API_KEY", gemini_key)
        if elevenlabs_key is not None:
            set_secret("ELEVENLABS_API_KEY", elevenlabs_key)

        was_live = bool(
            self.runtime.snapshot().get("monitoring")
        )
        if was_live:
            self.runtime.stop()

        self.runtime.close()
        self.config = self.config_store.update(patch)
        self.voice_init_error = ""
        self.runtime = self._build_runtime()
        return self.config

    def set_openai_key(self, value: str) -> None:
        set_secret("OPENAI_API_KEY", value)

    def api_key_saved(self) -> bool:
        return has_secret("OPENAI_API_KEY")

    def set_gemini_key(self, value: str) -> None:
        set_secret("GEMINI_API_KEY", value)

    def gemini_key_saved(self) -> bool:
        return has_secret("GEMINI_API_KEY")

    def elevenlabs_key_saved(self) -> bool:
        return has_secret("ELEVENLABS_API_KEY")

    def brain_health(self) -> tuple[bool, str]:
        provider = build_brain_provider(self.config)
        try:
            return provider.healthcheck()
        finally:
            close = getattr(provider, "close", None)
            if callable(close):
                close()

    def diagnostics(self) -> tuple[bool, str]:
        result = run_diagnostics(
            self.config,
            product_store=self.product_store,
        )
        return bool(result.get("ready_for_live")), diagnostics_text(result)

    def list_audio_devices(self) -> list[str]:
        return list(SoundDeviceAudioSink().list_devices())

    def test_voice(
        self,
        *,
        text: str = "Teste de voz do AGCN Live Voice.",
        config_override: dict[str, Any] | None = None,
    ) -> tuple[bool, str]:
        try:
            config = dict(self.config)
            if config_override:
                config.update(config_override)

            tts = build_tts_provider(config)
            audio_cfg = dict(config.get("audio") or {})
            sink = SoundDeviceAudioSink(
                device_name=str(
                    audio_cfg.get("output_device") or ""
                ),
                volume=float(audio_cfg.get("volume", 1.0)),
            )
            tts_cfg = dict(config.get("tts") or {})
            hq_cfg = dict(tts_cfg.get("qwen3_hq") or {})
            style = str(
                tts_cfg.get("voice_style")
                or hq_cfg.get("voice_style")
                or "auto"
            )
            configure = getattr(tts, "configure_for_job", None)
            if callable(configure):
                configure({
                    "type": "proactive",
                    "topic": "benefits",
                    "tactic": "benefit_translation",
                    "voice_style": (
                        style if style not in {"", "auto"} else "sales_energy"
                    ),
                })

            chunk = tts.synthesize(
                text,
                voice=str(tts_cfg.get("voice_override") or "") or None,
            )
            sink.play(chunk)
            active = getattr(tts, "last_provider", "") or tts.name
            return True, f"Voz testada com {active}."
        except Exception as exc:
            return False, str(exc)

    def test_presenter(
        self,
        *,
        comment: str = "",
        user: str = "Cliente",
    ) -> dict:
        if comment.strip():
            return self.runtime.test_presenter_comment(
                user,
                comment,
            )
        return self.runtime.test_presenter_proactive()

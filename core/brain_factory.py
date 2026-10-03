"""Factory dos providers de Presenter Brain.

Configuração decide o transporte; PresenterPolicy e validação continuam iguais.
"""

from __future__ import annotations

from typing import Any

from core.brain_orchestrator import PresenterBrain
from core.integration_contracts import BrainContext, BrainProvider, BrainResult
from core.secret_store import get_secret
from core.local_llama_brain import LlamaCppLocalTransport
from core.model_transports import (
    OllamaTransport,
    OpenAICompatibleChatTransport,
    OpenAIResponsesTransport,
)


class FallbackBrainProvider:
    """Tenta provider premium e cai para o Brain local quando configurado."""

    def __init__(self, primary: BrainProvider, fallback: BrainProvider) -> None:
        self.primary = primary
        self.fallback = fallback
        self.last_provider = ""

    @property
    def name(self) -> str:
        return f"{self.primary.name} -> fallback {self.fallback.name}"

    def healthcheck(self) -> tuple[bool, str]:
        ok_primary, message_primary = self.primary.healthcheck()
        ok_fallback, message_fallback = self.fallback.healthcheck()
        ok = ok_primary or ok_fallback
        return (
            ok,
            f"primário: {message_primary} | fallback: {message_fallback}",
        )

    def close(self) -> None:
        for provider in (self.primary, self.fallback):
            close = getattr(provider, "close", None)
            if callable(close):
                try:
                    close()
                except Exception:
                    pass

    def generate(self, context: BrainContext) -> BrainResult:
        try:
            result = self.primary.generate(context)
            self.last_provider = self.primary.name
            return result
        except Exception as primary_error:
            try:
                result = self.fallback.generate(context)
                self.last_provider = self.fallback.name
                result.raw.setdefault(
                    "_agcn_fallback",
                    {
                        "from": self.primary.name,
                        "to": self.fallback.name,
                        "reason": str(primary_error),
                    },
                )
                return result
            except Exception as fallback_error:
                raise RuntimeError(
                    "Brain primário e fallback falharam. "
                    f"Primário: {primary_error}. "
                    f"Fallback: {fallback_error}."
                ) from fallback_error


def _brain_cfg(config: dict[str, Any] | None) -> dict[str, Any]:
    config = dict(config or {})
    return dict(config.get("brain") or config)


def _build_agcn_local(cfg: dict[str, Any], *, session=None) -> PresenterBrain:
    local = dict(cfg.get("local_brain") or {})
    return PresenterBrain(
        LlamaCppLocalTransport(
            pack_dir=local.get("pack_dir") or None,
            model_file=str(
                local.get("model_file")
                or "Qwen3-4B-Q4_K_M.gguf"
            ),
            lora_file=(
                local.get("lora_file")
                if "lora_file" in local
                else "AGCN-Presenter-v0.1-F16.gguf"
            ),
            require_lora=bool(local.get("require_lora", False)),
            model_alias=str(
                local.get("model_alias")
                or "agcn-presenter-v0.1"
            ),
            port=int(local.get("port", 18766)),
            context_size=int(local.get("context_size", 4096)),
            threads=local.get("threads") or None,
            startup_timeout_seconds=float(
                local.get("startup_timeout_seconds", 180)
            ),
            timeout_seconds=float(
                local.get("timeout_seconds")
                or cfg.get("timeout_seconds")
                or 45
            ),
            temperature=float(local.get("temperature", 0.25)),
            max_output_tokens=int(
                local.get("max_output_tokens", 500)
            ),
            session=session,
        ),
        max_retries=int(cfg.get("max_retries", 1)),
    )


def _build_ollama(cfg: dict[str, Any], *, session=None) -> PresenterBrain:
    ollama = dict(cfg.get("ollama") or {})
    base_url = (
        ollama.get("base_url")
        or cfg.get("ollama_url")
        or "http://127.0.0.1:11434"
    )
    model = ollama.get("model") or cfg.get("model") or "qwen3:4b"
    timeout = (
        ollama.get("timeout_seconds")
        or cfg.get("timeout_seconds")
        or 45
    )

    return PresenterBrain(
        OllamaTransport(
            base_url=base_url,
            model=model,
            timeout_seconds=timeout,
            temperature=ollama.get("temperature", 0.25),
            keep_alive=ollama.get("keep_alive", "10m"),
            session=session,
        ),
        max_retries=int(cfg.get("max_retries", 1)),
    )


def _build_openai(cfg: dict[str, Any], *, session=None) -> PresenterBrain:
    api = dict(cfg.get("api") or {})
    key_env = str(api.get("api_key_env") or "OPENAI_API_KEY")
    api_key = get_secret(key_env)

    return PresenterBrain(
        OpenAIResponsesTransport(
            api_key=api_key,
            model=str(api.get("model") or "gpt-6-luna"),
            base_url=str(
                api.get("base_url")
                or "https://api.openai.com/v1"
            ),
            timeout_seconds=float(
                api.get("timeout_seconds")
                or cfg.get("timeout_seconds")
                or 45
            ),
            max_output_tokens=int(api.get("max_output_tokens", 500)),
            session=session,
        ),
        max_retries=int(cfg.get("max_retries", 1)),
    )


def _build_compatible(cfg: dict[str, Any], *, session=None) -> PresenterBrain:
    api = dict(cfg.get("api") or {})
    key_env = str(api.get("api_key_env") or "AGCN_LLM_API_KEY")

    return PresenterBrain(
        OpenAICompatibleChatTransport(
            api_key=get_secret(key_env),
            model=str(api.get("model") or "").strip(),
            base_url=str(api.get("base_url") or "").strip(),
            timeout_seconds=float(
                api.get("timeout_seconds")
                or cfg.get("timeout_seconds")
                or 45
            ),
            temperature=float(api.get("temperature", 0.25)),
            session=session,
        ),
        max_retries=int(cfg.get("max_retries", 1)),
    )


def build_brain_provider(
    config: dict[str, Any] | None = None,
    *,
    session=None,
) -> BrainProvider:
    cfg = _brain_cfg(config)
    provider = str(cfg.get("provider") or "agcn_local").casefold()
    fallback_enabled = bool(cfg.get("fallback_local", True))

    if provider in {"agcn_local", "qwen_local", "local"}:
        return _build_agcn_local(cfg, session=session)

    if provider in {"ollama", "ollama_legacy"}:
        return _build_ollama(cfg, session=session)

    try:
        if provider in {"openai", "openai_responses"}:
            primary = _build_openai(cfg, session=session)
        elif provider in {"openai_compatible", "compatible", "api"}:
            primary = _build_compatible(cfg, session=session)
        else:
            raise ValueError(f"brain provider desconhecido: {provider}")
    except Exception:
        if fallback_enabled:
            return _build_agcn_local(cfg, session=session)
        raise

    if fallback_enabled:
        return FallbackBrainProvider(
            primary,
            _build_agcn_local(cfg, session=session),
        )

    return primary

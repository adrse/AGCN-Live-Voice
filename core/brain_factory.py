"""Factory dos providers de Presenter Brain.

Configuração decide o transporte; PresenterPolicy e validação continuam iguais.
"""

from __future__ import annotations

import os
from typing import Any

from core.brain_orchestrator import PresenterBrain
from core.integration_contracts import BrainContext, BrainProvider, BrainResult
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


def _build_local(cfg: dict[str, Any], *, session=None) -> PresenterBrain:
    ollama = dict(cfg.get("ollama") or {})
    base_url = (
        ollama.get("base_url")
        or cfg.get("ollama_url")
        or "http://127.0.0.1:11434"
    )
    model = (
        ollama.get("model")
        or cfg.get("model")
        or "qwen3:4b"
    )
    timeout = (
        ollama.get("timeout_seconds")
        or cfg.get("timeout_seconds")
        or 45
    )
    temperature = ollama.get("temperature", 0.25)
    keep_alive = ollama.get("keep_alive", "10m")

    transport = OllamaTransport(
        base_url=base_url,
        model=model,
        timeout_seconds=timeout,
        temperature=temperature,
        keep_alive=keep_alive,
        session=session,
    )
    return PresenterBrain(
        transport,
        max_retries=int(cfg.get("max_retries", 1)),
    )


def _build_openai(cfg: dict[str, Any], *, session=None) -> PresenterBrain:
    api = dict(cfg.get("api") or {})
    key_env = str(api.get("api_key_env") or "OPENAI_API_KEY")
    api_key = str(os.getenv(key_env) or "")
    model = str(api.get("model") or "gpt-6-luna")
    base_url = str(
        api.get("base_url")
        or "https://api.openai.com/v1"
    )
    timeout = float(
        api.get("timeout_seconds")
        or cfg.get("timeout_seconds")
        or 45
    )

    transport = OpenAIResponsesTransport(
        api_key=api_key,
        model=model,
        base_url=base_url,
        timeout_seconds=timeout,
        max_output_tokens=int(api.get("max_output_tokens", 500)),
        session=session,
    )
    return PresenterBrain(
        transport,
        max_retries=int(cfg.get("max_retries", 1)),
    )


def _build_compatible(cfg: dict[str, Any], *, session=None) -> PresenterBrain:
    api = dict(cfg.get("api") or {})
    key_env = str(api.get("api_key_env") or "AGCN_LLM_API_KEY")
    api_key = str(os.getenv(key_env) or "")
    model = str(api.get("model") or "").strip()
    base_url = str(api.get("base_url") or "").strip()

    transport = OpenAICompatibleChatTransport(
        api_key=api_key,
        model=model,
        base_url=base_url,
        timeout_seconds=float(
            api.get("timeout_seconds")
            or cfg.get("timeout_seconds")
            or 45
        ),
        temperature=float(api.get("temperature", 0.25)),
        session=session,
    )
    return PresenterBrain(
        transport,
        max_retries=int(cfg.get("max_retries", 1)),
    )


def build_brain_provider(
    config: dict[str, Any] | None = None,
    *,
    session=None,
) -> BrainProvider:
    cfg = _brain_cfg(config)
    provider = str(cfg.get("provider") or "qwen_local").casefold()

    if provider in {"qwen_local", "ollama", "local"}:
        return _build_local(cfg, session=session)

    if provider in {"openai", "openai_responses"}:
        primary = _build_openai(cfg, session=session)
    elif provider in {"openai_compatible", "compatible", "api"}:
        primary = _build_compatible(cfg, session=session)
    else:
        raise ValueError(f"brain provider desconhecido: {provider}")

    if bool(cfg.get("fallback_local", True)):
        return FallbackBrainProvider(
            primary,
            _build_local(cfg, session=session),
        )

    return primary

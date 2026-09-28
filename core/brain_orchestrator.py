"""Orquestrador provider-agnostic do Presenter Brain.

Qwen local e APIs premium passam por esta classe. Nenhum transporte tem permissão
para inventar o próprio prompt comercial ou mandar texto cru direto ao TTS.
"""

from __future__ import annotations

import json
from collections.abc import Callable

from core.integration_contracts import BrainContext, BrainResult, TextModelTransport
from core.presenter_policy import build_system_instruction, build_turn_payload


class BrainOutputError(RuntimeError):
    pass


Validator = Callable[[BrainResult, BrainContext], tuple[bool, str]]


def _strip_code_fence(text: str) -> str:
    value = str(text or "").strip()
    fence = chr(96) * 3
    if value.startswith(fence):
        lines = value.splitlines()
        if lines and lines[0].startswith(fence):
            lines = lines[1:]
        if lines and lines[-1].strip() == fence:
            lines = lines[:-1]
        value = "\n".join(lines).strip()
    return value


def _parse_result(raw_text: str) -> BrainResult:
    payload = json.loads(_strip_code_fence(raw_text))
    if not isinstance(payload, dict):
        raise BrainOutputError("resposta do Brain não é objeto JSON")

    speech = str(payload.get("speech") or "").strip()
    if not speech:
        raise BrainOutputError("campo speech vazio")

    used = payload.get("used_facts") or []
    if not isinstance(used, list):
        used = [str(used)]

    return BrainResult(
        speech=speech,
        topic=str(payload.get("topic") or "").strip(),
        used_facts=[str(x).strip() for x in used if str(x).strip()],
        needs_fact=bool(payload.get("needs_fact", False)),
        next_sales_thread=str(payload.get("next_sales_thread") or "").strip(),
        raw=payload,
    )


def validate_reported_facts(
    result: BrainResult,
    context: BrainContext,
) -> tuple[bool, str]:
    """Confere se fatos declarados pelo modelo pertencem à lista permitida.

    A validação semântica da fala continua sendo responsabilidade de SalesGuard
    / validador factual mais forte.
    """
    allowed = {
        str(x).strip().casefold()
        for x in context.allowed_facts
        if str(x).strip()
    }
    for fact in result.used_facts:
        if fact.casefold() not in allowed:
            return False, f"used_fact não autorizado: {fact}"
    return True, ""


class PresenterBrain:
    def __init__(
        self,
        transport: TextModelTransport,
        *,
        validators: list[Validator] | None = None,
        max_retries: int = 1,
    ) -> None:
        self.transport = transport
        self.validators = [validate_reported_facts, *(validators or [])]
        self.max_retries = max(0, int(max_retries))

    @property
    def name(self) -> str:
        return f"AGCN Presenter Brain / {self.transport.name}"

    def healthcheck(self) -> tuple[bool, str]:
        return self.transport.healthcheck()

    def generate(self, context: BrainContext) -> BrainResult:
        system_instruction = build_system_instruction()
        base_payload = build_turn_payload(context)
        last_error = ""

        for attempt in range(self.max_retries + 1):
            user_payload = base_payload
            if attempt and last_error:
                user_payload += (
                    "\n\nCORREÇÃO OBRIGATÓRIA: a resposta anterior foi rejeitada. "
                    f"Motivo: {last_error}. Gere novamente seguindo o schema e os fatos."
                )

            raw = self.transport.complete(
                system_instruction=system_instruction,
                user_payload=user_payload,
            )

            try:
                result = _parse_result(raw)
            except (json.JSONDecodeError, BrainOutputError) as exc:
                last_error = f"JSON inválido: {exc}"
                continue

            rejected = None
            for validator in self.validators:
                ok, reason = validator(result, context)
                if not ok:
                    rejected = reason or "falha de validação"
                    break

            if rejected is not None:
                last_error = rejected
                continue

            return result

        raise BrainOutputError(
            f"Brain falhou após {self.max_retries + 1} tentativa(s): {last_error}"
        )

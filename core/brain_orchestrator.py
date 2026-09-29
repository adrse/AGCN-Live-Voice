"""Orquestrador provider-agnostic do Presenter Brain.

Qwen local e APIs premium passam por esta classe. Nenhum transporte tem permissão
para inventar o próprio prompt comercial ou mandar texto cru direto ao TTS.
"""

from __future__ import annotations

import json
import re
import unicodedata
from collections.abc import Callable
from difflib import SequenceMatcher

from core.integration_contracts import BrainContext, BrainResult, TextModelTransport
from core.presenter_policy import build_system_instruction, build_turn_payload


class BrainOutputError(RuntimeError):
    pass


Validator = Callable[[BrainResult, BrainContext], tuple[bool, str]]


def _fold(text: str) -> str:
    value = unicodedata.normalize("NFKD", str(text or ""))
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return value.casefold()


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
    """Exige que used_facts seja subconjunto exato de ALLOWED_FACTS."""
    allowed = {
        str(x).strip().casefold()
        for x in context.allowed_facts
        if str(x).strip()
    }
    for fact in result.used_facts:
        if fact.casefold() not in allowed:
            return False, f"used_fact não autorizado: {fact}"
    return True, ""


def validate_sensitive_claims(
    result: BrainResult,
    context: BrainContext,
) -> tuple[bool, str]:
    """Segunda barreira para fatos comerciais de alto risco.

    O modelo pode esquecer de reportar um fato em used_facts. Para preço,
    desconto, estoque, frete, cupom, garantia e números explícitos, exigimos
    evidência também nos fatos reportados/autorizados. Respostas de ausência
    com needs_fact=true são permitidas sem fabricar o dado.
    """
    # Mesmo quando o modelo marca needs_fact, continuamos validando a fala.
    # A camada Presenter descarta esse resultado, mas nenhum número ou alegação
    # inventada recebe passe livre.
    speech = _fold(result.speech)
    reported = [_fold(x) for x in result.used_facts]
    allowed = [_fold(x) for x in context.allowed_facts]

    requirements = [
        (
            ("r$", " reais", "preco", "valor de"),
            ("preco atual:", "preco regular:"),
            "preço",
        ),
        (
            ("desconto", "%"),
            ("desconto:",),
            "desconto",
        ),
        (
            (
                "estoque",
                "restam",
                "resta ",
                "ultima unidade",
                "ultimas unidades",
                "poucas unidades",
                "ta acabando",
                "esta acabando",
                "esgot",
                "nao tem pra todo mundo",
            ),
            (
                "estoque:",
                "texto da oferta da live:",
                "observacao promocional:",
            ),
            "escassez/estoque",
        ),
        (
            ("frete", "entrega gratis", "frete gratis"),
            ("frete/entrega:",),
            "frete",
        ),
        (
            ("cupom",),
            ("cupom:",),
            "cupom",
        ),
        (
            ("garantia",),
            ("garantia:",),
            "garantia",
        ),
    ]

    for markers, prefixes, label in requirements:
        if not any(marker in speech for marker in markers):
            continue
        if not any(
            any(fact.startswith(prefix) for prefix in prefixes)
            for fact in reported
        ):
            return False, f"alegação de {label} sem used_fact correspondente"

    water_markers = (
        "ip67",
        "ip68",
        "impermeavel",
        "a prova d'agua",
        "resistente a agua",
        "resistencia a agua",
        " atm",
    )
    if any(marker in speech for marker in water_markers):
        if not any(
            any(marker in fact for marker in water_markers)
            for fact in allowed
        ):
            return False, "alegação de resistência à água sem fato autorizado"

    exclusivity_markers = (
        "exclusiva da live",
        "exclusivo da live",
        "so na live",
        "somente na live",
        "so aqui na live",
    )
    if any(marker in speech for marker in exclusivity_markers):
        if not any(
            fact.startswith("oferta ativa na live:")
            or fact.startswith("texto da oferta da live:")
            or fact.startswith("observacao promocional:")
            for fact in reported
        ):
            return False, "exclusividade da LIVE sem fato autorizado"

    # Números explícitos normalmente são especificação, preço, desconto,
    # estoque, medida ou autonomia. Se aparecem na fala, devem existir em algum
    # fato autorizado, inclusive em respostas marcadas needs_fact.
    allowed_numbers = {
        token.replace(".", ",")
        for fact in context.allowed_facts
        for token in re.findall(r"\d+(?:[.,]\d+)?", str(fact))
    }
    for token in re.findall(r"\d+(?:[.,]\d+)?", result.speech):
        normalized = token.replace(".", ",")
        if normalized not in allowed_numbers:
            return False, f"número não autorizado na fala: {token}"

    return True, ""


def validate_repetition(
    result: BrainResult,
    context: BrainContext,
) -> tuple[bool, str]:
    """Impede fala proativa quase igual à fala anterior.

    O prompt ajuda, mas esta barreira é determinística: se o modelo repetir
    abertura/estrutura muito parecida, pedimos outra formulação.
    """
    if context.mode != "proactive":
        return True, ""

    speech = _fold(result.speech)
    speech = re.sub(r"[^a-z0-9\s]", " ", speech)
    speech = re.sub(r"\s+", " ", speech).strip()
    if not speech:
        return True, ""

    current_words = speech.split()
    recent = list(context.recent_speeches or [])[-4:]

    for previous in reversed(recent):
        prev = _fold(previous)
        prev = re.sub(r"[^a-z0-9\s]", " ", prev)
        prev = re.sub(r"\s+", " ", prev).strip()
        if not prev:
            continue

        prev_words = prev.split()
        ratio = SequenceMatcher(None, speech, prev).ratio()

        current_set = {
            w for w in current_words
            if len(w) >= 4
        }
        previous_set = {
            w for w in prev_words
            if len(w) >= 4
        }
        union = current_set | previous_set
        jaccard = (
            len(current_set & previous_set) / len(union)
            if union else 0.0
        )

        same_opening = (
            len(current_words) >= 3
            and len(prev_words) >= 3
            and current_words[:3] == prev_words[:3]
        )

        if same_opening or ratio >= 0.72 or jaccard >= 0.78:
            return (
                False,
                "fala muito parecida com uma fala recente; "
                "mude a abertura, estrutura e ângulo comercial",
            )

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
        self.validators = [
            validate_reported_facts,
            validate_sensitive_claims,
            validate_repetition,
            *(validators or []),
        ]
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

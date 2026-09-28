"""Monta BrainContext exclusivamente a partir de fatos cadastrados.

Este módulo transforma o produto ativo + decisão + memória no pacote enviado
para qualquer LLM. Assim Qwen e API recebem a mesma fonte da verdade.
"""

from __future__ import annotations

from typing import Any, Iterable

from core.integration_contracts import (
    BrainContext,
    CommentPayload,
)
from core.product_profile import LIVE_FIELDS, PERMANENT_FIELDS


FACT_LABELS = {
    "product_url": "link do produto",
    "name": "nome",
    "brand": "marca",
    "model": "modelo",
    "category": "categoria",
    "description": "descrição",
    "key_benefits": "benefícios",
    "problems_solved": "problemas que resolve",
    "differentials": "diferenciais",
    "included_items": "itens inclusos",
    "compatibility": "compatibilidade",
    "size_info": "tamanho/medidas",
    "battery_info": "bateria/autonomia",
    "usage_info": "modo de uso",
    "warranty": "garantia",
    "limitations": "limitações",
    "additional_info": "informações adicionais",
    "regular_price": "preço regular",
    "current_price": "preço atual",
    "discount": "desconto",
    "stock": "estoque",
    "shipping_info": "frete/entrega",
    "coupon": "cupom",
    "live_offer": "oferta ativa na LIVE",
    "live_offer_text": "texto da oferta da LIVE",
    "promotion_note": "observação promocional",
}


def _present(value: Any) -> bool:
    return value not in (None, "", [], {})


def _format_value(field: str, value: Any) -> str:
    if field in {"regular_price", "current_price"}:
        try:
            return (
                f"R$ {float(value):,.2f}"
                .replace(",", "X")
                .replace(".", ",")
                .replace("X", ".")
            )
        except Exception:
            return str(value).strip()

    if field == "discount":
        try:
            return f"{float(value):g}%"
        except Exception:
            return str(value).strip()

    if field == "stock":
        try:
            return str(int(float(value)))
        except Exception:
            return str(value).strip()

    if isinstance(value, bool):
        return "sim" if value else "não"

    if isinstance(value, (list, tuple, set)):
        return "; ".join(str(x).strip() for x in value if str(x).strip())

    return str(value).strip()


def split_presenter_product(product: dict | None) -> tuple[dict, dict]:
    """Separa dados permanentes de condições da LIVE.

    Aceita tanto produto achatado por ProductStore.active_for_presenter()
    quanto estrutura com live_conditions aninhada.
    """
    source = dict(product or {})
    nested_live = source.get("live_conditions")
    nested_live = nested_live if isinstance(nested_live, dict) else {}

    permanent: dict[str, Any] = {}
    live: dict[str, Any] = {}

    for field in PERMANENT_FIELDS:
        value = source.get(field)
        if _present(value):
            permanent[field] = value

    for field in LIVE_FIELDS:
        value = (
            source.get(field)
            if field in source
            else nested_live.get(field)
        )
        if _present(value) or (field == "live_offer" and value is True):
            live[field] = value

    return permanent, live


def build_allowed_facts(product: dict | None) -> list[str]:
    """Gera fatos canônicos que o modelo deve citar exatamente em used_facts."""
    permanent, live = split_presenter_product(product)
    facts: list[str] = []

    for field in PERMANENT_FIELDS:
        if field not in permanent:
            continue
        label = FACT_LABELS.get(field, field)
        facts.append(f"{label}: {_format_value(field, permanent[field])}")

    for field in LIVE_FIELDS:
        if field not in live:
            continue
        if field == "live_offer" and live[field] is False:
            continue
        label = FACT_LABELS.get(field, field)
        facts.append(f"{label}: {_format_value(field, live[field])}")

    return facts


def build_brain_context(
    *,
    product: dict,
    mode: str,
    decision: dict | None = None,
    planner_topic: str = "",
    memory_snapshot: dict | None = None,
    recent_comments: Iterable[CommentPayload | dict] | None = None,
    recent_facts: list[str] | None = None,
) -> BrainContext:
    permanent, live = split_presenter_product(product)
    decision = dict(decision or {})
    memory = dict(memory_snapshot or {})

    comment = None
    text = str(decision.get("comment") or "").strip()
    user = str(decision.get("user") or "").strip()
    if text:
        comment = CommentPayload(
            id=str(decision.get("comment_id") or ""),
            username=user,
            text=text,
        )

    normalized_recent: list[CommentPayload] = []
    for item in recent_comments or []:
        if isinstance(item, CommentPayload):
            normalized_recent.append(item)
            continue
        if isinstance(item, dict):
            normalized_recent.append(
                CommentPayload(
                    id=str(item.get("id") or ""),
                    username=str(
                        item.get("username")
                        or item.get("user")
                        or ""
                    ),
                    text=str(item.get("text") or item.get("comment") or ""),
                )
            )

    sales_thread = str(
        memory.get("current_pitch_topic")
        or memory.get("interrupted_topic")
        or ""
    )

    return BrainContext(
        mode=mode,
        product=permanent,
        live_conditions=live,
        comment=comment,
        decision=decision,
        recent_comments=normalized_recent[-8:],
        recent_speeches=list(memory.get("recent_speeches") or [])[-8:],
        recent_facts=list(recent_facts or [])[-12:],
        sales_thread=sales_thread,
        planner_topic=str(planner_topic or decision.get("topic") or ""),
        allowed_facts=build_allowed_facts(product),
    )

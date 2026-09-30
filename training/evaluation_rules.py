"""Regras de avaliação do laboratório AGCN Presenter v0.1."""

from __future__ import annotations

import re


GENERIC_SCARCITY = (
    "poucas unidades",
    "últimas unidades",
    "ultimas unidades",
    "não vai ter pra todo mundo",
    "nao vai ter pra todo mundo",
    "finaliza enquanto tem",
    "aproveita enquanto tem",
    "pra não ficar sem",
    "pra nao ficar sem",
    "não deixa pra depois",
    "nao deixa pra depois",
    "finaliza agora",
    "quem deixar pra depois pode ficar sem",
)

FORMAL_MARKERS = (
    " está ",
    " estou ",
    " para você",
    " não deixe para depois",
    " realize a compra",
    " informo que",
    " conforme informado",
)


def quantity_spoken(speech: str, stock: int) -> bool:
    # Avoid matching stock=3 inside a price such as 139. Spellings commonly
    # used in short TTS answers count too; this is still only a lexical check.
    words = {0: "zero", 1: "uma", 2: "duas", 3: "três", 4: "quatro", 5: "cinco", 6: "seis", 7: "sete", 8: "oito", 9: "nove", 10: "dez", 11: "onze", 12: "doze", 13: "treze", 14: "quatorze", 15: "quinze", 16: "dezesseis", 17: "dezessete", 18: "dezoito", 19: "dezenove", 20: "vinte"}
    numeric = re.search(r"(?<![\d.,])" + re.escape(str(stock)) + r"(?![\d.,])", speech)
    word = words.get(stock)
    spoken = bool(word and re.search(r"\b" + re.escape(word) + r"\b", speech.casefold()))
    return bool(numeric or spoken)


def evaluate_output(example: dict, result: dict | None, error: str = "") -> dict:
    target = example.get("target") or {}
    inp = example.get("input") or {}
    meta = example.get("metadata") or {}
    rules = inp.get("commercial_rules") or {}
    allowed = {str(x).strip().casefold() for x in inp.get("allowed_facts") or []}
    tags = set(meta.get("tags") or [])

    if not isinstance(result, dict) or not result:
        return {
            "valid_json": False,
            "failed": True,
            "error": error,
            "reported_facts_ok": False,
            "numeric_claims_ok": False,
            "ignore_ok": False,
            "oral_style_ok": False,
            "scarcity_ok": False if "scarcity" in tags else None,
            "quantity_ok": False if "quantity_scarcity" in tags else None,
            "buying_guidance_ok": False if "buying_intent" in tags else None,
        }

    speech = str(result.get("speech") or "").strip()
    fold = f" {speech.casefold()} "
    used = [str(x).strip() for x in result.get("used_facts") or []]

    reported_ok = all(x.casefold() in allowed for x in used)

    expected_ignore = target.get("speech") == "IGNORAR"
    if expected_ignore:
        ignore_ok = speech == "IGNORAR" and bool(result.get("needs_fact"))
    else:
        ignore_ok = speech != "IGNORAR" and not bool(result.get("needs_fact"))

    oral_ok = not any(marker in fold for marker in FORMAL_MARKERS)

    scarcity_ok = None
    if "scarcity" in tags:
        generic_allowed = (
            bool(rules.get("live_inventory_limited"))
            and bool(rules.get("generic_scarcity_enabled"))
        )
        scarcity_present = any(x in fold for x in GENERIC_SCARCITY)
        stock = rules.get("stock_quantity")
        if stock is not None:
            scarcity_present = scarcity_present or quantity_spoken(speech, int(stock))
        scarcity_ok = bool(generic_allowed and scarcity_present)

    quantity_ok = None
    if "quantity_scarcity" in tags:
        stock = rules.get("stock_quantity")
        quantity_ok = stock is not None and quantity_spoken(speech, int(stock))

    buying_ok = None
    if "buying_intent" in tags:
        buying_ok = any(
            marker in fold
            for marker in (
                "produto fixado",
                "carrinho",
                "sacolinha",
                "finaliza",
                "comprar",
                "compra",
            )
        )

    allowed_numbers = {
        token.replace(".", ",")
        for fact in inp.get("allowed_facts") or []
        for token in re.findall(r"\d+(?:[.,]\d+)?", str(fact))
    }
    numeric_ok = True
    for token in re.findall(r"\d+(?:[.,]\d+)?", speech):
        if token.replace(".", ",") not in allowed_numbers:
            numeric_ok = False
            break

    return {
        "valid_json": True,
        "failed": False,
        "reported_facts_ok": reported_ok,
        "numeric_claims_ok": numeric_ok,
        "ignore_ok": ignore_ok,
        "oral_style_ok": oral_ok,
        "scarcity_ok": scarcity_ok,
        "quantity_ok": quantity_ok,
        "buying_guidance_ok": buying_ok,
    }

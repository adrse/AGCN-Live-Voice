from __future__ import annotations

from core.product_knowledge import ProductKnowledge


class SalesGuard:
    """Expõe somente fatos comerciais realmente cadastrados."""

    FACT_MAP = {
        "brand": "brand",
        "price": "current_price",
        "regular_price": "regular_price",
        "availability": "stock",
        "stock": "stock",
        "shipping": "shipping_info",
        "warranty": "warranty",
        "compatibility": "compatibility",
        "included_items": "included_items",
        "size": "size_info",
        "battery": "battery_info",
        "usage": "usage_info",
        "limitations": "limitations",
        "benefits": "key_benefits",
        "problems_solved": "problems_solved",
        "differentials": "differentials",
    }

    def __init__(self, product: dict | None):
        self.product = dict(product or {})
        self.knowledge = ProductKnowledge(self.product)

    def get(self, fact: str):
        key = self.FACT_MAP.get(fact, fact)
        value = self.product.get(key)
        if value in (None, "", [], {}):
            return None
        return value

    def live_offer(self) -> str | None:
        enabled = bool(self.product.get("live_offer"))
        text = self.product.get("live_offer_text")
        if not enabled:
            return None
        return str(text or "Oferta cadastrada para esta LIVE.").strip()

    def grounded_urgency(self) -> list[str]:
        """Retorna somente sinais de urgência comercial verificáveis.

        Estoque baixo real (1 a 10 unidades) pode ser verbalizado pelo número
        exato. Estoque alto não autoriza "está acabando". Oferta/nota
        promocional também só entra quando foi cadastrada para esta LIVE.
        """
        reasons: list[str] = []

        stock = self.get("stock")
        if stock is not None:
            try:
                stock_n = int(float(stock))
                if 1 <= stock_n <= 10:
                    reasons.append(f"stock:{stock_n}")
            except Exception:
                pass

        if self.live_offer():
            reasons.append("live_offer")

        note = str(self.product.get("promotion_note") or "").strip()
        folded = (
            note.casefold()
            .replace("á", "a")
            .replace("à", "a")
            .replace("ã", "a")
            .replace("â", "a")
            .replace("é", "e")
            .replace("ê", "e")
            .replace("í", "i")
            .replace("ó", "o")
            .replace("ô", "o")
            .replace("õ", "o")
            .replace("ú", "u")
            .replace("ç", "c")
        )
        urgency_markers = (
            "ultima",
            "resta",
            "relampago",
            "termina",
            "encerra",
            "so hoje",
            "exclusiv",
            "esgot",
            "carrinho",
            "limitad",
        )
        if note and any(marker in folded for marker in urgency_markers):
            reasons.append("promotion_note")

        return reasons

    def fact_for_topic(self, topic: str):
        if topic == "price":
            return {
                "current_price": self.product.get("current_price"),
                "regular_price": self.product.get("regular_price"),
                "discount": self.product.get("discount"),
            }
        return self.get(topic)

    def fact_for_decision(self, decision: dict) -> dict:
        """Resolve uma pergunta usando somente informações cadastradas."""
        packet = self.knowledge.resolve(
            intent=decision.get("intent"),
            topic=decision.get("topic"),
            comment=decision.get("comment"),
        )
        return packet

    def can_claim(self, claim: str) -> bool:
        if claim == "live_exclusive":
            return bool(self.live_offer())
        if claim == "scarcity":
            return bool(self.grounded_urgency())
        return self.get(claim) is not None

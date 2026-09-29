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
        """Retorna apenas urgência explicitamente cadastrada.

        Um número de estoque, sozinho, NÃO significa escassez. Isso evita
        frases como "está acabando" quando existem muitas unidades.
        """
        reasons = []
        if self.live_offer():
            reasons.append("live_offer")
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

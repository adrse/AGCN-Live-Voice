from __future__ import annotations

import math
import random
import re


def text(value) -> str:
    if value in (None, "", [], {}):
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def brl(value):
    if value in (None, ""):
        return None
    try:
        return (
            f"R$ {float(value):,.2f}"
            .replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )
    except Exception:
        return str(value)


class PersuasionEngine:
    """Persuasão comercial forte, mas sempre presa aos fatos da LIVE.

    O objetivo é reproduzir os comportamentos que funcionaram nos benchmarks:
    resposta imediata, ancoragem, urgência, escassez real, prova social real,
    dor -> solução -> benefício e CTA claro. Nenhum gatilho é inventado.
    """

    CTA_VARIANTS = {
        "buy_now": [
            "Se você já decidiu, clica no produto fixado e garante o seu.",
            "Gostou e quer levar? Vai no produto fixado e finaliza enquanto essa condição estiver valendo.",
            "Pra garantir o seu, é só abrir o produto fixado aqui na LIVE e finalizar.",
            "Se era isso que você estava procurando, aproveita e garante pelo produto fixado.",
        ],
        "soft_close": [
            "Olha a condição no produto fixado e compara com o que você estava procurando.",
            "Dá uma conferida no produto fixado porque, pelo que você falou, ele pode encaixar bem no que você precisa.",
            "Confere a oferta no produto fixado e vê se faz sentido pra você.",
        ],
        "after_answer": [
            "Se isso era o que faltava pra decidir, o produto está fixado aqui na LIVE.",
            "Se essa era sua dúvida, já dá pra conferir a oferta no produto fixado.",
            "Agora que ficou claro, dá uma olhada no produto fixado aqui embaixo.",
        ],
    }

    PURCHASE_VARIANTS = [
        "Aí sim, {user}! Compra garantida. Parabéns!",
        "Boa, {user}! Você garantiu o seu. Parabéns pela compra!",
        "Fechou, {user}! Parabéns pela compra!",
        "{user}, boa demais! Pedido garantido, parabéns!",
    ]

    def __init__(self, product: dict | None):
        self.product = dict(product or {})

    def set_product(self, product: dict | None) -> None:
        self.product = dict(product or {})

    def signals(self) -> dict:
        current = self._number(self.product.get("current_price"))
        regular = self._number(self.product.get("regular_price"))
        discount = self._number(self.product.get("discount"))
        stock = self._number(self.product.get("stock"))

        savings = None
        calculated_discount = None
        if current is not None and regular is not None and regular > current:
            savings = regular - current
            calculated_discount = round((savings / regular) * 100)

        return {
            "current_price": current,
            "regular_price": regular,
            "discount": discount if discount is not None else calculated_discount,
            "savings": savings,
            "stock": int(stock) if stock is not None and stock >= 0 else None,
            "coupon": text(self.product.get("coupon")),
            "live_offer": bool(self.product.get("live_offer")),
            "live_offer_text": text(self.product.get("live_offer_text")),
            "promotion_note": text(self.product.get("promotion_note")),
            "shipping_info": text(self.product.get("shipping_info")),
        }

    def price_anchor(self) -> str:
        s = self.signals()
        current = s["current_price"]
        regular = s["regular_price"]
        savings = s["savings"]
        discount = s["discount"]

        if current is not None and regular is not None and regular > current:
            parts = [
                f"Ele está por {brl(current)}, e o valor de referência cadastrado é {brl(regular)}."
            ]
            if savings is not None and savings > 0:
                parts.append(f"São {brl(savings)} de diferença.")
            if discount is not None and discount > 0:
                parts.append(f"Isso dá cerca de {int(round(discount))}% a menos.")
            return " ".join(parts)

        if current is not None:
            return f"O valor cadastrado agora é {brl(current)}."

        if regular is not None:
            return f"O valor cadastrado é {brl(regular)}."

        return ""

    def grounded_urgency(self, memory=None, *, strong=False) -> str:
        s = self.signals()
        pieces = []

        # Estoque só vira escassez se o número realmente existir.
        stock = s["stock"]
        if stock is not None:
            if stock <= 3:
                pieces.append(
                    f"Atenção porque o estoque informado está em só {stock} unidade"
                    + ("" if stock == 1 else "s")
                    + "."
                )
            elif stock <= 10:
                pieces.append(
                    f"O estoque informado está em {stock} unidades agora."
                )
            elif strong:
                pieces.append(
                    f"O estoque informado agora é de {stock} unidades."
                )

        if s["live_offer"] and s["live_offer_text"]:
            pieces.append(s["live_offer_text"])
        elif s["live_offer"]:
            pieces.append("Tem uma condição de oferta cadastrada para esta LIVE.")

        if s["coupon"]:
            pieces.append(f"Tem cupom cadastrado: {s['coupon']}.")

        if s["promotion_note"]:
            pieces.append(s["promotion_note"])

        if not pieces:
            return ""

        return " ".join(pieces[:2])

    def social_proof(self, memory) -> str:
        if memory is None:
            return ""

        count = memory.recent_purchase_count(within=180)
        if count <= 0:
            return ""

        if count == 1:
            return "Já teve compra confirmada aqui no chat."
        return f"Já tivemos {count} compras confirmadas pelo chat nos últimos minutos."

    def objection_response(self, user: str, name: str, memory=None) -> str:
        address = f"{user}, " if user else ""
        benefits = text(self.product.get("key_benefits"))
        problems = text(self.product.get("problems_solved"))
        differentials = text(self.product.get("differentials"))

        parts = [f"{address}eu entendo a sua dúvida."]

        # Primeiro reancora no valor real, como nos vendedores humanos mais
        # fortes do benchmark.
        anchor = self.price_anchor()
        if anchor:
            parts.append(anchor)

        if problems and benefits:
            parts.append(
                f"O ponto é que ele foi pensado pra {problems}, e entrega {benefits}."
            )
        elif benefits:
            parts.append(f"O que pesa a favor dele é {benefits}.")
        elif differentials:
            parts.append(f"O diferencial dele é {differentials}.")

        urgency = self.grounded_urgency(memory)
        if urgency:
            parts.append(urgency)

        return " ".join(parts)

    def value_bridge(
        self,
        *,
        intent: str,
        memory,
        name: str,
    ) -> str:
        """Expansão curta depois de responder a pergunta."""
        candidates = []

        benefits = text(self.product.get("key_benefits"))
        problems = text(self.product.get("problems_solved"))
        differentials = text(self.product.get("differentials"))
        included = text(self.product.get("included_items"))

        if problems and benefits:
            candidates.append((
                "pain_solution",
                f"Na prática, isso ajuda principalmente quem quer {problems}, porque {benefits}.",
            ))

        if benefits:
            candidates.append((
                "benefit",
                f"E o ponto forte do {name} é {benefits}.",
            ))

        if differentials:
            candidates.append((
                "differential",
                f"O diferencial aqui é {differentials}.",
            ))

        if included:
            candidates.append((
                "bundle",
                f"E já olha o conjunto completo: {included}.",
            ))

        anchor = self.price_anchor()
        if anchor:
            candidates.append(("price_anchor", anchor))

        social = self.social_proof(memory)
        if social:
            candidates.append(("social_proof", social))

        # Em perguntas técnicas, evita transformar toda resposta em um pitch.
        if intent in {
            "safety_or_critical",
            "technical_question",
            "compatibility",
            "warranty",
        }:
            candidates = [
                item
                for item in candidates
                if item[0] in {"benefit", "differential", "pain_solution"}
            ]

        available = [
            item
            for item in candidates
            if not memory.recently_used_tactic(item[0], within=35)
        ]

        if not available:
            return ""

        tactic, phrase = random.choice(available)
        memory.remember_tactic(tactic)
        return phrase

    def proactive_pitch(self, topic: str, name: str, memory) -> str:
        s = self.signals()

        if topic == "scarcity":
            urgency = self.grounded_urgency(memory, strong=True)
            if urgency:
                memory.remember_tactic("scarcity")
                return (
                    f"Quem já estava de olho no {name}, presta atenção: {urgency} "
                    "Se você quer levar, não deixa pra decidir depois."
                )

        if topic == "price_value":
            anchor = self.price_anchor()
            if anchor:
                memory.remember_tactic("price_anchor")
                return (
                    f"Olha a relação de valor do {name}: {anchor} "
                    "É justamente aí que a oferta fica interessante."
                )

        if topic == "social_proof":
            proof = self.social_proof(memory)
            if proof:
                memory.remember_tactic("social_proof")
                return f"{proof} O {name} está chamando atenção aqui na LIVE."

        if topic == "pain_solution":
            problems = text(self.product.get("problems_solved"))
            benefits = text(self.product.get("key_benefits"))
            if problems and benefits:
                memory.remember_tactic("pain_solution")
                return (
                    f"Se você sofre com {problems}, presta atenção no {name}: "
                    f"{benefits}."
                )

        if topic == "bundle_value":
            included = text(self.product.get("included_items"))
            if included:
                memory.remember_tactic("bundle")
                return f"Olha o que já vem no {name}: {included}."

        if topic == "trust":
            limitation = text(self.product.get("limitations"))
            warranty = text(self.product.get("warranty"))
            if limitation:
                memory.remember_tactic("trust")
                return (
                    f"E eu prefiro ser claro sobre o {name}: {limitation}. "
                    "Assim você compra sabendo exatamente o que está levando."
                )
            if warranty:
                memory.remember_tactic("trust")
                return f"Pra quem perguntou de segurança na compra: {warranty}."

        return ""

    def cta(
        self,
        kind: str,
        *,
        memory=None,
        allow_urgency=True,
    ) -> str:
        variants = self.CTA_VARIANTS.get(kind) or []
        if not variants:
            return ""

        phrase = random.choice(variants)
        if memory is not None:
            memory.remember_tactic("cta_" + kind)

        if allow_urgency:
            urgency = self.grounded_urgency(memory)
            if urgency and (
                memory is None
                or not memory.recently_used_tactic("urgency", within=30)
            ):
                if memory is not None:
                    memory.remember_tactic("urgency")
                phrase = f"{phrase} {urgency}"

        return phrase

    def purchase_celebration(self, user: str) -> str:
        safe_user = user or "você"
        return random.choice(self.PURCHASE_VARIANTS).format(user=safe_user)

    @staticmethod
    def _number(value):
        if value in (None, ""):
            return None
        try:
            return float(value)
        except Exception:
            return None

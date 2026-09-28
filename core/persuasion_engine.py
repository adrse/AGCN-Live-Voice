from __future__ import annotations

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
    """Persuasão de LIVE com linguagem brasileira natural.

    Regra central: vender forte sem soar como script e sem inventar urgência,
    estoque, compra, preço, benefício ou condição comercial.
    """

    CTA_VARIANTS = {
        "buy_now": [
            "Não perde tempo não, garante o seu.",
            "Se você quer mesmo, já garante o seu.",
            "Aproveita e garante o seu agora.",
            "Gostou? Então já garante o seu.",
            "Se era isso que você queria, já pega o seu.",
        ],
        "soft_close": [
            "Dá uma olhada ali no produto, acho que vale a pena conferir.",
            "Confere ali a oferta e vê se é o que você tava procurando.",
            "Olha ali no produto porque pode compensar bastante pra você.",
            "Dá uma conferida ali e vê se te atende.",
        ],
        "after_answer": [
            "Se era essa a dúvida, já dá uma olhada ali no produto.",
            "Pronto, agora já dá pra decidir mais tranquilo.",
            "Era isso que você queria saber, né? Confere ali o produto.",
            "Aí ó, se era isso que faltava, já dá uma olhada na oferta.",
        ],
    }

    PURCHASE_VARIANTS = [
        "Aí sim, {user}! Boa compra!",
        "Boa, {user}! Garantiu o seu!",
        "Fechou, {user}! Parabéns!",
        "{user}, boa! Já garantiu o seu!",
        "Aí sim, {user}! Valeu, boa compra!",
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

        if current is not None and regular is not None and regular > current:
            variants = [
                f"Tá {brl(current)} só. Ele era {brl(regular)}.",
                f"Olha o preço: de {brl(regular)} por {brl(current)}.",
                f"Tá saindo por {brl(current)}. O preço anterior era {brl(regular)}.",
            ]
            base = random.choice(variants)

            if savings is not None and savings >= 10:
                saving = brl(savings)
                if random.random() < 0.55:
                    base += f" Dá {saving} de diferença."

            return base

        if current is not None:
            return random.choice([
                f"Tá {brl(current)} agora.",
                f"Hoje tá saindo por {brl(current)}.",
                f"O preço agora tá {brl(current)}.",
            ])

        if regular is not None:
            return f"Tá {brl(regular)}."

        return ""

    def grounded_urgency(self, memory=None, *, strong=False) -> str:
        s = self.signals()
        pieces = []
        stock = s["stock"]

        if stock is not None:
            noun = "unidade" if stock == 1 else "unidades"
            if stock <= 3:
                pieces.append(random.choice([
                    f"Tem {stock} {noun} só agora.",
                    f"Ó, só {stock} {noun} agora.",
                    f"Restam {stock} {noun} só.",
                ]))
            elif stock <= 10:
                pieces.append(random.choice([
                    f"Tem {stock} {noun} só.",
                    f"Ó, tá em {stock} {noun} agora.",
                    f"Agora tem {stock} {noun}.",
                ]))
            elif strong:
                pieces.append(f"Tem {stock} {noun} disponíveis agora.")

        if s["live_offer"] and s["live_offer_text"]:
            pieces.append(s["live_offer_text"])
        elif s["live_offer"]:
            pieces.append(random.choice([
                "Tem oferta rolando na LIVE agora.",
                "A oferta da LIVE tá ativa agora.",
            ]))

        if s["coupon"]:
            pieces.append(random.choice([
                f"E tem cupom também: {s['coupon']}.",
                f"Tem cupom rolando também: {s['coupon']}.",
            ]))

        if s["promotion_note"]:
            pieces.append(s["promotion_note"])

        return " ".join(pieces[:2])

    def social_proof(self, memory) -> str:
        if memory is None:
            return ""

        count = memory.recent_purchase_count(within=180)
        if count <= 0:
            return ""

        if count == 1:
            return random.choice([
                "Ó, já teve gente garantindo aqui.",
                "Já saiu compra aqui no chat.",
                "Já teve gente levando agora há pouco.",
            ])

        return random.choice([
            f"Ó, já foram {count} compras confirmadas aqui no chat nos últimos minutos.",
            f"Já teve {count} pessoas confirmando compra aqui nos últimos minutos.",
            f"Enquanto a gente tá falando, já apareceram {count} compras confirmadas no chat.",
        ])

    def buying_intent_response(
        self,
        user: str,
        comment: str,
        memory=None,
    ) -> str:
        address = f"{user}, " if user else ""
        q = text(comment).casefold()

        asks_how = any(
            token in q
            for token in (
                "como compra",
                "como comprar",
                "onde compra",
                "onde comprar",
                "manda o link",
                "cadê o link",
                "cade o link",
                "qual link",
            )
        )

        if asks_how:
            base = random.choice([
                "é só clicar no produto fixado aí e finalizar.",
                "clica no produto fixado aí embaixo e já finaliza por lá.",
                "vai no produto fixado da LIVE e finaliza por ali.",
            ])
        else:
            base = random.choice(self.CTA_VARIANTS["buy_now"])

        urgency = self.grounded_urgency(memory)
        if urgency:
            base = f"{base} {urgency}"

        return address + base

    def objection_response(
        self,
        user: str,
        name: str,
        memory=None,
        comment: str = "",
    ) -> str:
        address = f"{user}, " if user else ""
        q = text(comment).casefold()
        benefits = text(self.product.get("key_benefits"))
        problems = text(self.product.get("problems_solved"))
        differentials = text(self.product.get("differentials"))
        shipping = text(self.product.get("shipping_info"))

        parts = []
        anchor = self.price_anchor()

        if any(x in q for x in ("caro", "cara", "preço", "preco", "valor")):
            if anchor:
                parts.append(f"{address}{anchor}")
            else:
                parts.append(f"{address}olha só.")
        elif any(x in q for x in ("frete", "entrega")) and shipping:
            parts.append(f"{address}{shipping}.")
        else:
            if anchor:
                parts.append(f"{address}{anchor}")
            else:
                parts.append(random.choice([
                    f"{address}olha só.",
                    f"{address}presta atenção nisso.",
                    f"{address}vou te falar.",
                ]))

        if problems and benefits:
            parts.append(random.choice([
                f"O legal é que ele resolve {problems} e ainda {benefits}.",
                f"Pra quem quer {problems}, ele ajuda porque {benefits}.",
            ]))
        elif benefits:
            parts.append(random.choice([
                f"E o bom dele é {benefits}.",
                f"O ponto forte dele é {benefits}.",
                f"E tem isso aqui que pesa muito: {benefits}.",
            ]))
        elif differentials:
            parts.append(random.choice([
                f"E o diferencial dele é {differentials}.",
                f"O que muda nele é {differentials}.",
            ]))

        urgency = self.grounded_urgency(memory)
        if urgency:
            parts.append(urgency)

        return " ".join(x for x in parts if x).strip()

    def value_bridge(
        self,
        *,
        intent: str,
        memory,
        name: str,
    ) -> str:
        candidates = []

        benefits = text(self.product.get("key_benefits"))
        problems = text(self.product.get("problems_solved"))
        differentials = text(self.product.get("differentials"))
        included = text(self.product.get("included_items"))

        if problems and benefits:
            candidates.extend([
                (
                    "pain_solution",
                    f"E pra quem quer {problems}, isso ajuda bastante porque {benefits}.",
                ),
                (
                    "pain_solution",
                    f"Na prática, isso ajuda muito em {problems}, porque {benefits}.",
                ),
            ])

        if benefits:
            candidates.extend([
                ("benefit", f"E o bom dele é {benefits}."),
                ("benefit", f"Ó, um ponto forte dele é {benefits}."),
            ])

        if differentials:
            candidates.extend([
                ("differential", f"E o diferencial aqui é {differentials}."),
                ("differential", f"Agora, uma coisa legal nele é {differentials}."),
            ])

        if included:
            candidates.extend([
                ("bundle", f"E já vem com {included}."),
                ("bundle", f"Fora que no kit já vem {included}."),
            ])

        anchor = self.price_anchor()
        if anchor:
            candidates.append(("price_anchor", anchor))

        social = self.social_proof(memory)
        if social:
            candidates.append(("social_proof", social))

        # Pergunta técnica: responde primeiro e não transforma tudo num
        # discurso enorme de venda.
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
        if topic == "scarcity":
            urgency = self.grounded_urgency(memory, strong=True)
            if urgency:
                memory.remember_tactic("scarcity")
                return random.choice([
                    f"Ó, quem tava de olho no {name}: {urgency} Não deixa pra depois não.",
                    f"Gente, presta atenção no {name}: {urgency} Se quiser, já garante.",
                    f"Quem queria o {name}, é agora: {urgency}",
                ])

        if topic == "price_value":
            anchor = self.price_anchor()
            if anchor:
                memory.remember_tactic("price_anchor")
                return random.choice([
                    f"Olha o preço do {name}: {anchor}",
                    f"Gente, olha isso no {name}: {anchor}",
                    f"Pra quem tava esperando preço, ó: {anchor}",
                ])

        if topic == "social_proof":
            proof = self.social_proof(memory)
            if proof:
                memory.remember_tactic("social_proof")
                return f"{proof} O {name} tá saindo."

        if topic == "pain_solution":
            problems = text(self.product.get("problems_solved"))
            benefits = text(self.product.get("key_benefits"))
            if problems and benefits:
                memory.remember_tactic("pain_solution")
                return random.choice([
                    f"Se o seu problema é {problems}, olha esse {name}: {benefits}.",
                    f"Pra quem quer resolver {problems}, presta atenção: {benefits}.",
                ])

        if topic == "bundle_value":
            included = text(self.product.get("included_items"))
            if included:
                memory.remember_tactic("bundle")
                return random.choice([
                    f"E olha o que já vem junto: {included}.",
                    f"Fora que você já leva {included}.",
                ])

        if topic == "trust":
            limitation = text(self.product.get("limitations"))
            warranty = text(self.product.get("warranty"))
            if limitation:
                memory.remember_tactic("trust")
                return random.choice([
                    f"Agora, sendo bem claro: {limitation}. Melhor você saber certinho antes de comprar.",
                    f"E tem um detalhe importante: {limitation}. Tô falando pra você saber exatamente o que tá levando.",
                ])
            if warranty:
                memory.remember_tactic("trust")
                return f"Pra quem perguntou de garantia: {warranty}."

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

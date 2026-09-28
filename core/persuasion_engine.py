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

    @staticmethod
    def entries(value) -> list[str]:
        if value in (None, "", [], {}):
            return []

        if isinstance(value, (list, tuple, set)):
            raw = [text(x) for x in value]
        else:
            raw = [
                text(x)
                for x in re.split(r"[\n;|]+", text(value))
            ]

        out = []
        seen = set()
        for item in raw:
            if not item:
                continue
            key = item.casefold()
            if key in seen:
                continue
            seen.add(key)
            out.append(item)
        return out

    def pick_item(
        self,
        field: str,
        memory=None,
        *,
        count: int = 1,
    ) -> list[str]:
        items = self.entries(self.product.get(field))
        if not items:
            return []

        if memory is not None:
            fresh = [
                item
                for item in items
                if not memory.recently_used_tactic(
                    "fact:" + field + ":" + item.casefold(),
                    within=120,
                )
            ]
            if fresh:
                items = fresh

        random.shuffle(items)
        chosen = items[:max(1, min(count, len(items)))]

        if memory is not None:
            for item in chosen:
                memory.remember_tactic(
                    "fact:" + field + ":" + item.casefold()
                )

        return chosen

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
        if topic == "description":
            item = self.pick_item(
                "description",
                memory,
                count=1,
            )
            if item:
                return random.choice([
                    f"Ó, esse {name} aqui: {item[0]}.",
                    f"Esse aqui é o {name}. {item[0]}.",
                    f"Olha só esse {name}: {item[0]}.",
                ])

        if topic == "benefits":
            items = self.pick_item(
                "key_benefits",
                memory,
                count=1,
            )
            if items:
                return random.choice([
                    f"Ó, uma coisa boa dele: {items[0]}.",
                    f"E olha isso aqui: {items[0]}.",
                    f"Esse aqui tem um ponto muito bom: {items[0]}.",
                    f"O bom dele é isso: {items[0]}.",
                ])

        if topic == "usage":
            items = self.pick_item(
                "usage_info",
                memory,
                count=1,
            )
            if items:
                return random.choice([
                    f"Pra usar é bem tranquilo: {items[0]}.",
                    f"No dia a dia funciona assim: {items[0]}.",
                    f"Ó, na prática você usa assim: {items[0]}.",
                ])

        if topic == "differentials":
            items = self.pick_item(
                "differentials",
                memory,
                count=1,
            )
            if items:
                return random.choice([
                    f"E presta atenção nesse detalhe: {items[0]}.",
                    f"Agora, o diferencial dele é esse aqui: {items[0]}.",
                    f"Uma coisa que eu achei legal nele: {items[0]}.",
                ])

        if topic == "bundle_value":
            items = self.pick_item(
                "included_items",
                memory,
                count=2,
            )
            if items:
                joined = " e ".join(items)
                return random.choice([
                    f"E já vem com {joined}.",
                    f"No kit você já leva {joined}.",
                    f"Fora o produto, já vem {joined}.",
                ])

        if topic == "compatibility":
            items = self.pick_item(
                "compatibility",
                memory,
                count=1,
            )
            if items:
                return random.choice([
                    f"E uma coisa importante: {items[0]}.",
                    f"Ó, sobre compatibilidade: {items[0]}.",
                    f"Pra não ter dúvida depois: {items[0]}.",
                ])

        if topic == "size":
            items = self.pick_item(
                "size_info",
                memory,
                count=1,
            )
            if items:
                return random.choice([
                    f"Ó, o tamanho dele é {items[0]}.",
                    f"Pra vocês terem noção do tamanho: {items[0]}.",
                    f"Medida dele: {items[0]}.",
                ])

        if topic == "battery":
            items = self.pick_item(
                "battery_info",
                memory,
                count=1,
            )
            if items:
                return random.choice([
                    f"E de bateria, ó: {items[0]}.",
                    f"Sobre a bateria: {items[0]}.",
                    f"Uma coisa boa pra saber da bateria: {items[0]}.",
                ])

        if topic == "pain_solution":
            problems = self.pick_item(
                "problems_solved",
                memory,
                count=1,
            )
            benefits = self.pick_item(
                "key_benefits",
                memory,
                count=1,
            )
            if problems and benefits:
                return random.choice([
                    f"Se você sofre com {problems[0]}, esse aqui ajuda porque {benefits[0]}.",
                    f"Pra quem quer resolver {problems[0]}, olha isso: {benefits[0]}.",
                ])

        if topic == "price_value":
            anchor = self.price_anchor()
            if anchor:
                memory.remember_tactic("price_anchor")
                return random.choice([
                    f"Olha o preço: {anchor}",
                    f"E o valor dele agora, ó: {anchor}",
                    f"Agora presta atenção no preço: {anchor}",
                ])

        if topic == "scarcity":
            urgency = self.grounded_urgency(memory, strong=True)
            if urgency:
                memory.remember_tactic("scarcity")
                return random.choice([
                    f"Ó, presta atenção nisso: {urgency} Não enrola muito não.",
                    f"Agora é bom ficar ligado: {urgency}",
                    f"E olha a quantidade agora: {urgency}",
                ])

        if topic == "social_proof":
            proof = self.social_proof(memory)
            if proof:
                memory.remember_tactic("social_proof")
                return proof

        if topic == "trust":
            limitations = self.pick_item(
                "limitations",
                memory,
                count=1,
            )
            warranty = self.pick_item(
                "warranty",
                memory,
                count=1,
            )
            if limitations:
                return random.choice([
                    f"Agora, um detalhe pra você saber certinho: {limitations[0]}.",
                    f"E eu vou falar isso aqui também: {limitations[0]}.",
                ])
            if warranty:
                return random.choice([
                    f"E de garantia: {warranty[0]}.",
                    f"Sobre garantia, ó: {warranty[0]}.",
                ])

        if topic == "newcomer_recap":
            benefit = self.pick_item(
                "key_benefits",
                memory,
                count=1,
            )
            desc = self.pick_item(
                "description",
                memory,
                count=1,
            )
            detail = benefit[0] if benefit else (desc[0] if desc else "")
            if detail:
                return random.choice([
                    f"Pra quem chegou agora, a gente tá mostrando o {name}. {detail}.",
                    f"Ó, só recapitulando pra quem entrou agora: esse é o {name}. {detail}.",
                ])
            return f"Pra quem chegou agora, esse aqui é o {name}."

        if topic == "product_recap":
            benefit = self.pick_item(
                "key_benefits",
                memory,
                count=1,
            )
            if benefit:
                return f"Ó, resumindo esse {name}: {benefit[0]}."
            desc = self.pick_item(
                "description",
                memory,
                count=1,
            )
            if desc:
                return f"Ó, esse {name} aqui: {desc[0]}."
            return f"Ó, esse aqui é o {name}."

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

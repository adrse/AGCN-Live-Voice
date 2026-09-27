from __future__ import annotations

import heapq
import itertools
import re
import time


def clean(text) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip())


def money(value) -> str | None:
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


class PresenterEngine:
    """Presenter determinístico da baseline V0.4.1.

    Será evoluído na V0.5 pelo Presenter Behavior V1.
    """

    PRIORITY = {
        "direct_question": 100,
        "price": 95,
        "availability": 92,
        "buying_intent": 90,
        "shipping": 86,
        "usage": 82,
        "objection": 78,
        "engagement": 45,
        "proactive": 20,
    }

    LABELS = {
        "direct_question": "Pergunta direta",
        "price": "Preço",
        "availability": "Disponibilidade",
        "buying_intent": "Intenção de compra",
        "shipping": "Frete / entrega",
        "usage": "Como usar",
        "objection": "Objeção",
        "engagement": "Engajamento",
        "proactive": "Fala proativa",
    }

    def __init__(self, product: dict | None):
        self.product = dict(product or {})
        self.queue = []
        self.counter = itertools.count()
        self.recent_keys = {}
        self.last_proactive_at = 0.0

    def product_name(self) -> str:
        return clean(self.product.get("name")) or "este produto"

    def known(self, key: str) -> str | None:
        value = self.product.get(key)
        if value is None:
            return None
        value = clean(value)
        return value or None

    def price_text(self) -> str | None:
        current = self.product.get("current_price")
        regular = self.product.get("regular_price")
        discount = self.product.get("discount")

        if current is not None and regular is not None:
            text = f"Hoje ele está por {money(current)}, de {money(regular)}."
        elif current is not None:
            text = f"Hoje ele está por {money(current)}."
        elif regular is not None:
            text = f"O preço cadastrado é {money(regular)}."
        else:
            return None

        if discount not in (None, ""):
            try:
                text += f" Desconto de {float(discount):g}%."
            except Exception:
                text += f" Desconto cadastrado: {discount}."

        return text

    def classify(self, text: str) -> str | None:
        original = clean(text)
        t = original.casefold()

        if not t:
            return None

        if any(k in t for k in (
            "quanto", "preço", "preco", "valor", "custa", "por quanto"
        )):
            return "price"

        if any(k in t for k in (
            "tem cor", "cor ", "tamanho", "numeração", "numeracao",
            "estoque", "disponível", "disponivel"
        )):
            return "availability"

        if any(k in t for k in ("frete", "entrega", "chega", "envio")):
            return "shipping"

        if any(k in t for k in (
            "como usa", "como usar", "funciona", "serve pra", "serve para"
        )):
            return "usage"

        if any(k in t for k in (
            "vou comprar", "quero comprar", "comprei",
            "onde compra", "onde comprar", "manda o link", "link"
        )):
            return "buying_intent"

        if any(k in t for k in (
            "caro", "muito caro", "não vale", "nao vale",
            "dúvida", "duvida"
        )):
            return "objection"

        is_question = (
            "?" in original
            or any(
                t.startswith(x)
                for x in (
                    "tem ", "qual ", "quanto ", "como ",
                    "serve ", "funciona ", "pode ", "vem ", "é "
                )
            )
        )

        if is_question:
            return "direct_question"

        if any(k in t for k in (
            "amei", "lindo", "gostei", "top", "perfeito", "eu quero"
        )):
            return "engagement"

        return None

    def unknown(self, user: str, topic: str) -> str:
        return (
            f"{user}, vi sua pergunta sobre {topic}. "
            "Essa informação não está cadastrada no produto ainda, "
            "então prefiro não te passar algo errado."
        )

    def build_response(
        self,
        user: str,
        text: str,
        category: str,
    ) -> str | None:
        name = self.product_name()
        description = self.known("description")
        additional = self.known("additional_info")
        price = self.price_text()

        if category == "price":
            return (
                f"{user}, sobre o preço do {name}: {price}"
                if price
                else self.unknown(user, "preço")
            )

        if category == "availability":
            searchable = " ".join(
                x for x in (description, additional) if x
            ).casefold()

            if any(k in searchable for k in (
                "cor", "tamanho", "estoque", "dispon"
            )):
                return (
                    f"{user}, sobre disponibilidade do {name}: "
                    f"{additional or description}"
                )
            return self.unknown(user, "cor, tamanho ou disponibilidade")

        if category == "shipping":
            searchable = " ".join(
                x for x in (description, additional) if x
            ).casefold()

            if any(k in searchable for k in (
                "frete", "envio", "entrega"
            )):
                return f"{user}, sobre entrega: {additional or description}"
            return self.unknown(user, "frete ou entrega")

        if category == "usage":
            return (
                f"{user}, sobre como usar o {name}: {description}"
                if description
                else self.unknown(user, "uso do produto")
            )

        if category == "buying_intent":
            parts = [f"{user}, boa! O produto é o {name}."]
            if price:
                parts.append(price)
            if additional:
                parts.append(additional)
            return " ".join(parts)

        if category == "objection":
            parts = [f"{user}, entendo sua dúvida sobre o {name}."]
            if description:
                parts.append(description)
            if price:
                parts.append(price)
            return " ".join(parts)

        if category == "direct_question":
            if description or additional:
                info = " ".join(
                    x for x in (description, additional) if x
                )
                return (
                    f"{user}, vi sua pergunta. "
                    f"Sobre o {name}, o que tenho cadastrado é: {info}"
                )
            return self.unknown(user, "esse detalhe")

        if category == "engagement":
            return f"{user}, valeu! Estamos mostrando o {name} agora."

        return None

    def enqueue_comment(self, user: str, text: str) -> dict | None:
        category = self.classify(text)
        if not category:
            return None

        now = time.time()
        key = (
            clean(user).casefold(),
            clean(text).casefold(),
            category,
        )

        if now - self.recent_keys.get(key, -999) < 30:
            return None

        self.recent_keys[key] = now
        self.recent_keys = {
            k: ts
            for k, ts in self.recent_keys.items()
            if now - ts <= 120
        }

        speech = self.build_response(user, text, category)
        if not speech:
            return None

        item = {
            "type": "reactive",
            "category": category,
            "label": self.LABELS[category],
            "priority": self.PRIORITY[category],
            "user": clean(user),
            "comment": clean(text),
            "speech": speech,
            "created_at": now,
        }

        heapq.heappush(
            self.queue,
            (-item["priority"], next(self.counter), item),
        )
        return item

    def maybe_enqueue_proactive(self, interval: float = 25.0) -> dict | None:
        now = time.time()

        if self.queue or now - self.last_proactive_at < interval:
            return None

        name = self.product_name()
        description = self.known("description")
        additional = self.known("additional_info")
        price = self.price_text()

        if price:
            speech = f"Pra quem chegou agora, estamos mostrando o {name}. {price}"
        elif description:
            speech = f"Pra quem chegou agora, olha só o {name}: {description}"
        elif additional:
            speech = f"Uma informação importante sobre o {name}: {additional}"
        else:
            speech = f"Pra quem chegou agora, o produto ativo é o {name}."

        item = {
            "type": "proactive",
            "category": "proactive",
            "label": self.LABELS["proactive"],
            "priority": self.PRIORITY["proactive"],
            "user": None,
            "comment": None,
            "speech": speech,
            "created_at": now,
        }

        heapq.heappush(
            self.queue,
            (-item["priority"], next(self.counter), item),
        )
        self.last_proactive_at = now
        return item

    def next_speech(self) -> dict | None:
        if not self.queue:
            return None
        _, _, item = heapq.heappop(self.queue)
        return item

    def queue_snapshot(self) -> list[dict]:
        return [item for _, _, item in sorted(self.queue)]

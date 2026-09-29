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


def _sentences(text: str) -> list[str]:
    text = clean(text)
    if not text:
        return []
    parts = re.split(r"(?<=[.!?;])\s+|\n+", text)
    return [clean(part).rstrip(" ;") for part in parts if clean(part)]


class PresenterEngine:
    """Comportamento do apresentador da LIVE.

    A regra central é simples: a LIVE é uma apresentação de produto, não um
    chatbot. Comentários entram numa fila e podem interromper a apresentação
    por pouco tempo; depois de um pequeno bloco de respostas, o apresentador
    volta obrigatoriamente ao produto antes de responder novamente.
    """

    MAX_REACTIVE_BURST = 3
    FORCED_SALES_SECONDS = 30.0
    MAX_REACTIVE_QUEUE = 40
    DUPLICATE_WINDOW_SECONDS = 45.0

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

    TOPIC_KEYWORDS = {
        "garantia": ("garantia", "garantido"),
        "bateria": (
            "bateria", "autonomia", "carga", "carrega", "carregamento",
            "horas", "dias"
        ),
        "compatibilidade": (
            "compatível", "compativel", "android", "iphone", "ios",
            "bluetooth", "aplicativo", "app"
        ),
        "água": (
            "água", "agua", "impermeável", "impermeavel",
            "resistente", "ip67", "ip68"
        ),
        "tamanho": (
            "tamanho", "medida", "medidas", "dimensão", "dimensao",
            "dimensões", "dimensoes", "numeração", "numeracao"
        ),
        "cor": ("cor", "cores"),
        "entrega": ("frete", "entrega", "envio", "prazo", "chega"),
    }

    STOPWORDS = {
        "a", "o", "as", "os", "de", "da", "do", "das", "dos", "e",
        "é", "eh", "em", "um", "uma", "pra", "para", "por", "que",
        "qual", "quais", "como", "tem", "ele", "ela", "isso", "esse",
        "essa", "este", "esta", "me", "eu", "você", "voce"
    }

    def __init__(self, product: dict | None):
        self.product = dict(product or {})
        self.queue = []
        self.counter = itertools.count()
        self.recent_keys = {}

        self.last_proactive_at = 0.0
        self.reactive_streak = 0
        self.forced_sales_until = 0.0
        self.proactive_step = 0
        self.response_step = 0

    def product_name(self) -> str:
        return clean(self.product.get("name")) or "produto"

    @staticmethod
    def _friendly_user(user: str) -> str:
        value = clean(user).lstrip("@")
        if not value:
            return ""
        return value.split()[0]

    def known(self, key: str) -> str | None:
        value = self.product.get(key)
        if value is None:
            return None
        value = clean(value)
        return value or None

    def _short(self, text: str | None, limit: int = 130) -> str | None:
        if not text:
            return None
        pieces = _sentences(text)
        value = pieces[0] if pieces else clean(text)
        if len(value) <= limit:
            return value
        clipped = value[:limit].rsplit(" ", 1)[0].rstrip(" ,.;:")
        return clipped + "."

    def price_text(self) -> str | None:
        current = self.product.get("current_price")
        regular = self.product.get("regular_price")
        discount = self.product.get("discount")

        if current not in (None, "") and regular not in (None, ""):
            text = f"Hoje ele tá por {money(current)}, de {money(regular)}."
        elif current not in (None, ""):
            text = f"Hoje ele tá por {money(current)}."
        elif regular not in (None, ""):
            text = f"Ele tá por {money(regular)}."
        else:
            return None

        if discount not in (None, ""):
            try:
                text += f" Dá {float(discount):g}% de desconto."
            except Exception:
                text += f" E tem {clean(discount)} de desconto."

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
            "tem cor", "cor ", "cores", "tamanho", "numeração", "numeracao",
            "estoque", "disponível", "disponivel"
        )):
            return "availability"

        if any(k in t for k in ("frete", "entrega", "chega", "envio", "prazo")):
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
                    "tem ", "qual ", "quanto ", "como ", "quando ",
                    "serve ", "funciona ", "pode ", "vem ", "é ", "e ",
                    "possui ", "aceita ", "dura "
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

    def _question_topic(self, text: str) -> str | None:
        t = clean(text).casefold()
        for topic, keywords in self.TOPIC_KEYWORDS.items():
            if any(k in t for k in keywords):
                return topic
        return None

    def _description_points(self) -> list[str]:
        points = self.product.get("description_points") or []
        if isinstance(points, list):
            cleaned = [clean(point) for point in points if clean(point)]
            if cleaned:
                return cleaned

        # Compatibilidade com produtos antigos, salvos antes da descrição
        # estruturada em tópicos.
        return _sentences(self.known("description") or "")

    def _all_facts(self) -> list[str]:
        facts = list(self._description_points())
        facts.extend(_sentences(self.known("additional_info") or ""))

        result = []
        seen = set()
        for fact in facts:
            fact = clean(fact)
            key = fact.casefold()
            if fact and key not in seen:
                result.append(fact)
                seen.add(key)
        return result

    def _fact_for_question(self, text: str) -> str | None:
        candidates = self._all_facts()
        if not candidates:
            return None

        t = clean(text).casefold()
        topic = self._question_topic(text)
        query_words = {
            word for word in re.findall(r"[a-záàâãéêíóôõúç0-9]+", t)
            if len(word) >= 3 and word not in self.STOPWORDS
        }

        best = None
        best_score = 0
        for fact in candidates:
            s = fact.casefold()
            score = sum(1 for word in query_words if word in s)

            if topic:
                score += 4 * sum(
                    1 for keyword in self.TOPIC_KEYWORDS[topic] if keyword in s
                )

            if score > best_score:
                best = fact
                best_score = score

        return self._short(best) if best_score > 0 else None

    def _casual_fact(self, fact: str) -> str:
        value = self._short(fact) or clean(fact)
        replacements = (
            (r"^o produto possui\s+", "ele tem "),
            (r"^este produto possui\s+", "ele tem "),
            (r"^possui\s+", "tem "),
            (r"^o produto é compatível com\s+", "funciona com "),
            (r"^é compatível com\s+", "funciona com "),
            (r"^o produto conta com\s+", "ele tem "),
        )
        for pattern, repl in replacements:
            changed = re.sub(pattern, repl, value, flags=re.IGNORECASE)
            if changed != value:
                value = changed
                break
        return clean(value)

    def _natural_reply(self, user: str, fact: str, lead: str | None = None) -> str:
        person = self._friendly_user(user)
        fact = self._casual_fact(fact)

        if person:
            variants = (
                f"{person}, {lead + ' ' if lead else ''}{fact}",
                f"Olha, {person}, {lead + ' ' if lead else ''}{fact}",
                f"{person}, {fact}",
            )
        else:
            variants = (
                f"{lead + ' ' if lead else ''}{fact}",
                f"Olha, {lead + ' ' if lead else ''}{fact}",
                fact,
            )

        value = variants[self.response_step % len(variants)]
        self.response_step += 1
        return clean(value)

    def build_response(
        self,
        user: str,
        text: str,
        category: str,
    ) -> str | None:
        name = self.product_name()
        price = self.price_text()
        matched_fact = self._fact_for_question(text)
        points = self._description_points()

        # Regra do Presenter: se a informação não está disponível, não responde.
        # A pergunta simplesmente não entra na fila de fala.
        if category == "price":
            if not price:
                return None
            person = self._friendly_user(user)
            prefix = f"{person}, " if person else ""
            return clean(f"{prefix}{price}")

        if category in {"availability", "shipping", "direct_question"}:
            if not matched_fact:
                return None
            return self._natural_reply(user, matched_fact)

        if category == "usage":
            if matched_fact:
                return self._natural_reply(user, matched_fact)

            # Para perguntas genéricas como "como funciona?", pode usar um
            # único tópico de descrição, nunca a descrição inteira.
            generic = clean(text).casefold()
            if points and any(k in generic for k in (
                "como funciona", "como usa", "como usar", "serve pra", "serve para"
            )):
                return self._natural_reply(user, points[0])
            return None

        if category == "buying_intent":
            person = self._friendly_user(user)
            prefix = f"{person}, " if person else ""
            if price:
                return clean(f"{prefix}boa! É esse {name} mesmo. {price}")
            return clean(f"{prefix}boa! É esse {name} que eu tô mostrando.")

        if category == "objection":
            person = self._friendly_user(user)
            prefix = f"{person}, " if person else ""
            if matched_fact:
                return clean(f"{prefix}entendo. {matched_fact}")
            if price:
                return clean(f"{prefix}entendo. {price}")
            return None

        if category == "engagement":
            person = self._friendly_user(user)
            if person:
                return f"Boa, {person}! Esse {name} tá legal demais."
            return f"Esse {name} tá legal demais."

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

        if now - self.recent_keys.get(key, -999) < self.DUPLICATE_WINDOW_SECONDS:
            return None

        self.recent_keys[key] = now
        self.recent_keys = {
            k: ts
            for k, ts in self.recent_keys.items()
            if now - ts <= 180
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

        if len(self.queue) > self.MAX_REACTIVE_QUEUE:
            kept = sorted(self.queue)[:self.MAX_REACTIVE_QUEUE]
            self.queue = kept
            heapq.heapify(self.queue)

        return item

    def _sales_fact(self) -> str | None:
        # A fala proativa usa um tópico por vez. Isso evita despejar uma
        # descrição inteira na LIVE e deixa a apresentação mais espontânea.
        facts = self._description_points()
        if not facts:
            facts = _sentences(self.known("additional_info") or "")
        if not facts:
            return None
        index = self.proactive_step % len(facts)
        return self._casual_fact(facts[index])

    def build_proactive(self, now: float | None = None) -> dict:
        now = time.time() if now is None else now
        name = self.product_name()
        fact = self._sales_fact()
        price = self.price_text()

        templates = []

        if fact:
            templates.extend([
                f"Olha esse {name}, gente. {fact}",
                f"Pra quem chegou agora: {fact}",
                f"Outra coisa legal dele: {fact}",
            ])

        if price:
            templates.extend([
                f"E olha o preço: {price}",
                f"Pra quem perguntou valor, {price}",
            ])

        if fact and price:
            templates.append(f"Ó, {fact} E hoje {price.lower()}")

        templates.extend([
            f"Quem tá chegando agora, eu tô mostrando o {name}.",
            f"Vou mostrar mais um pouco desse {name} pra vocês.",
        ])

        speech = templates[self.proactive_step % len(templates)]
        self.proactive_step += 1
        self.last_proactive_at = now

        return {
            "type": "proactive",
            "category": "proactive",
            "label": self.LABELS["proactive"],
            "priority": self.PRIORITY["proactive"],
            "user": None,
            "comment": None,
            "speech": clean(speech),
            "created_at": now,
        }

    def in_forced_sales_window(self, now: float | None = None) -> bool:
        now = time.time() if now is None else now
        if self.forced_sales_until and now >= self.forced_sales_until:
            self.forced_sales_until = 0.0
            self.reactive_streak = 0
            return False
        return now < self.forced_sales_until

    def seconds_until_reactive(self, now: float | None = None) -> int:
        now = time.time() if now is None else now
        if not self.in_forced_sales_window(now):
            return 0
        return max(0, int(round(self.forced_sales_until - now)))

    def can_take_reactive(self, now: float | None = None) -> bool:
        if self.in_forced_sales_window(now):
            return False
        return self.reactive_streak < self.MAX_REACTIVE_BURST

    def next_reactive(self) -> dict | None:
        if not self.queue:
            return None
        _, _, item = heapq.heappop(self.queue)
        return item

    def mark_spoken(
        self,
        item: dict,
        now: float | None = None,
        speech_until: float | None = None,
    ) -> None:
        now = time.time() if now is None else now

        if item.get("type") == "reactive":
            self.reactive_streak += 1
            if self.reactive_streak >= self.MAX_REACTIVE_BURST:
                start = max(now, speech_until or now)
                self.forced_sales_until = start + self.FORCED_SALES_SECONDS
        else:
            # Fala de produto fora da janela forçada quebra uma sequência curta
            # de respostas e impede que a LIVE vire um tira-dúvidas contínuo.
            if not self.in_forced_sales_window(now):
                self.reactive_streak = 0

    def queue_snapshot(self) -> list[dict]:
        return [item for _, _, item in sorted(self.queue)]

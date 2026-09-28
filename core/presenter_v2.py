from __future__ import annotations

import heapq
import itertools
import random
import time

from core.comment_fusion import CommentFusion
from core.comment_intelligence import CommentIntelligence
from core.decision_engine import DecisionEngine
from core.memory_manager import MemoryManager
from core.sales_guard import SalesGuard
from core.silence_watchdog import SilenceWatchdog
from core.speech_planner import SpeechPlanner


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


def as_text(value) -> str:
    if value in (None, "", [], {}):
        return ""
    if isinstance(value, (list, tuple, set)):
        return ", ".join(str(x) for x in value if str(x).strip())
    return str(value).strip()


class PresenterV2:
    """Presenter Behavior V1 — ainda sem LLM/TTS.

    O foco é comportamento, memória, timing, fatos e variedade.
    """

    def __init__(self, product: dict | None):
        self.product = dict(product or {})
        self.guard = SalesGuard(self.product)
        self.memory = MemoryManager()
        self.intelligence = CommentIntelligence()
        self.fusion = CommentFusion(window_seconds=1.4)
        self.decision_engine = DecisionEngine()
        self.planner = SpeechPlanner()
        self.watchdog = SilenceWatchdog(
            target_seconds=8.0,
            hard_seconds=10.0,
        )
        self.queue = []
        self.counter = itertools.count()
        self.recent_keys = {}

    def set_product(self, product: dict | None) -> None:
        self.product = dict(product or {})
        self.guard = SalesGuard(self.product)

    def ingest_comment(self, user: str, text: str) -> dict | None:
        analyzed = self.intelligence.analyze(user, text)
        if not analyzed:
            return None

        now = time.time()
        key = (
            analyzed["user"].casefold(),
            analyzed["comment"].casefold(),
            analyzed["intent"],
        )
        if now - self.recent_keys.get(key, -999) < 20:
            return None

        self.recent_keys[key] = now
        self.recent_keys = {
            k: ts
            for k, ts in self.recent_keys.items()
            if now - ts <= 90
        }

        self.fusion.add(analyzed)
        return analyzed

    def process_pending_comments(self) -> list[dict]:
        created = []
        groups = self.fusion.ready_groups()

        for group in groups:
            decision = self.decision_engine.decide(
                group,
                self.memory.snapshot(),
            )
            plan = self.planner.plan(
                decision,
                self.guard,
                self.memory,
            )
            item = self._render_plan(plan)
            if item:
                heapq.heappush(
                    self.queue,
                    (-item["priority"], next(self.counter), item),
                )
                created.append(item)

        return created

    def maybe_proactive(self) -> dict | None:
        seconds = self.memory.seconds_since_speech()
        if not self.watchdog.should_trigger(
            seconds,
            queue_empty=not self.queue,
        ):
            return None

        topic = self.planner.choose_proactive_topic(
            self.guard,
            self.memory,
        )
        decision = self.decision_engine.proactive(
            topic,
            priority=35 if self.watchdog.urgency(seconds) == "hard" else 30,
        )
        plan = self.planner.plan(
            decision,
            self.guard,
            self.memory,
        )
        item = self._render_plan(plan)

        if item:
            heapq.heappush(
                self.queue,
                (-item["priority"], next(self.counter), item),
            )
        return item

    def next_speech(self) -> dict | None:
        self.process_pending_comments()
        if not self.queue:
            self.maybe_proactive()
        if not self.queue:
            return None

        _, _, item = heapq.heappop(self.queue)
        self.memory.remember_speech(item)
        return item

    def queue_snapshot(self) -> list[dict]:
        return [item for _, _, item in sorted(self.queue)]

    def snapshot(self) -> dict:
        return {
            "memory": self.memory.snapshot(),
            "watchdog": {
                "target_seconds": self.watchdog.target_seconds,
                "hard_seconds": self.watchdog.hard_seconds,
                "status": self.watchdog.urgency(
                    self.memory.seconds_since_speech()
                ),
            },
        }

    def _render_plan(self, plan: dict) -> dict | None:
        intent = plan.get("intent")
        user = plan.get("user")
        name = self.product.get("name") or "produto"
        fact = plan.get("fact")
        speech = None
        cta = plan.get("cta")

        if plan.get("type") == "proactive":
            speech = self._proactive_text(plan, name)
        elif intent == "brand":
            brand = as_text(self.guard.get("brand"))
            speech = (
                f"{user}, a marca é {brand}."
                if brand
                else f"{user}, a marca não está cadastrada aqui pra eu te confirmar com segurança."
            )
        elif intent == "price":
            current = self.product.get("current_price")
            regular = self.product.get("regular_price")
            if current is not None and regular is not None:
                speech = f"{user}, hoje ele está por {brl(current)}, de {brl(regular)}."
            elif current is not None:
                speech = f"{user}, hoje ele está por {brl(current)}."
            elif regular is not None:
                speech = f"{user}, o preço cadastrado é {brl(regular)}."
            else:
                speech = f"{user}, o preço não está cadastrado aqui pra eu te confirmar agora."
        elif intent == "buying_intent":
            speech = f"{user}, boa! Se você quer garantir o {name}, pode finalizar pelo produto fixado na LIVE."
        elif intent == "purchase_confirmation":
            speech = random.choice([
                f"Boa, {user}! Parabéns pela compra.",
                f"{user}, aí sim! Obrigado pela compra.",
                f"Parabéns, {user}! Você garantiu o seu.",
            ])
        elif intent == "engagement":
            speech = random.choice([
                f"Valeu, {user}! Esse {name} tá chamando atenção mesmo.",
                f"{user}, bom demais! Vou continuar mostrando os detalhes dele.",
            ])
        elif intent == "objection":
            speech = self._objection_text(user, name)
        else:
            speech = self._fact_answer(
                user,
                intent,
                name,
                fact,
                fact_label=plan.get("fact_label"),
                comment=plan.get("comment"),
            )

        if not speech:
            return None

        speech = self._append_value_if_useful(
            speech,
            plan,
            name,
        )
        speech = self._append_cta(
            speech,
            cta,
        )

        return {
            "type": plan.get("type"),
            "intent": intent,
            "category": intent,
            "topic": plan.get("topic"),
            "label": plan.get("label"),
            "priority": plan.get("priority", 0),
            "user": user,
            "comment": plan.get("comment"),
            "speech": speech,
            "cta": cta,
            "plan": plan.get("steps", []),
            "resume_topic": plan.get("resume_topic"),
            "created_at": time.time(),
        }

    def _fact_answer(
        self,
        user,
        intent,
        name,
        fact,
        *,
        fact_label=None,
        comment=None,
    ):
        text = as_text(fact)
        labels = {
            "availability": "disponibilidade",
            "compatibility": "compatibilidade",
            "technical_question": "essa especificação",
            "shipping": "frete e entrega",
            "warranty": "garantia",
            "included_items": "o que acompanha",
            "size": "tamanho e medidas",
            "battery": "bateria",
            "usage": "modo de uso",
            "safety_or_critical": "essa informação",
        }
        label = as_text(fact_label) or labels.get(intent, "esse detalhe")
        address = f"{user}, " if user else ""
        question = str(comment or "").casefold()

        if text:
            negative = any(
                marker in text.casefold()
                for marker in ("não ", "nao ", "sem ")
            )
            yes_no_question = any(
                question.startswith(prefix)
                for prefix in (
                    "tem ", "vem ", "possui ", "é ", "e ",
                    "serve ", "funciona ",
                )
            )

            if yes_no_question and not negative:
                return f"{address}tem sim. {label}: {text}."

            return f"{address}{label}: {text}."

        if intent in {"direct_question", "technical_question"}:
            return (
                f"{address}esse detalhe não está cadastrado na ficha do {name}. "
                "Prefiro não te passar informação no chute."
            )

        return (
            f"{address}eu ainda não tenho {label} cadastrado "
            "pra te responder com segurança."
        )

    def _objection_text(self, user, name):
        benefits = as_text(self.guard.get("benefits"))
        current = self.product.get("current_price")
        regular = self.product.get("regular_price")

        parts = [f"{user}, entendi seu ponto sobre o {name}."]

        if benefits:
            parts.append(f"O valor dele está principalmente em {benefits}.")

        if current is not None and regular is not None:
            parts.append(f"Hoje está {brl(current)}, de {brl(regular)}.")

        return " ".join(parts)

    def _append_value_if_useful(self, speech, plan, name):
        if "expand_with_value" not in plan.get("steps", []):
            return speech

        if plan.get("intent") in {
            "brand", "price", "purchase_confirmation",
            "engagement", "buying_intent",
        }:
            return speech

        benefits = as_text(self.guard.get("benefits"))
        if benefits and not self.memory.recently_said_topic(
            "benefits",
            within=30,
        ):
            return f"{speech} E um ponto forte do {name} é {benefits}."

        return speech

    def _append_cta(self, speech, cta):
        if cta == "buy_now":
            return f"{speech} Se fizer sentido pra você, aproveita o produto fixado na LIVE."
        if cta == "soft_close":
            return f"{speech} Dá uma olhada na oferta fixada e vê se encaixa no que você procura."
        if cta == "live_offer":
            offer = self.guard.live_offer()
            if offer:
                return f"{speech} {offer}"
        return speech

    def _proactive_text(self, plan, name):
        topic = plan.get("topic")

        if topic == "benefits":
            value = as_text(self.guard.get("benefits"))
            if value:
                return f"Pra quem tá chegando agora, olha o principal do {name}: {value}."

        if topic == "problems_solved":
            value = as_text(self.guard.get("problems_solved"))
            if value:
                return f"Esse {name} faz sentido principalmente pra quem quer resolver {value}."

        if topic == "differentials":
            value = as_text(self.guard.get("differentials"))
            if value:
                return f"Um diferencial importante desse {name} é {value}."

        if topic == "included_items":
            value = as_text(self.guard.get("included_items"))
            if value:
                return f"E presta atenção no que você recebe com o {name}: {value}."

        if topic == "usage":
            value = as_text(self.guard.get("usage"))
            if value:
                return f"No uso do dia a dia, o {name} funciona assim: {value}."

        if topic == "price":
            current = self.product.get("current_price")
            regular = self.product.get("regular_price")
            if current is not None and regular is not None:
                return f"Olha o valor agora do {name}: {brl(current)}, de {brl(regular)}."
            if current is not None:
                return f"O {name} está por {brl(current)} agora."

        if topic == "cta":
            offer = self.guard.live_offer()
            if offer:
                return f"Pra quem estiver avaliando o {name}, {offer}"

        desc = as_text(self.product.get("description"))
        if desc:
            options = [
                f"Pra quem chegou agora, o {name} é o produto que estamos mostrando. {desc}",
                f"Se você acabou de entrar na LIVE, presta atenção no {name}: {desc}",
                f"Rapidinho pra quem chegou agora: estamos com o {name}. {desc}",
            ]
            return random.choice(options)

        return random.choice([
            f"Pra quem chegou agora, o produto que está na tela é o {name}.",
            f"Se você acabou de entrar, estamos mostrando o {name}.",
        ])

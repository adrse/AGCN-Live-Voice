from __future__ import annotations

import heapq
import itertools
import random
import time

from core.comment_fusion import CommentFusion
from core.comment_intelligence import CommentIntelligence
from core.decision_engine import DecisionEngine
from core.memory_manager import MemoryManager
from core.persuasion_engine import PersuasionEngine
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
        self.persuasion = PersuasionEngine(self.product)
        self.memory = MemoryManager()
        self.intelligence = CommentIntelligence()
        # Benchmark forte responde em poucos segundos. Janela menor preserva
        # fusão de comentários sem deixar a pergunta esperando.
        self.fusion = CommentFusion(window_seconds=0.9)
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
        self.persuasion.set_product(self.product)

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

    def force_proactive(self) -> dict | None:
        """Gera uma fala de produto mesmo quando há comentários na fila.

        Usado pelo runtime durante a janela obrigatória de foco no produto.
        Comentários continuam aguardando, mas não dominam a LIVE.
        """
        topic = self.planner.choose_proactive_topic(
            self.guard,
            self.memory,
        )
        decision = self.decision_engine.proactive(
            topic,
            priority=36,
        )
        plan = self.planner.plan(
            decision,
            self.guard,
            self.memory,
        )
        item = self._render_plan(plan)
        if item:
            self.memory.remember_speech(item)
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

    def test_comment(self, user: str, text: str) -> dict:
        """Laboratório síncrono da conversa, sem precisar iniciar uma LIVE."""
        analyzed = self.intelligence.analyze(user, text)
        if not analyzed:
            return {
                "ok": True,
                "ignored": True,
                "analyzed": None,
                "decision": None,
                "plan": None,
                "speech": None,
                "memory": self.memory.snapshot(),
            }

        group = {
            "primary": analyzed,
            "items": [analyzed],
            "priority": analyzed.get("priority", 0),
            "users": [analyzed.get("user")] if analyzed.get("user") else [],
            "topics": [analyzed.get("topic")] if analyzed.get("topic") else [],
        }
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
            self.memory.remember_speech(item)

        return {
            "ok": True,
            "ignored": not bool(item),
            "analyzed": analyzed,
            "decision": decision,
            "plan": plan,
            "speech": item,
            "memory": self.memory.snapshot(),
        }

    def test_proactive(self) -> dict:
        """Gera uma fala comercial proativa para o laboratório."""
        topic = self.planner.choose_proactive_topic(
            self.guard,
            self.memory,
        )
        decision = self.decision_engine.proactive(
            topic,
            priority=30,
        )
        plan = self.planner.plan(
            decision,
            self.guard,
            self.memory,
        )
        item = self._render_plan(plan)

        if item:
            self.memory.remember_speech(item)

        return {
            "ok": bool(item),
            "topic": topic,
            "speech": item,
            "memory": self.memory.snapshot(),
        }

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
        user = self._display_user(plan)
        name = self.product.get("name") or "produto"
        fact = plan.get("fact")
        speech = None
        cta = plan.get("cta")

        if plan.get("type") == "proactive":
            speech = self._proactive_text(plan, name)
        elif intent == "brand":
            brand = as_text(self.guard.get("brand"))
            if brand:
                speech = (
                    f"{user}, é {brand}."
                    if user
                    else f"É {brand}."
                )
            else:
                speech = None
        elif intent == "price":
            anchor = self.persuasion.price_anchor()
            if anchor:
                speech = f"{user}, {anchor}" if user else anchor
            else:
                speech = None
        elif intent == "buying_intent":
            speech = self.persuasion.buying_intent_response(
                user,
                plan.get("comment") or "",
                memory=self.memory,
            )
            # O CTA já foi aplicado diretamente.
            cta = None
        elif intent == "purchase_confirmation":
            speech = self.persuasion.purchase_celebration(user)
        elif intent == "engagement":
            options = [
                f"Valeu, {user}! Bora continuar.",
                f"Boa, {user}! Fica aí que eu vou mostrando.",
                f"Tamo junto, {user}! Olha só esse produto aqui.",
            ]
            speech = random.choice(options) if user else "Valeu! Bora continuar."
        elif intent == "objection":
            speech = self.persuasion.objection_response(
                user,
                name,
                memory=self.memory,
                comment=plan.get("comment") or "",
            )
        else:
            speech = self._fact_answer(
                user,
                intent,
                name,
                fact,
                fact_items=plan.get("fact_items") or [],
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
        speech = self._append_resume_if_useful(
            speech,
            plan,
            name,
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

    def _display_user(self, plan: dict) -> str:
        users = [
            str(x).strip()
            for x in (plan.get("users") or [])
            if str(x or "").strip()
        ]

        if len(users) >= 2 and plan.get("intent") not in {
            "purchase_confirmation",
            "buying_intent",
        }:
            return " e ".join(users[:2])

        return str(plan.get("user") or "").strip()

    def _append_resume_if_useful(
        self,
        speech: str,
        plan: dict,
        name: str,
    ) -> str:
        # O retorno ao produto acontece como uma fala própria do Presenter.
        # Assim a resposta ao espectador fica curta e natural.
        return speech

    def _casual_fact(self, value) -> str:
        text = as_text(value).strip().rstrip(" .;")
        replacements = (
            ("O produto possui ", "tem "),
            ("Este produto possui ", "tem "),
            ("Possui ", "tem "),
            ("O produto conta com ", "tem "),
            ("É compatível com ", "funciona com "),
        )
        for prefix, replacement in replacements:
            if text.casefold().startswith(prefix.casefold()):
                text = replacement + text[len(prefix):]
                break
        return text

    def _fact_answer(
        self,
        user,
        intent,
        name,
        fact,
        *,
        fact_items=None,
        fact_label=None,
        comment=None,
    ):
        items = [
            self._casual_fact(x)
            for x in (fact_items or [])
            if as_text(x)
        ]
        value = self._casual_fact(fact)
        question = str(comment or "").casefold().strip()
        address = f"{user}, " if user else ""

        # Um fato por resposta. Se o campo tem vários tópicos, nunca despeja
        # a lista inteira no espectador.
        if items:
            value = items[0]

        # Pergunta cuja resposta não está na ficha: silêncio. Ela não entra na
        # fila de fala e a apresentadora continua vendendo o produto.
        if not value:
            return None

        value_fold = value.casefold().strip()
        negative = (
            value_fold in {"não", "nao", "não possui", "nao possui"}
            or value_fold.startswith(("não ", "nao ", "sem "))
        )

        if question.startswith(("tem ", "vem ", "possui ")):
            if negative:
                if value_fold in {"não", "nao"}:
                    return f"{address}não."
                return f"{address}{value}."
            if value.casefold().startswith("tem "):
                tail = value[4:].strip()
                return f"{address}tem sim, {tail}."
            if intent == "warranty":
                if "garantia" in value.casefold():
                    return f"{address}tem sim, {value}."
                return f"{address}tem sim, garantia de {value}."
            return f"{address}tem sim. {value}."

        if question.startswith(("serve ", "funciona ")):
            if negative:
                if value_fold in {"não", "nao"}:
                    return f"{address}não."
                return f"{address}{value}."
            if value.casefold().startswith("funciona "):
                return f"{address}sim, {value}."
            return f"{address}serve sim. {value}."

        if "qual" in question or "quanto" in question or "quantos" in question or "quantas" in question:
            return f"{address}{value}."

        return f"{address}{value}."

    def _objection_text(self, user, name):
        return self.persuasion.objection_response(
            user,
            name,
            memory=self.memory,
        )

    def _append_value_if_useful(self, speech, plan, name):
        # Resposta de comentário é curta. A venda continua em falas próprias,
        # em vez de anexar um mini-pitch a cada pergunta.
        if plan.get("type") == "reactive":
            return speech

        if "expand_with_value" not in plan.get("steps", []):
            return speech

        if plan.get("intent") in {
            "brand",
            "benefits",
            "price",
            "purchase_confirmation",
            "engagement",
            "buying_intent",
        }:
            return speech

        bridge = self.persuasion.value_bridge(
            intent=plan.get("intent"),
            memory=self.memory,
            name=name,
        )
        if bridge:
            return f"{speech} {bridge}"

        return speech

    def _append_cta(self, speech, cta):
        if not cta:
            return speech

        if cta in {"buy_now", "soft_close"}:
            close = self.persuasion.cta(
                cta,
                memory=self.memory,
                allow_urgency=True,
            )
            return f"{speech} {close}" if close else speech

        if cta == "live_offer":
            offer = self.guard.live_offer()
            if offer:
                close = self.persuasion.cta(
                    "after_answer",
                    memory=self.memory,
                    allow_urgency=False,
                )
                return f"{speech} {offer} {close}".strip()

        return speech

    def _proactive_text(self, plan, name):
        topic = plan.get("topic")

        strategic = self.persuasion.proactive_pitch(
            topic,
            name,
            self.memory,
        )
        if strategic:
            return strategic

        if topic == "benefits":
            entries = self.guard.knowledge.entries(
                self.guard.get("benefits")
            )
            if entries:
                value = self._casual_fact(
                    entries[self.memory.proactive_cursor() % len(entries)]
                )
                return random.choice([
                    f"Olha só: {value}.",
                    f"Ó, presta atenção nisso: {value}.",
                    f"Uma coisa boa dele: {value}.",
                ])

        if topic in {"problems_solved", "pain_solution"}:
            problems = as_text(self.guard.get("problems_solved"))
            benefits = as_text(self.guard.get("benefits"))
            if problems and benefits:
                return f"Se você quer resolver {problems}, o {name} entrega {benefits}."
            if problems:
                return f"Esse {name} faz sentido principalmente pra quem quer resolver {problems}."

        if topic == "differentials":
            value = as_text(self.guard.get("differentials"))
            if value:
                return random.choice([
                    f"Ó, uma coisa legal dele é {value}.",
                    f"E olha esse detalhe: {value}.",
                    f"O diferencial aqui é {value}.",
                ])

        if topic in {"included_items", "bundle_value"}:
            value = as_text(self.guard.get("included_items"))
            if value:
                return random.choice([
                    f"E olha o que já vem junto: {value}.",
                    f"Fora que já vem {value}.",
                    f"No kit já vai {value}.",
                ])

        if topic == "usage":
            value = as_text(self.guard.get("usage"))
            if value:
                return random.choice([
                    f"No dia a dia é simples: {value}.",
                    f"Pra usar, é assim: {value}.",
                    f"Na prática funciona assim: {value}.",
                ])

        if topic in {"price", "price_value"}:
            current = self.product.get("current_price")
            regular = self.product.get("regular_price")
            if current is not None and regular is not None:
                return random.choice([
                    f"Olha o preço: de {brl(regular)} por {brl(current)}.",
                    f"Tá {brl(current)} só, e era {brl(regular)}.",
                    f"Agora tá saindo por {brl(current)}. Antes tava {brl(regular)}.",
                ])
            if current is not None:
                return random.choice([
                    f"Tá {brl(current)} agora.",
                    f"Hoje tá saindo por {brl(current)}.",
                    f"Ó, o preço agora é {brl(current)}.",
                ])

        if topic == "cta":
            offer = self.guard.live_offer()
            if offer:
                return f"Pra quem estiver avaliando o {name}, {offer}"

        desc_items = self.guard.knowledge.entries(
            self.product.get("description")
        )
        if desc_items:
            cursor = self.memory.proactive_cursor()
            desc = self._casual_fact(
                desc_items[cursor % len(desc_items)]
            )
            options = [
                f"Ó, uma coisa legal dele: {desc}.",
                f"Olha isso aqui: {desc}.",
                f"E tem mais: {desc}.",
            ]
            return random.choice(options)

        return random.choice([
            f"Pra quem chegou agora, a gente tá com o {name} aqui.",
            f"Se você acabou de entrar, olha só o {name} aqui.",
            f"Quem caiu agora na LIVE, presta atenção no {name}.",
        ])

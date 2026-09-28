"""Presenter V3: mesma lógica de LIVE, fala realizada por Presenter Brain.

Comment Intelligence/Decision/Speech Planner continuam determinísticos.
Qwen/API apenas transformam a missão + fatos em fala natural estruturada.
"""

from __future__ import annotations

import heapq
import itertools
import time
from collections import deque

from core.brain_context_builder import build_brain_context
from core.comment_fusion import CommentFusion
from core.comment_intelligence import CommentIntelligence
from core.decision_engine import DecisionEngine
from core.integration_contracts import BrainProvider, CommentPayload
from core.memory_manager import MemoryManager
from core.sales_guard import SalesGuard
from core.silence_watchdog import SilenceWatchdog
from core.speech_planner import SpeechPlanner


class PresenterV3:
    def __init__(
        self,
        product: dict | None,
        brain: BrainProvider,
    ) -> None:
        self.product = dict(product or {})
        self.brain = brain
        self.guard = SalesGuard(self.product)
        self.memory = MemoryManager()
        self.intelligence = CommentIntelligence()
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
        self.recent_comments = deque(maxlen=12)
        self.recent_facts = deque(maxlen=24)
        self.last_brain_error = ""

    def set_product(self, product: dict | None) -> None:
        self.product = dict(product or {})
        self.guard = SalesGuard(self.product)
        self.recent_facts.clear()

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

        self.recent_comments.append(
            CommentPayload(
                username=analyzed.get("user") or "",
                text=analyzed.get("comment") or "",
            )
        )
        self.fusion.add(analyzed)
        return analyzed

    def process_pending_comments(self) -> list[dict]:
        created = []
        for group in self.fusion.ready_groups():
            decision = self.decision_engine.decide(
                group,
                self.memory.snapshot(),
            )
            plan = self.planner.plan(
                decision,
                self.guard,
                self.memory,
            )
            item = self._generate_item(plan)
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
        item = self._generate_item(plan)
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
        for fact in item.get("used_facts") or []:
            if fact:
                self.recent_facts.append(str(fact))
        return item

    def test_comment(self, user: str, text: str) -> dict:
        analyzed = self.intelligence.analyze(user, text)
        if not analyzed:
            return {
                "ok": False,
                "message": "Comentário sem intenção comercial reconhecida.",
                "analyzed": None,
                "speech": None,
            }

        self.recent_comments.append(
            CommentPayload(
                username=analyzed.get("user") or "",
                text=analyzed.get("comment") or "",
            )
        )
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
        item = self._generate_item(plan)
        if item:
            self.memory.remember_speech(item)
            for fact in item.get("used_facts") or []:
                self.recent_facts.append(str(fact))

        return {
            "ok": bool(item),
            "analyzed": analyzed,
            "decision": decision,
            "plan": plan,
            "speech": item,
            "memory": self.memory.snapshot(),
            "brain_error": self.last_brain_error or None,
        }

    def test_proactive(self) -> dict:
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
        item = self._generate_item(plan)
        if item:
            self.memory.remember_speech(item)
            for fact in item.get("used_facts") or []:
                self.recent_facts.append(str(fact))

        return {
            "ok": bool(item),
            "topic": topic,
            "speech": item,
            "memory": self.memory.snapshot(),
            "brain_error": self.last_brain_error or None,
        }

    def queue_snapshot(self) -> list[dict]:
        return [item for _, _, item in sorted(self.queue)]

    def snapshot(self) -> dict:
        ok, health = self.brain.healthcheck()
        return {
            "memory": self.memory.snapshot(),
            "brain": {
                "name": self.brain.name,
                "healthy": ok,
                "health": health,
                "last_error": self.last_brain_error or None,
            },
            "recent_facts": list(self.recent_facts)[-12:],
            "watchdog": {
                "target_seconds": self.watchdog.target_seconds,
                "hard_seconds": self.watchdog.hard_seconds,
                "status": self.watchdog.urgency(
                    self.memory.seconds_since_speech()
                ),
            },
        }

    def _generate_item(self, plan: dict) -> dict | None:
        mode = (
            "proactive"
            if plan.get("type") == "proactive"
            else "comment_reply"
        )
        context = build_brain_context(
            product=self.product,
            mode=mode,
            decision=plan,
            planner_topic=plan.get("topic") or "",
            memory_snapshot=self.memory.snapshot(),
            recent_comments=list(self.recent_comments),
            recent_facts=list(self.recent_facts),
        )

        try:
            result = self.brain.generate(context)
            self.last_brain_error = ""
        except Exception as exc:
            self.last_brain_error = str(exc)
            return None

        return {
            "type": plan.get("type"),
            "intent": plan.get("intent"),
            "category": plan.get("intent"),
            "topic": result.topic or plan.get("topic"),
            "label": plan.get("label"),
            "priority": plan.get("priority", 0),
            "user": plan.get("user"),
            "comment": plan.get("comment"),
            "speech": result.speech,
            "cta": plan.get("cta"),
            "plan": plan.get("steps", []),
            "resume_topic": (
                result.next_sales_thread
                or plan.get("resume_topic")
            ),
            "next_sales_thread": result.next_sales_thread,
            "used_facts": list(result.used_facts),
            "needs_fact": result.needs_fact,
            "brain": self.brain.name,
            "created_at": time.time(),
        }

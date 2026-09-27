from __future__ import annotations

import random


class SpeechPlanner:
    """Transforma uma decisão em um plano de fala estruturado."""

    PROACTIVE_TOPICS = [
        "benefits",
        "problems_solved",
        "differentials",
        "price",
        "included_items",
        "usage",
        "trust",
        "cta",
        "product_recap",
    ]

    def plan(self, decision: dict, guard, memory) -> dict:
        kind = decision.get("type")
        topic = decision.get("topic")

        if kind == "proactive":
            return self._plan_proactive(decision, guard, memory)

        fact = guard.fact_for_topic(topic)
        has_fact = fact not in (None, "", [], {}, {
            "current_price": None,
            "regular_price": None,
            "discount": None,
        })

        steps = ["answer_directly"]
        if has_fact and decision.get("intent") not in {
            "purchase_confirmation",
            "engagement",
        }:
            steps.append("expand_with_value")

        cta = self._select_cta(decision, guard, memory)
        if cta:
            steps.append("cta")

        resume = decision.get("resume_topic")
        if resume and resume != topic:
            steps.append("resume_previous_topic")

        return {
            **decision,
            "fact": fact,
            "has_fact": has_fact,
            "steps": steps,
            "cta": cta,
            "resume_topic": resume,
        }

    def choose_proactive_topic(self, guard, memory) -> str:
        recent = set(memory.last_topics(limit=5))
        available = []

        mapping = {
            "benefits": guard.get("benefits"),
            "problems_solved": guard.get("problems_solved"),
            "differentials": guard.get("differentials"),
            "price": guard.fact_for_topic("price"),
            "included_items": guard.get("included_items"),
            "usage": guard.get("usage"),
        }

        for topic, fact in mapping.items():
            if fact not in (None, "", [], {}) and topic not in recent:
                available.append(topic)

        if guard.live_offer() and "cta" not in recent:
            available.append("cta")

        if not available:
            available = [
                t for t in self.PROACTIVE_TOPICS
                if t not in recent
            ] or ["product_recap"]

        return random.choice(available)

    def _plan_proactive(self, decision: dict, guard, memory) -> dict:
        topic = decision.get("topic")
        fact = guard.fact_for_topic(topic)

        if topic == "cta":
            fact = guard.live_offer() or guard.grounded_urgency()

        return {
            **decision,
            "fact": fact,
            "has_fact": fact not in (None, "", [], {}),
            "steps": ["proactive_value", "optional_cta"],
            "cta": self._select_cta(decision, guard, memory),
        }

    def _select_cta(self, decision: dict, guard, memory) -> str | None:
        intent = decision.get("intent")

        if intent == "purchase_confirmation":
            return None

        if intent == "buying_intent":
            return "buy_now"

        if intent == "objection":
            return "soft_close"

        if decision.get("type") == "proactive":
            if not memory.recently_used_cta("buy_now", within=25):
                return "buy_now"

        if guard.live_offer() and not memory.recently_used_cta(
            "live_offer",
            within=35,
        ):
            return "live_offer"

        return None

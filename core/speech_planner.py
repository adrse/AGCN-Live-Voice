from __future__ import annotations

import random


class SpeechPlanner:
    """Transforma uma decisão em um plano de fala estruturado."""

    # Sequência inspirada no comportamento das LIVEs analisadas:
    # fala do produto -> uso/benefício -> detalhe -> valor -> urgência real.
    # Não sorteia "quem chegou agora" a cada rodada.
    PROACTIVE_FLOW = [
        "description",
        "benefits",
        "usage",
        "differentials",
        "bundle_value",
        "compatibility",
        "size",
        "battery",
        "pain_solution",
        "price_value",
        "trust",
        "scarcity",
        "social_proof",
    ]

    def plan(self, decision: dict, guard, memory) -> dict:
        kind = decision.get("type")
        topic = decision.get("topic")

        if kind == "proactive":
            return self._plan_proactive(decision, guard, memory)

        fact_packet = guard.fact_for_decision(decision)
        fact = fact_packet.get("value")
        has_fact = bool(fact_packet.get("found"))

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
            "fact_items": fact_packet.get("items") or [],
            "fact_label": fact_packet.get("label"),
            "fact_field": fact_packet.get("field"),
            "has_fact": has_fact,
            "steps": steps,
            "cta": cta,
            "resume_topic": resume,
        }

    def choose_proactive_topic(self, guard, memory) -> str:
        # "Pra quem chegou agora" é recap espaçado, não muleta de toda fala.
        if memory.newcomer_recap_due(
            min_since_start=300,
            cooldown=420,
        ):
            return "newcomer_recap"

        price_fact = guard.fact_for_topic("price")
        has_price = any(
            value not in (None, "", [], {})
            for value in (price_fact or {}).values()
        )

        availability = {
            "description": bool(guard.get("description")),
            "benefits": bool(guard.get("benefits")),
            "usage": bool(guard.get("usage")),
            "differentials": bool(guard.get("differentials")),
            "bundle_value": bool(guard.get("included_items")),
            "compatibility": bool(guard.get("compatibility")),
            "size": bool(guard.get("size")),
            "battery": bool(guard.get("battery")),
            "pain_solution": bool(
                guard.get("problems_solved")
                and guard.get("benefits")
            ),
            "price_value": has_price,
            "trust": bool(
                guard.get("limitations")
                or guard.get("warranty")
            ),
            "scarcity": bool(guard.grounded_urgency()),
            "social_proof": memory.recent_purchase_count(within=180) > 0,
        }

        available = [
            topic
            for topic in self.PROACTIVE_FLOW
            if availability.get(topic)
        ]

        if not available:
            return "product_recap"

        # Anda pela sequência em vez de sortear frases com o mesmo sentido.
        cursor = memory.proactive_cursor()
        start = cursor % len(self.PROACTIVE_FLOW)

        for offset in range(len(self.PROACTIVE_FLOW)):
            topic = self.PROACTIVE_FLOW[
                (start + offset) % len(self.PROACTIVE_FLOW)
            ]
            if not availability.get(topic):
                continue

            # Evita voltar no mesmo assunto logo em seguida.
            if memory.recently_said_topic(topic, within=24):
                continue
            return topic

        # Se todos foram usados recentemente, continua o fluxo no próximo
        # tópico disponível sem travar a LIVE.
        for offset in range(len(self.PROACTIVE_FLOW)):
            topic = self.PROACTIVE_FLOW[
                (start + offset) % len(self.PROACTIVE_FLOW)
            ]
            if availability.get(topic):
                return topic

        return "product_recap"

    def _plan_proactive(self, decision: dict, guard, memory) -> dict:
        topic = decision.get("topic")

        topic_to_fact = {
            "description": "description",
            "benefits": "benefits",
            "usage": "usage",
            "differentials": "differentials",
            "bundle_value": "included_items",
            "compatibility": "compatibility",
            "size": "size",
            "battery": "battery",
            "pain_solution": "problems_solved",
            "trust": "limitations",
        }
        fact = guard.fact_for_topic(
            topic_to_fact.get(topic, topic)
        )

        if topic == "price_value":
            fact = guard.fact_for_topic("price")
        elif topic == "scarcity":
            fact = guard.live_offer() or guard.grounded_urgency()
        elif topic == "social_proof":
            fact = memory.recent_purchase_count(within=180)
        elif topic == "newcomer_recap":
            fact = guard.get("description") or guard.get("benefits")

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
            topic = decision.get("topic")
            if (
                topic in {
                    "price_value",
                    "scarcity",
                    "social_proof",
                }
                and not memory.recently_used_cta(
                    "buy_now",
                    within=45,
                )
            ):
                return "buy_now"
            return None

        # Respostas factuais ficam curtas. Oferta/CTA não é colada em toda
        # pergunta; a venda continua nas falas proativas do Presenter.
        return None

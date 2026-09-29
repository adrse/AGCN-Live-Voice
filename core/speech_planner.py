from __future__ import annotations

import random


class SpeechPlanner:
    """Transforma uma decisão em um plano de fala estruturado."""

    # Sequência informativa. A cada poucos blocos entra um bloco de conversão
    # (valor, dor, urgência real, prova social etc.) para não virar catálogo.
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

    CONVERSION_TOPICS = [
        "scarcity",
        "price_value",
        "social_proof",
        "pain_solution",
        "bundle_value",
    ]

    TACTIC_BY_TOPIC = {
        "description": "desire_visualization",
        "benefits": "benefit_translation",
        "usage": "use_case",
        "differentials": "contrast",
        "bundle_value": "value_stack",
        "compatibility": "objection_preempt",
        "size": "feature_to_benefit",
        "battery": "feature_to_benefit",
        "pain_solution": "pain_relief",
        "price_value": "price_anchor",
        "trust": "risk_reversal",
        "scarcity": "grounded_scarcity",
        "social_proof": "social_proof",
        "newcomer_recap": "fast_recap",
        "product_recap": "fast_recap",
    }

    def plan(self, decision: dict, guard, memory) -> dict:
        kind = decision.get("type")
        topic = decision.get("topic")

        if kind == "proactive":
            return self._plan_proactive(decision, guard, memory)

        fact_packet = guard.fact_for_decision(decision)
        fact = fact_packet.get("value")
        has_fact = bool(fact_packet.get("found"))

        # Resposta factual deve ser curta. A venda continua no fluxo
        # proativo do Presenter; não anexamos mini discurso após cada dúvida.
        steps = ["answer_directly"]

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

        cursor = memory.proactive_cursor()

        # Postura de vendedor: aproximadamente a cada 3 blocos proativos,
        # priorizamos uma técnica de conversão, desde que exista fato real.
        if cursor > 0 and cursor % 3 == 2:
            for topic in self.CONVERSION_TOPICS:
                if not availability.get(topic):
                    continue
                cooldown = 55 if topic == "scarcity" else 42
                if memory.recently_said_topic(topic, within=cooldown):
                    continue
                return topic

        # Anda pela sequência sem voltar no mesmo assunto logo em seguida.
        start = cursor % len(self.PROACTIVE_FLOW)
        for offset in range(len(self.PROACTIVE_FLOW)):
            topic = self.PROACTIVE_FLOW[
                (start + offset) % len(self.PROACTIVE_FLOW)
            ]
            if not availability.get(topic):
                continue
            if memory.recently_said_topic(topic, within=42):
                continue
            return topic

        # Se todos foram usados recentemente, escolhe o próximo disponível,
        # preferindo não repetir exatamente o último tópico.
        recent = memory.last_topics(limit=1)
        last_topic = recent[-1] if recent else None
        for offset in range(len(self.PROACTIVE_FLOW)):
            topic = self.PROACTIVE_FLOW[
                (start + offset) % len(self.PROACTIVE_FLOW)
            ]
            if availability.get(topic) and topic != last_topic:
                return topic

        return available[0]

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

        if topic == "description" and fact:
            items = guard.knowledge.entries(fact)
            if items:
                fact = items[
                    memory.proactive_cursor() % len(items)
                ]

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
            "tactic": self.TACTIC_BY_TOPIC.get(topic, "benefit_translation"),
            "steps": [
                "proactive_value",
                "apply_sales_tactic",
                "optional_cta",
            ],
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
                    "pain_solution",
                    "bundle_value",
                }
                and not memory.recently_used_cta(
                    "buy_now",
                    within=35,
                )
            ):
                return "buy_now"
            return None

        # Comentários factuais não recebem CTA automático. Isso evita que
        # cada resposta vire um mini pitch e deixa a LIVE mais humana.
        return None

from core.brain_context_builder import (
    build_allowed_facts,
    build_brain_context,
    split_presenter_product,
)


def product():
    return {
        "name": "Smart Band X",
        "brand": "Marca X",
        "description": "Pulseira inteligente para acompanhar atividades.",
        "key_benefits": "Tela nítida e bateria duradoura",
        "battery_info": "até 7 dias",
        "current_price": 199.90,
        "regular_price": 249.90,
        "discount": 20,
        "stock": 12,
        "shipping_info": "frete conforme o endereço",
        "live_offer": True,
        "live_offer_text": "oferta válida durante a LIVE",
    }


def test_split_separates_permanent_from_live_conditions():
    permanent, live = split_presenter_product(product())
    assert permanent["name"] == "Smart Band X"
    assert permanent["battery_info"] == "até 7 dias"
    assert "current_price" not in permanent
    assert live["current_price"] == 199.90
    assert live["stock"] == 12


def test_allowed_facts_are_canonical_and_only_from_product():
    facts = build_allowed_facts(product())
    assert "nome: Smart Band X" in facts
    assert "bateria/autonomia: até 7 dias" in facts
    assert "preço atual: R$ 199,90" in facts
    assert "estoque: 12" in facts
    assert not any("IP68" in fact for fact in facts)


def test_context_uses_product_comment_memory_and_allowed_facts():
    context = build_brain_context(
        product=product(),
        mode="comment_reply",
        decision={
            "user": "Maria",
            "comment": "quanto custa?",
            "intent": "price",
            "topic": "price",
            "priority": 96,
        },
        planner_topic="price",
        memory_snapshot={
            "recent_speeches": ["Falamos da bateria."],
            "current_pitch_topic": "battery",
        },
        recent_facts=["bateria/autonomia: até 7 dias"],
    )
    assert context.product["name"] == "Smart Band X"
    assert context.live_conditions["current_price"] == 199.90
    assert context.comment.username == "Maria"
    assert context.comment.text == "quanto custa?"
    assert context.sales_thread == "battery"
    assert "preço atual: R$ 199,90" in context.allowed_facts
    assert context.recent_facts == ["bateria/autonomia: até 7 dias"]

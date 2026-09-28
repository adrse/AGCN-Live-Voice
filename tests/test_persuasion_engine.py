from core.memory_manager import MemoryManager
from core.persuasion_engine import PersuasionEngine
from core.presenter_v2 import PresenterV2


def test_scarcity_is_only_used_when_stock_or_offer_exists():
    engine = PersuasionEngine({
        "name": "Produto X",
        "stock": None,
        "live_offer": False,
        "coupon": "",
        "promotion_note": "",
    })
    memory = MemoryManager()
    assert engine.grounded_urgency(memory) == ""


def test_grounded_stock_scarcity():
    engine = PersuasionEngine({
        "name": "Produto X",
        "stock": 3,
    })
    memory = MemoryManager()
    text = engine.grounded_urgency(memory)
    assert "3" in text
    assert any(word in text.casefold() for word in ("unidade", "restam", "tem 3"))
    assert "estoque informado" not in text.casefold()


def test_price_anchor_uses_real_difference():
    engine = PersuasionEngine({
        "current_price": 59.90,
        "regular_price": 129.90,
    })
    text = engine.price_anchor()
    assert "59,90" in text
    assert "129,90" in text
    assert "valor de referência cadastrado" not in text.casefold()


def test_purchase_confirmation_becomes_real_social_proof():
    memory = MemoryManager()
    memory.remember_speech({
        "speech": "Parabéns pela compra",
        "topic": "purchase",
        "intent": "purchase_confirmation",
        "cta": None,
        "user": "Ana",
        "type": "reactive",
    })
    engine = PersuasionEngine({"name": "Produto X"})
    proof = engine.social_proof(memory)
    assert any(word in proof.casefold() for word in ("compra", "levando", "garantindo"))
    assert memory.recent_purchase_count() == 1


def test_buying_intent_gets_direct_cta():
    presenter = PresenterV2({
        "name": "Mop 14L",
        "current_price": 44.89,
        "regular_price": 99.90,
        "stock": 5,
        "key_benefits": "centrifuga sem exigir torcer o refil com as mãos",
    })

    analyzed = presenter.intelligence.analyze(
        "Joana",
        "eu quero, como compra?",
    )
    assert analyzed is not None

    decision = presenter.decision_engine.decide(
        {
            "primary": analyzed,
            "items": [analyzed],
            "priority": analyzed["priority"],
            "users": ["Joana"],
            "topics": [analyzed["topic"]],
        },
        presenter.memory.snapshot(),
    )
    plan = presenter.planner.plan(
        decision,
        presenter.guard,
        presenter.memory,
    )
    item = presenter._render_plan(plan)

    assert item is not None
    assert "produto fixado" in item["speech"].casefold()
    assert "5" in item["speech"]


def test_objection_reframes_value_without_inventing():
    presenter = PresenterV2({
        "name": "Conjunto de Frigideiras",
        "current_price": 59.90,
        "regular_price": 129.90,
        "key_benefits": "revestimento antiaderente e três tamanhos no conjunto",
        "problems_solved": "ter opções de tamanho para diferentes preparos",
    })

    speech = presenter.persuasion.objection_response(
        "Maria",
        "Conjunto de Frigideiras",
        memory=presenter.memory,
    )

    assert "59,90" in speech
    assert "129,90" in speech
    assert "antiaderente" in speech
    assert "estoque" not in speech.casefold()


def test_human_buying_intent_avoids_corporate_language():
    presenter = PresenterV2({
        "name": "Produto X",
        "stock": 5,
    })
    result = presenter.test_comment(
        "Joana",
        "eu quero",
    )
    speech = result["speech"]["speech"].casefold()
    assert "joana" in speech
    assert "5" in speech
    assert "condição cadastrada" not in speech
    assert "estoque informado" not in speech
    assert "se fizer sentido" not in speech


def test_price_objection_sounds_short_and_oral():
    presenter = PresenterV2({
        "name": "Produto X",
        "current_price": 59.90,
        "regular_price": 129.90,
    })
    result = presenter.test_comment(
        "Maria",
        "tá caro",
    )
    speech = result["speech"]["speech"].casefold()
    assert "59,90" in speech
    assert "129,90" in speech
    assert "eu entendo a sua dúvida" not in speech
    assert "valor de referência cadastrado" not in speech

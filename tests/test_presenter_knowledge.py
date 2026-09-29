from core.comment_intelligence import CommentIntelligence
from core.product_knowledge import ProductKnowledge
from core.presenter_v2 import PresenterV2
from core.sales_guard import SalesGuard


def test_product_knowledge_finds_power_from_additional_info():
    knowledge = ProductKnowledge({
        "name": "Bifeteira Chapa 30x60",
        "additional_info": (
            "Potência: 3000W; Material: Aço inox; "
            "Dimensões: 30 x 60 cm; Voltagem: 220V"
        ),
    })

    packet = knowledge.resolve(
        intent="technical_question",
        topic="technical",
        comment="qual a potência dela?",
    )

    assert packet["found"] is True
    assert "3000" in str(packet["value"])


def test_comment_intelligence_recognizes_technical_question():
    item = CommentIntelligence().analyze(
        "Ana",
        "qual a potência dela?",
    )
    assert item is not None
    assert item["intent"] == "technical_question"


def test_missing_fact_is_not_invented():
    knowledge = ProductKnowledge({
        "name": "Produto genérico",
        "description": "Produto para uso doméstico.",
    })

    packet = knowledge.resolve(
        intent="technical_question",
        topic="technical",
        comment="qual a voltagem?",
    )

    assert packet["found"] is False
    assert packet["value"] is None


def test_presenter_answers_grounded_technical_fact():
    presenter = PresenterV2({
        "name": "Bifeteira Chapa 30x60",
        "additional_info": "Potência: 3000W; Material: Aço inox",
        "key_benefits": "boa área para preparo de lanches",
    })

    analyzed = presenter.intelligence.analyze(
        "Carlos",
        "qual a potência dela?",
    )
    assert analyzed is not None

    decision = presenter.decision_engine.decide(
        {
            "primary": analyzed,
            "items": [analyzed],
            "priority": analyzed["priority"],
            "users": ["Carlos"],
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
    assert "3000" in item["speech"]


def test_high_stock_alone_does_not_create_scarcity():
    guard = SalesGuard({
        "name": "Produto X",
        "stock": 30,
        "live_offer": False,
    })
    assert guard.grounded_urgency() == []
    assert guard.can_claim("scarcity") is False


def test_low_real_stock_can_create_grounded_scarcity():
    guard = SalesGuard({
        "name": "Produto X",
        "stock": 3,
        "live_offer": False,
    })
    assert "stock:3" in guard.grounded_urgency()
    assert guard.can_claim("scarcity") is True

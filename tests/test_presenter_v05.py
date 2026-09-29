from core.comment_intelligence import CommentIntelligence
from core.memory_manager import MemoryManager
from core.presenter_v2 import PresenterV2
from core.sales_guard import SalesGuard
from core.silence_watchdog import SilenceWatchdog


def test_comment_intelligence_brand():
    ci = CommentIntelligence()
    item = ci.analyze("Maria", "qual a marca dele?")
    assert item["intent"] == "brand"
    assert item["priority"] == 86


def test_buying_intent_has_high_priority():
    ci = CommentIntelligence()
    item = ci.analyze("João", "eu quero, como compra?")
    assert item["intent"] == "buying_intent"
    assert item["priority"] >= 95


def test_sales_guard_never_invents_urgency():
    guard = SalesGuard({
        "name": "Produto X",
        "stock": None,
        "live_offer": False,
    })
    assert guard.grounded_urgency() == []
    assert guard.can_claim("scarcity") is False
    assert guard.can_claim("live_exclusive") is False


def test_sales_guard_allows_grounded_urgency():
    guard = SalesGuard({
        "name": "Produto X",
        "stock": 3,
        "live_offer": True,
        "live_offer_text": "Preço especial confirmado durante esta LIVE.",
    })
    assert "stock:3" in guard.grounded_urgency()
    assert guard.can_claim("scarcity") is True
    assert guard.can_claim("live_exclusive") is True


def test_watchdog_target():
    watchdog = SilenceWatchdog(target_seconds=8, hard_seconds=10)
    assert watchdog.should_trigger(7.9, True) is False
    assert watchdog.should_trigger(8.0, True) is True
    assert watchdog.urgency(10.0) == "hard"


def test_presenter_answers_brand_directly():
    presenter = PresenterV2({
        "id": "x",
        "name": "Relógio Teste",
        "brand": "AGCN",
    })
    presenter.ingest_comment("Maria", "qual a marca dele?")
    groups = presenter.fusion.ready_groups(force=True)
    assert groups
    decision = presenter.decision_engine.decide(
        groups[0],
        presenter.memory.snapshot(),
    )
    plan = presenter.planner.plan(
        decision,
        presenter.guard,
        presenter.memory,
    )
    item = presenter._render_plan(plan)
    speech = item["speech"].casefold()
    assert "agcn" in speech
    assert "cadastr" not in speech
    assert len(speech) < 80


def test_memory_records_topic():
    memory = MemoryManager()
    memory.remember_speech({
        "speech": "Teste",
        "topic": "price",
        "intent": "price",
        "type": "reactive",
    })
    assert memory.current_topic == "price"
    assert memory.seconds_since_speech() < 1

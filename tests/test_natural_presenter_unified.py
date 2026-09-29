import time

from core.brain_context_builder import build_allowed_facts
from core.comment_intelligence import CommentIntelligence
from core.integration_contracts import BrainResult
from core.presenter_v3 import PresenterV3
from core.product_store import ProductStore
from core.runtime import AGCNVoiceRuntime


class CountingBrain:
    name = "counting-brain"

    def __init__(self):
        self.calls = 0

    def healthcheck(self):
        return True, "ok"

    def generate(self, context):
        self.calls += 1
        fact = context.allowed_facts[0] if context.allowed_facts else None
        return BrainResult(
            speech="Resposta curta.",
            topic=context.planner_topic or "test",
            used_facts=[fact] if fact else [],
            needs_fact=False,
            next_sales_thread="benefits",
        )


def test_battery_duration_is_not_price():
    result = CommentIntelligence().analyze(
        "Maria",
        "quanto dura a bateria?",
    )
    assert result is not None
    assert result["intent"] == "battery"
    assert result["topic"] == "battery"


def test_unknown_fact_is_silently_ignored_before_brain():
    brain = CountingBrain()
    presenter = PresenterV3(
        {
            "name": "SmartBand X",
            "description": "Tela AMOLED",
        },
        brain,
    )

    result = presenter.test_comment(
        "Ana",
        "tem GPS integrado?",
    )

    assert result["ok"] is True
    assert result["ignored"] is True
    assert result["speech"] is None
    assert brain.calls == 0


def test_description_points_become_separate_allowed_facts():
    facts = build_allowed_facts({
        "name": "SmartBand X",
        "description": (
            "Tela AMOLED\n"
            "Bateria de até 6 dias\n"
            "Recebe notificações"
        ),
    })

    descriptions = [
        fact for fact in facts
        if fact.startswith("descrição:")
    ]
    assert descriptions == [
        "descrição: Tela AMOLED",
        "descrição: Bateria de até 6 dias",
        "descrição: Recebe notificações",
    ]


def test_runtime_forces_thirty_second_product_window(tmp_path):
    store = ProductStore(tmp_path / "products.json")
    store.add(
        name="Produto Teste",
        description="Ponto um\nPonto dois",
        key_benefits="Benefício real",
    )
    runtime = AGCNVoiceRuntime(
        store,
        brain_provider=CountingBrain(),
    )

    start = time.time() + 2
    runtime.reactive_streak = runtime.MAX_REACTIVE_BURST
    runtime._schedule_product_window_after(start)

    assert runtime.MAX_REACTIVE_BURST == 3
    assert runtime.FORCED_PRODUCT_SECONDS == 30.0
    assert runtime._product_window_active(start + 0.1) is True
    remaining = runtime._seconds_until_comments(start + 0.1)
    assert 29 <= remaining <= 30

    assert runtime._product_window_active(start + 30.1) is False
    assert runtime.reactive_streak == 0
    runtime.close()

import time

from core.brain_context_builder import build_allowed_facts, build_brain_context
from core.comment_intelligence import CommentIntelligence
from core.integration_contracts import BrainResult
from core.memory_manager import MemoryManager
from core.sales_guard import SalesGuard
from core.speech_planner import SpeechPlanner
from core.presenter_v2 import PresenterV2
from core.presenter_v3 import PresenterV3
from core.product_store import ProductStore
from core.runtime import AGCNVoiceRuntime


class CountingBrain:
    name = "counting-brain"

    def __init__(self):
        self.calls = 0
        self.modes = []

    def healthcheck(self):
        return True, "ok"

    def generate(self, context):
        self.calls += 1
        self.modes.append(context.mode)
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


def test_comment_can_wait_as_plan_without_spending_brain():
    brain = CountingBrain()
    presenter = PresenterV3(
        {
            "name": "SmartBand X",
            "battery_info": "até 6 dias",
        },
        brain,
    )
    presenter.fusion.window_seconds = 0

    presenter.ingest_comment(
        "Maria",
        "quanto dura a bateria?",
    )
    added = presenter.collect_pending_comments()

    assert added == 1
    assert brain.calls == 0
    assert len(presenter.plan_queue) == 1

    created = presenter.process_pending_comments(max_generate=1)
    assert len(created) == 1
    assert brain.calls == 1
    assert brain.modes == ["comment_reply"]


def test_conversion_slot_prefers_real_scarcity_when_available():
    planner = SpeechPlanner()
    memory = MemoryManager()
    memory.proactive_turns = 2
    guard = SalesGuard({
        "name": "Produto X",
        "description": "Descrição real",
        "current_price": 49.90,
        "regular_price": 99.90,
        "stock": 4,
    })

    topic = planner.choose_proactive_topic(guard, memory)

    assert topic == "scarcity"


def test_proactive_plan_exposes_sales_tactic():
    planner = SpeechPlanner()
    memory = MemoryManager()
    guard = SalesGuard({
        "name": "Produto X",
        "current_price": 49.90,
        "regular_price": 99.90,
    })
    decision = {
        "type": "proactive",
        "intent": "proactive",
        "topic": "price_value",
        "priority": 30,
        "user": None,
        "comment": None,
    }

    plan = planner.plan(decision, guard, memory)

    assert plan["tactic"] == "price_anchor"


def test_recent_purchase_count_becomes_authorized_social_proof():
    context = build_brain_context(
        product={"name": "Produto X"},
        mode="proactive",
        decision={"type": "proactive", "topic": "social_proof"},
        planner_topic="social_proof",
        memory_snapshot={
            "recent_purchase_count": 2,
            "recent_speeches": [],
        },
    )

    assert "compras confirmadas recentemente: 2" in context.allowed_facts


def test_benefits_and_problems_are_atomic_but_included_items_stay_grouped():
    facts = build_allowed_facts({
        "name": "Fone X",
        "key_benefits": "Áudio claro\nSem fio\nConfortável",
        "problems_solved": "Ficar preso a fios\nChamadas com áudio ruim",
        "included_items": "Fone; estojo; cabo",
    })

    benefits = [x for x in facts if x.startswith("benefícios:")]
    problems = [x for x in facts if x.startswith("problemas que resolve:")]
    included = [x for x in facts if x.startswith("itens inclusos:")]

    assert benefits == [
        "benefícios: Áudio claro",
        "benefícios: Sem fio",
        "benefícios: Confortável",
    ]
    assert problems == [
        "problemas que resolve: Ficar preso a fios",
        "problemas que resolve: Chamadas com áudio ruim",
    ]
    assert included == ["itens inclusos: Fone; estojo; cabo"]


def test_benefit_turn_exposes_only_selected_subset_to_brain():
    planner = SpeechPlanner()
    memory = MemoryManager()
    memory.proactive_turns = 1
    product = {
        "name": "Fone X",
        "key_benefits": (
            "Áudio claro\n"
            "Sem fio\n"
            "Confortável\n"
            "Pareamento fácil\n"
            "Estojo compacto"
        ),
    }
    guard = SalesGuard(product)
    decision = {
        "type": "proactive",
        "intent": "proactive",
        "topic": "benefits",
        "priority": 30,
        "user": None,
        "comment": None,
    }

    plan = planner.plan(decision, guard, memory)
    selected = plan["selected_facts"]["key_benefits"]

    assert 1 <= len(selected) <= 3
    assert len(selected) < 5

    context = build_brain_context(
        product=product,
        mode="proactive",
        decision=plan,
        planner_topic="benefits",
        memory_snapshot=memory.snapshot(),
    )
    visible_benefits = [
        x for x in context.allowed_facts
        if x.startswith("benefícios:")
    ]

    assert visible_benefits == [
        f"benefícios: {item}"
        for item in selected
    ]


def test_pain_solution_turn_limits_problems_and_supporting_benefits():
    planner = SpeechPlanner()
    memory = MemoryManager()
    memory.proactive_turns = 2
    product = {
        "name": "Fone X",
        "key_benefits": "Sem fio\nÁudio claro\nConfortável",
        "problems_solved": (
            "Ficar preso a fios\n"
            "Chamadas com áudio ruim\n"
            "Desconforto em uso prolongado"
        ),
    }
    guard = SalesGuard(product)
    decision = {
        "type": "proactive",
        "intent": "proactive",
        "topic": "pain_solution",
        "priority": 30,
        "user": None,
        "comment": None,
    }

    plan = planner.plan(decision, guard, memory)
    context = build_brain_context(
        product=product,
        mode="proactive",
        decision=plan,
        planner_topic="pain_solution",
        memory_snapshot=memory.snapshot(),
    )

    visible_problems = [
        x for x in context.allowed_facts
        if x.startswith("problemas que resolve:")
    ]
    visible_benefits = [
        x for x in context.allowed_facts
        if x.startswith("benefícios:")
    ]

    assert 1 <= len(visible_problems) <= 2
    assert 1 <= len(visible_benefits) <= 2


def test_legacy_presenter_also_ignores_unknown_question():
    presenter = PresenterV2({
        "name": "SmartBand X",
        "description": "Tela AMOLED",
    })

    result = presenter.test_comment(
        "Maria",
        "tem GPS integrado?",
    )

    assert result["speech"] is None
    assert result["ok"] is False


def test_legacy_presenter_known_answer_is_natural_without_internal_language():
    presenter = PresenterV2({
        "name": "SmartBand X",
        "warranty": "1 ano",
    })

    result = presenter.test_comment(
        "Maria",
        "tem garantia?",
    )

    speech = (result.get("speech") or {}).get("speech", "").casefold()
    assert speech
    assert "cadastro" not in speech
    assert "cadastrad" not in speech
    assert "ficha" not in speech
    assert "sistema" not in speech



def test_direct_commercial_question_can_interrupt_proactive_speech(tmp_path):
    store = ProductStore(tmp_path / "products.json")
    store.add(
        name="Produto Teste",
        description="Produto cadastrado.",
        current_price="49,90",
    )
    runtime = AGCNVoiceRuntime(store)
    runtime.monitor = type(
        "ActiveMonitor",
        (),
        {
            "snapshot": lambda self: {
                "monitoring": True,
                "status": "ativo",
            },
            "stop": lambda self: {"ok": True},
        },
    )()

    runtime.current_speech = {
        "type": "proactive",
        "priority": 30,
        "speech": "fala proativa",
    }
    runtime.current_speech_until = time.time() + 20
    runtime.presenter.fusion.window_seconds = 0
    runtime.presenter.ingest_comment("Maria", "quanto custa?")

    with runtime.lock:
        runtime._tick_presenter_locked()

    assert runtime.current_speech["type"] == "reactive"
    assert runtime.current_speech["intent"] == "price"
    runtime.close()

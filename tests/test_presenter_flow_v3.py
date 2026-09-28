from core.comment_intelligence import CommentIntelligence
from core.presenter_v2 import PresenterV2
from core.speech_planner import SpeechPlanner
from core.sales_guard import SalesGuard


def test_benefits_questions_are_understood():
    intelligence = CommentIntelligence()

    for text in (
        "quais benefícios?",
        "benefícios quais?",
        "qual o benefício?",
        "o que ele tem de bom?",
    ):
        result = intelligence.analyze("Cliente", text)
        assert result is not None
        assert result["intent"] == "benefits"
        assert result["topic"] == "benefits"


def test_benefits_answer_uses_only_part_of_registered_list():
    presenter = PresenterV2({
        "name": "Xiaomi Watch",
        "key_benefits": (
            "bateria dura até 18 dias\n"
            "controle de música pelo relógio\n"
            "monitoramento de atividades físicas"
        ),
    })

    result = presenter.test_comment(
        "Ana",
        "quais benefícios?",
    )
    speech = result["speech"]["speech"].casefold()

    assert "não tenho" not in speech
    found = sum(
        item in speech
        for item in (
            "bateria dura até 18 dias",
            "controle de música",
            "monitoramento de atividades",
        )
    )
    assert 1 <= found <= 2


def test_proactive_flow_talks_about_product_before_newcomer_recap():
    presenter = PresenterV2({
        "name": "Xiaomi Watch",
        "description": "relógio inteligente para uso diário",
        "key_benefits": "bateria dura até 18 dias\nrecebe notificações",
        "usage_info": "conecta ao celular pelo aplicativo",
        "differentials": "tela AMOLED",
        "included_items": "relógio\ncarregador",
        "battery_info": "até 18 dias de autonomia",
        "current_price": 199.90,
    })

    outputs = []
    topics = []
    for _ in range(6):
        result = presenter.test_proactive()
        topics.append(result["topic"])
        outputs.append(result["speech"]["speech"].casefold())

    assert "newcomer_recap" not in topics
    assert all("pra quem chegou agora" not in speech for speech in outputs)
    assert any(
        topic in {
            "description",
            "benefits",
            "usage",
            "differentials",
            "bundle_value",
            "battery",
            "price_value",
        }
        for topic in topics
    )


def test_newcomer_recap_only_after_time_and_then_cooldown():
    presenter = PresenterV2({
        "name": "Xiaomi Watch",
        "key_benefits": "bateria dura até 18 dias",
    })

    assert presenter.memory.newcomer_recap_due() is False

    presenter.memory.live_started_at -= 301
    planner = SpeechPlanner()
    topic = planner.choose_proactive_topic(
        SalesGuard(presenter.product),
        presenter.memory,
    )
    assert topic == "newcomer_recap"

    result = presenter.test_proactive()
    assert result["topic"] == "newcomer_recap"

    next_topic = planner.choose_proactive_topic(
        SalesGuard(presenter.product),
        presenter.memory,
    )
    assert next_topic != "newcomer_recap"


def test_product_list_items_stay_separate_for_proactive_speech():
    presenter = PresenterV2({
        "name": "Relógio X",
        "key_benefits": (
            "bateria dura até 18 dias\n"
            "GPS integrado\n"
            "resistência 5ATM"
        ),
    })

    result = presenter.test_proactive()
    speech = result["speech"]["speech"].casefold()

    # A fala usa um fato por vez em vez de despejar todo o cadastro.
    occurrences = sum(
        item in speech
        for item in (
            "bateria dura até 18 dias",
            "gps integrado",
            "resistência 5atm",
        )
    )
    assert occurrences == 1

from core.presenter_v2 import PresenterV2
from core.runtime import AGCNVoiceRuntime
from core.product_store import ProductStore

import tempfile
import time
from pathlib import Path


def test_unknown_question_is_silently_ignored():
    presenter = PresenterV2({
        "name": "SmartBand X",
        "description": "Tela AMOLED\nBateria de até 6 dias",
    })

    result = presenter.test_comment(
        "Ana",
        "tem GPS integrado?",
    )

    assert result["ok"] is True
    assert result["ignored"] is True
    assert result["speech"] is None


def test_known_warranty_answer_is_short_and_informal():
    presenter = PresenterV2({
        "name": "SmartBand X",
        "warranty": "1 ano",
    })

    result = presenter.test_comment(
        "Maria",
        "tem garantia?",
    )

    assert result["ignored"] is False
    speech = result["speech"]["speech"].casefold()
    assert "maria" in speech
    assert "tem sim" in speech
    assert "garantia" in speech
    assert "1 ano" in speech
    assert "cadastr" not in speech
    assert "ficha" not in speech
    assert len(speech) < 120


def test_description_proactive_says_only_one_registered_point():
    presenter = PresenterV2({
        "name": "SmartBand X",
        "description": (
            "Tela AMOLED\n"
            "Bateria de até 6 dias\n"
            "Recebe notificações do celular"
        ),
    })

    result = presenter.test_proactive()
    speech = result["speech"]["speech"].casefold()

    found = sum(
        point in speech
        for point in (
            "tela amoled",
            "bateria de até 6 dias",
            "recebe notificações do celular",
        )
    )
    assert found == 1


def test_factual_reply_does_not_append_sales_pitch_or_cta():
    presenter = PresenterV2({
        "name": "SmartBand X",
        "battery_info": "até 6 dias",
        "key_benefits": "Tela AMOLED\nMonitoramento de sono",
        "live_offer": True,
        "live_offer_text": "Oferta especial da LIVE",
    })

    result = presenter.test_comment(
        "João",
        "quanto dura a bateria?",
    )

    speech = result["speech"]["speech"].casefold()
    assert "6 dias" in speech
    assert "oferta especial" not in speech
    assert "tela amoled" not in speech
    assert "monitoramento de sono" not in speech


def test_runtime_product_window_is_thirty_seconds():
    with tempfile.TemporaryDirectory() as tmp:
        store = ProductStore(Path(tmp) / "products.json")
        runtime = AGCNVoiceRuntime(store=store)

        start = time.time() + 5
        runtime.reactive_streak = runtime.MAX_REACTIVE_BURST
        runtime._schedule_product_window_after(start)

        assert runtime._product_window_active(start + 0.1) is True
        remaining = runtime._seconds_until_comments(start + 0.1)
        assert 29 <= remaining <= 30

        assert runtime._product_window_active(
            start + runtime.FORCED_PRODUCT_SECONDS + 0.1
        ) is False
        assert runtime.reactive_streak == 0

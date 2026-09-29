from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.presenter_v2 import PresenterV2
from core.product_store import ProductStore
from core.runtime import AGCNVoiceRuntime


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    product = {
        "name": "SmartBand Teste",
        "description": (
            "Tela AMOLED\n"
            "Bateria de até 6 dias\n"
            "Recebe notificações do celular"
        ),
        "battery_info": "até 6 dias",
        "warranty": "1 ano",
        "key_benefits": "Tela AMOLED\nMonitoramento de sono",
        "live_offer": True,
        "live_offer_text": "Oferta especial da LIVE",
    }

    presenter = PresenterV2(product)

    unknown = presenter.test_comment("Ana", "tem GPS integrado?")
    check(
        unknown.get("ignored") is True and unknown.get("speech") is None,
        "Pergunta desconhecida deveria ser ignorada silenciosamente.",
    )

    warranty = presenter.test_comment("Maria", "tem garantia?")
    warranty_text = (((warranty.get("speech") or {}).get("speech") or "")).casefold()
    check(
        "tem sim" in warranty_text and "garantia" in warranty_text and "1 ano" in warranty_text,
        "Garantia conhecida não gerou resposta curta/natural.",
    )
    check(
        "cadastr" not in warranty_text and "ficha" not in warranty_text,
        "Resposta expôs linguagem interna.",
    )

    battery = presenter.test_comment("João", "quanto dura a bateria?")
    battery_text = (((battery.get("speech") or {}).get("speech") or "")).casefold()
    check("6 dias" in battery_text, "Bateria conhecida não foi respondida.")
    check(
        "oferta especial" not in battery_text
        and "monitoramento de sono" not in battery_text,
        "Resposta factual ficou grande ou recebeu pitch/CTA automático.",
    )

    presenter2 = PresenterV2(product)
    proactive = presenter2.test_proactive()
    proactive_text = (((proactive.get("speech") or {}).get("speech") or "")).casefold()
    description_hits = sum(
        point in proactive_text
        for point in (
            "tela amoled",
            "bateria de até 6 dias",
            "recebe notificações do celular",
        )
    )
    check(
        description_hits == 1,
        "Fala proativa deveria usar somente um ponto de descrição.",
    )

    with tempfile.TemporaryDirectory() as tmp:
        store = ProductStore(Path(tmp) / "products.json")
        runtime = AGCNVoiceRuntime(store=store)
        start = time.time() + 1
        runtime.reactive_streak = runtime.MAX_REACTIVE_BURST
        runtime._schedule_product_window_after(start)
        check(
            runtime._product_window_active(start + 0.1),
            "Janela obrigatória de produto não foi ativada.",
        )
        remaining = runtime._seconds_until_comments(start + 0.1)
        check(
            29 <= remaining <= 30,
            "Janela de produto deveria durar aproximadamente 30 segundos.",
        )

    print("SMOKE OK — Natural Presenter V0.6.1")


if __name__ == "__main__":
    main()

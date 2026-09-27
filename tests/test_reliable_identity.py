from core.product_research_v054 import ProductResearchEngineV054


def test_generic_fan_does_not_invent_brand_or_model():
    engine = ProductResearchEngineV054()
    title = (
        "120W 6 Hélices Ventilador De Teto Potente Controle Remoto "
        "LED Regulável 3 cores E27 Silencio Inteligente Ventilador Forte"
    )

    model = engine._model_from_title(title)
    category = engine._category_from_title(title)
    brand = engine._brand_from_title_if_strong(
        title,
        model=model,
        category=category,
    )

    assert model == ""
    assert brand == ""
    assert category == "Ventilador de teto"


def test_arno_title_can_recover_model_and_brand_conservatively():
    engine = ProductResearchEngineV054()
    title = (
        "Fritadeira Elétrica Arno 7,5L Air Fryer Sem Óleo "
        "Expert Maxxi AFD7 8 Programas Painel Digital Inox"
    )

    model = engine._model_from_title(title)
    category = engine._category_from_title(title)
    brand = engine._brand_from_title_if_strong(
        title,
        model=model,
        category=category,
    )

    assert model == "AFD7"
    assert brand == "Arno"
    assert category == "Fritadeira elétrica / Air Fryer"


def test_aurafit_title_can_recover_brand_model():
    engine = ProductResearchEngineV054()
    title = "Aurafit G6 Smartwatch GPS Interno 5ATM AMOLED"

    model = engine._model_from_title(title)
    category = engine._category_from_title(title)
    brand = engine._brand_from_title_if_strong(
        title,
        model=model,
        category=category,
    )

    assert model == "G6"
    assert brand == "Aurafit"
    assert category == "Smartwatch"

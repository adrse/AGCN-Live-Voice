import tempfile
from pathlib import Path

from core.product_profile import now_iso
from core.product_store import ProductStore


def test_product_store_v3_flow():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "products.json"
        store = ProductStore(path)

        p1 = store.add(
            name="Produto A",
            brand="Marca A",
            regular_price="199,90",
            current_price="149,90",
            discount="25",
            description="Teste A",
            manual_fields=[
                "name",
                "brand",
                "regular_price",
                "current_price",
                "discount",
                "description",
            ],
        )

        active = store.active()
        assert active["id"] == p1["id"]
        assert active["live_conditions"]["current_price"] == 149.90
        assert active["field_meta"]["brand"]["origin"] == "user"
        assert active["field_meta"]["brand"]["locked_by_user"] is True

        p2 = store.add(
            name="Produto B",
            current_price="89,90",
            manual_fields=["name", "current_price"],
        )

        assert len(store.list()) == 2
        store.activate(p2["id"])
        assert store.active()["name"] == "Produto B"

        store.update(
            p2["id"],
            current_price="79,90",
            additional_info="Informação manual",
            manual_fields=["current_price", "additional_info"],
        )

        active = store.active()
        assert active["live_conditions"]["current_price"] == 79.90
        assert active["additional_info"] == "Informação manual"
        assert active["live_meta"]["current_price"]["locked_by_user"] is True

        context = store.presenter_context()
        assert context["ready"] is True
        assert context["product"]["name"] == "Produto B"
        assert context["product"]["current_price"] == 79.90

        assert store.delete(p2["id"]) is True
        assert len(store.list()) == 1
        assert store.active()["name"] == "Produto A"


def test_research_respects_manual_override():
    with tempfile.TemporaryDirectory() as tmp:
        store = ProductStore(Path(tmp) / "products.json")
        product = store.add(
            name="Relógio",
            brand="Marca informada pelo usuário",
            manual_fields=["name", "brand"],
        )

        store.apply_research(
            product["id"],
            values={
                "brand": "Marca da pesquisa",
                "model": "S20",
                "battery_info": "Até 7 dias",
            },
            field_sources={
                "brand": [{"url": "https://example.com"}],
                "model": [{"url": "https://example.com"}],
                "battery_info": [{"url": "https://example.com"}],
            },
            confidence={
                "brand": 0.9,
                "model": 0.95,
                "battery_info": 0.8,
            },
            research_summary={
                "status": "completed",
                "source_count": 1,
            },
        )

        saved = store.get(product["id"])

        assert saved["brand"] == "Marca informada pelo usuário"
        assert saved["model"] == "S20"
        assert saved["battery_info"] == "Até 7 dias"
        assert saved["field_meta"]["model"]["origin"] == "research"
        assert saved["field_meta"]["model"]["locked_by_user"] is False


def test_live_conditions_are_separate_from_product_facts():
    with tempfile.TemporaryDirectory() as tmp:
        store = ProductStore(Path(tmp) / "products.json")
        product = store.add(
            name="Produto",
            current_price="49,90",
            stock="5",
            live_offer=True,
            live_offer_text="Oferta confirmada nesta LIVE.",
            manual_fields=[
                "name",
                "current_price",
                "stock",
                "live_offer",
                "live_offer_text",
            ],
        )

        raw = store.get(product["id"])
        presenter = store.presenter_context()["product"]

        assert raw["live_conditions"]["stock"] == 5.0
        assert "stock" not in {
            k: v
            for k, v in raw.items()
            if k != "live_conditions"
        }
        assert presenter["stock"] == 5.0
        assert presenter["live_offer"] is True



def test_save_research_draft_preserves_origin():
    with tempfile.TemporaryDirectory() as tmp:
        store = ProductStore(Path(tmp) / "products.json")
        product = store.add(
            name="Relógio S20",
            brand="Marca X",
            battery_info="Até 7 dias",
            manual_fields=[],
            research_meta={
                "name": {
                    "confidence": 0.9,
                    "sources": [{"url": "https://example.com"}],
                },
                "brand": {
                    "confidence": 0.95,
                    "sources": [{"url": "https://example.com"}],
                },
                "battery_info": {
                    "confidence": 0.8,
                    "sources": [{"url": "https://example.com"}],
                },
            },
            research_summary={
                "status": "completed",
                "source_count": 1,
            },
        )

        assert product["field_meta"]["brand"]["origin"] == "research"
        assert product["field_meta"]["brand"]["locked_by_user"] is False
        assert product["research"]["source_count"] == 1

        updated = store.update(
            product["id"],
            brand="Marca corrigida",
            manual_fields=["brand"],
            research_meta={},
        )

        assert updated["brand"] == "Marca corrigida"
        assert updated["field_meta"]["brand"]["origin"] == "user"
        assert updated["field_meta"]["brand"]["locked_by_user"] is True



def test_product_timestamp_does_not_require_iana_tzdata():
    stamp = now_iso()
    assert "T" in stamp
    assert stamp[-6] in {"+", "-"} or stamp.endswith("Z")

    source = (
        Path(__file__).resolve().parents[1]
        / "core"
        / "product_profile.py"
    ).read_text(encoding="utf-8")
    assert "ZoneInfo(" not in source
    assert "America/Araguaina" not in source

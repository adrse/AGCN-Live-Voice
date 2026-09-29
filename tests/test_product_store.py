import tempfile
from pathlib import Path

from core.product_store import ProductStore


def test_product_store_flow():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "products.json"
        store = ProductStore(path)

        p1 = store.add(
            name="Produto A",
            regular_price="199,90",
            current_price="149,90",
            discount="25",
            description="Teste A",
            description_points=[
                "Bateria dura 6 dias",
                "Garantia de 1 ano",
            ],
        )
        assert store.active()["id"] == p1["id"]
        assert store.active()["current_price"] == 149.90
        assert store.active()["description_points"] == [
            "Bateria dura 6 dias",
            "Garantia de 1 ano",
        ]

        p2 = store.add(
            name="Produto B",
            current_price="89,90",
        )
        assert len(store.list()) == 2

        store.activate(p2["id"])
        assert store.active()["name"] == "Produto B"

        store.update(
            p2["id"],
            current_price="79,90",
            additional_info="Frete grátis",
        )
        assert store.active()["current_price"] == 79.90
        assert store.active()["additional_info"] == "Frete grátis"

        context = store.presenter_context()
        assert context["ready"] is True
        assert context["product"]["name"] == "Produto B"
        assert "description_points" in context["product"]

        assert store.delete(p2["id"]) is True
        assert len(store.list()) == 1
        assert store.active()["name"] == "Produto A"

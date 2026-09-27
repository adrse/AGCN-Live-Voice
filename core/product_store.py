from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from threading import RLock
from zoneinfo import ZoneInfo


TEXT_FIELDS = {
    "name", "description", "additional_info", "category", "image_url",
    "brand", "key_benefits", "problems_solved", "differentials",
    "included_items", "compatibility", "limitations", "size_info",
    "battery_info", "usage_info", "shipping_info", "warranty",
    "live_offer_text",
}

NUMBER_FIELDS = {
    "regular_price", "current_price", "discount", "stock",
}


def agora_iso() -> str:
    return datetime.now(
        ZoneInfo("America/Araguaina")
    ).isoformat(timespec="seconds")


def default_store_file() -> Path:
    project_root = Path(__file__).resolve().parents[1]
    data_dir = Path(
        os.getenv(
            "AGCN_DATA_DIR",
            project_root / "data" / "runtime",
        )
    )
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "products.json"


class ProductStore:
    """Product Store portável e compatível com a V0.2."""

    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else default_store_file()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = RLock()
        self.data = {
            "version": 2,
            "active_product_id": None,
            "products": [],
        }
        self.load()

    def load(self) -> None:
        with self.lock:
            if self.path.exists():
                try:
                    content = json.loads(
                        self.path.read_text(encoding="utf-8")
                    )
                    if isinstance(content, dict):
                        self.data["version"] = content.get("version", 1)
                        self.data["active_product_id"] = content.get(
                            "active_product_id"
                        )
                        self.data["products"] = (
                            content.get("products")
                            if isinstance(content.get("products"), list)
                            else []
                        )
                except Exception:
                    self.data = {
                        "version": 2,
                        "active_product_id": None,
                        "products": [],
                    }

            self.data["version"] = 2
            self._repair_active()
            self.save()

    def save(self) -> None:
        with self.lock:
            self.path.write_text(
                json.dumps(
                    self.data,
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

    def _repair_active(self) -> None:
        ids = {p.get("id") for p in self.data["products"]}
        if self.data["active_product_id"] not in ids:
            self.data["active_product_id"] = (
                self.data["products"][0]["id"]
                if self.data["products"]
                else None
            )

    def list(self) -> list[dict]:
        with self.lock:
            active_id = self.data.get("active_product_id")
            items = []
            for product in self.data["products"]:
                item = dict(product)
                item["active"] = product.get("id") == active_id
                items.append(item)
            return items

    def get(self, product_id: str) -> dict | None:
        with self.lock:
            return next(
                (
                    dict(p)
                    for p in self.data["products"]
                    if p.get("id") == product_id
                ),
                None,
            )

    def active(self) -> dict | None:
        with self.lock:
            active_id = self.data.get("active_product_id")
            if not active_id:
                return None
            return self.get(active_id)

    def add(self, **payload) -> dict:
        name = str(payload.get("name") or "").strip()
        if not name:
            raise ValueError("O nome do produto é obrigatório.")

        product = {
            "id": uuid.uuid4().hex[:12],
            "name": name,
            "description": "",
            "regular_price": None,
            "current_price": None,
            "discount": None,
            "additional_info": "",
            "category": "",
            "image_url": "",
            "brand": "",
            "key_benefits": "",
            "problems_solved": "",
            "differentials": "",
            "included_items": "",
            "compatibility": "",
            "limitations": "",
            "size_info": "",
            "battery_info": "",
            "usage_info": "",
            "shipping_info": "",
            "warranty": "",
            "stock": None,
            "live_offer": False,
            "live_offer_text": "",
            "created_at": agora_iso(),
            "updated_at": agora_iso(),
        }

        for key in TEXT_FIELDS:
            if key == "name":
                continue
            if key in payload:
                product[key] = str(payload.get(key) or "").strip()

        for key in NUMBER_FIELDS:
            if key in payload:
                product[key] = self._number_or_none(payload.get(key))

        product["live_offer"] = self._bool_value(
            payload.get("live_offer", False)
        )

        with self.lock:
            self.data["products"].append(product)

            if not self.data.get("active_product_id"):
                self.data["active_product_id"] = product["id"]

            self.save()
            return dict(product)

    def update(self, product_id: str, **changes) -> dict:
        with self.lock:
            product = next(
                (
                    p
                    for p in self.data["products"]
                    if p.get("id") == product_id
                ),
                None,
            )

            if not product:
                raise KeyError("Produto não encontrado.")

            for key, value in changes.items():
                if key in TEXT_FIELDS:
                    product[key] = str(value or "").strip()
                elif key in NUMBER_FIELDS:
                    product[key] = self._number_or_none(value)
                elif key == "live_offer":
                    product[key] = self._bool_value(value)

            if not product.get("name"):
                raise ValueError("O nome do produto é obrigatório.")

            product["updated_at"] = agora_iso()
            self.save()
            return dict(product)

    def delete(self, product_id: str) -> bool:
        with self.lock:
            before = len(self.data["products"])
            self.data["products"] = [
                p
                for p in self.data["products"]
                if p.get("id") != product_id
            ]
            removed = len(self.data["products"]) < before

            if self.data.get("active_product_id") == product_id:
                self.data["active_product_id"] = (
                    self.data["products"][0]["id"]
                    if self.data["products"]
                    else None
                )

            self.save()
            return removed

    def activate(self, product_id: str) -> dict:
        with self.lock:
            if not self.get(product_id):
                raise KeyError("Produto não encontrado.")

            self.data["active_product_id"] = product_id
            self.save()
            return self.active()

    @staticmethod
    def _number_or_none(value):
        if value in (None, ""):
            return None

        if isinstance(value, str):
            raw = value.strip().replace("R$", "").replace(" ", "")
            if "," in raw:
                raw = raw.replace(".", "").replace(",", ".")
            value = raw

        try:
            return float(value)
        except Exception as exc:
            raise ValueError(
                f"Valor numérico inválido: {value}"
            ) from exc

    @staticmethod
    def _bool_value(value) -> bool:
        if isinstance(value, bool):
            return value
        return str(value or "").strip().casefold() in {
            "1", "true", "sim", "yes", "on"
        }

    def presenter_context(self) -> dict:
        product = self.active()

        if not product:
            return {
                "ready": False,
                "message": "Nenhum produto ativo.",
            }

        return {
            "ready": True,
            "product": dict(product),
        }

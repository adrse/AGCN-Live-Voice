from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from threading import RLock
from zoneinfo import ZoneInfo


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
    """Product Store portável baseado na V0.2 aprovada no Colab."""

    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else default_store_file()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = RLock()
        self.data = {
            "version": 1,
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
                        "version": 1,
                        "active_product_id": None,
                        "products": [],
                    }

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
            self.data["active_product_id"] = None

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

    def add(
        self,
        *,
        name,
        description="",
        description_points=None,
        regular_price=None,
        current_price=None,
        discount=None,
        additional_info="",
        category="",
        image_url="",
    ) -> dict:
        name = str(name or "").strip()
        if not name:
            raise ValueError("O nome do produto é obrigatório.")

        product = {
            "id": uuid.uuid4().hex[:12],
            "name": name,
            "description": str(description or "").strip(),
            "description_points": self._clean_points(description_points),
            "regular_price": self._number_or_none(regular_price),
            "current_price": self._number_or_none(current_price),
            "discount": self._number_or_none(discount),
            "additional_info": str(additional_info or "").strip(),
            "category": str(category or "").strip(),
            "image_url": str(image_url or "").strip(),
            "created_at": agora_iso(),
            "updated_at": agora_iso(),
        }

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

            allowed = {
                "name",
                "description",
                "description_points",
                "regular_price",
                "current_price",
                "discount",
                "additional_info",
                "category",
                "image_url",
            }

            for key, value in changes.items():
                if key not in allowed:
                    continue

                if key in {
                    "regular_price",
                    "current_price",
                    "discount",
                }:
                    product[key] = self._number_or_none(value)
                elif key == "description_points":
                    product[key] = self._clean_points(value)
                else:
                    product[key] = str(value or "").strip()

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
    def _clean_points(value) -> list[str]:
        if value in (None, ""):
            return []
        if not isinstance(value, list):
            value = [value]
        result = []
        seen = set()
        for item in value:
            text = str(item or "").strip()
            key = text.casefold()
            if text and key not in seen:
                result.append(text)
                seen.add(key)
        return result

    @staticmethod
    def _number_or_none(value):
        if value in (None, ""):
            return None

        if isinstance(value, str):
            value = (
                value.strip()
                .replace("R$", "")
                .replace(" ", "")
                .replace(".", "")
                .replace(",", ".")
            )

        try:
            return float(value)
        except Exception as exc:
            raise ValueError(
                f"Valor numérico inválido: {value}"
            ) from exc

    def presenter_context(self) -> dict:
        product = self.active()

        if not product:
            return {
                "ready": False,
                "message": "Nenhum produto ativo.",
            }

        return {
            "ready": True,
            "product": {
                "id": product.get("id"),
                "name": product.get("name"),
                "description": product.get("description"),
                "description_points": product.get("description_points") or [],
                "regular_price": product.get("regular_price"),
                "current_price": product.get("current_price"),
                "discount": product.get("discount"),
                "additional_info": product.get("additional_info"),
                "category": product.get("category"),
                "image_url": product.get("image_url"),
            },
        }

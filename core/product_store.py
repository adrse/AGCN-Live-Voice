from __future__ import annotations

import json
import os
import uuid
from copy import deepcopy
from pathlib import Path
from threading import RLock

from core.product_profile import (
    BOOL_FIELDS,
    LIVE_FIELDS,
    NUMBER_FIELDS,
    PERMANENT_FIELDS,
    TEXT_FIELDS,
    default_field_meta,
    empty_product,
    flatten_for_presenter,
    migrate_product,
    now_iso,
)


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
    """Ficha Inteligente do Produto — V0.5.1.

    Mantém compatibilidade com os produtos antigos e prepara a base
    para o Product Intelligence automático da próxima etapa.
    """

    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else default_store_file()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = RLock()
        self.data = {
            "version": 3,
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
                        self.data["active_product_id"] = content.get(
                            "active_product_id"
                        )
                        raw_products = (
                            content.get("products")
                            if isinstance(content.get("products"), list)
                            else []
                        )
                        self.data["products"] = [
                            migrate_product(p)
                            for p in raw_products
                            if isinstance(p, dict)
                        ]
                except Exception:
                    self.data = {
                        "version": 3,
                        "active_product_id": None,
                        "products": [],
                    }

            self.data["version"] = 3
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
                item = deepcopy(product)
                item["active"] = product.get("id") == active_id
                items.append(item)
            return items

    def get(self, product_id: str) -> dict | None:
        with self.lock:
            product = next(
                (
                    p
                    for p in self.data["products"]
                    if p.get("id") == product_id
                ),
                None,
            )
            return deepcopy(product) if product else None

    def active(self) -> dict | None:
        with self.lock:
            active_id = self.data.get("active_product_id")
            if not active_id:
                return None
            return self.get(active_id)

    def active_for_presenter(self) -> dict:
        return flatten_for_presenter(self.active())

    def add(self, **payload) -> dict:
        base = empty_product()
        name = str(payload.get("name") or "").strip()

        if not name:
            raise ValueError("O nome do produto é obrigatório.")

        product = {
            **base,
            "id": uuid.uuid4().hex[:12],
            "created_at": now_iso(),
            "updated_at": now_iso(),
        }

        manual_fields = set(payload.pop("manual_fields", []) or [])

        for field in PERMANENT_FIELDS:
            if field in payload:
                product[field] = self._normalize(field, payload.get(field))
                if (
                    field in manual_fields
                    or product[field] not in (None, "", False)
                ):
                    product["field_meta"][field] = default_field_meta("user")

        live = product["live_conditions"]

        for field in LIVE_FIELDS:
            if field in payload:
                live[field] = self._normalize(field, payload.get(field))
                if (
                    field in manual_fields
                    or live[field] not in (None, "", False)
                ):
                    product["live_meta"][field] = default_field_meta("user")

        product["name"] = name
        product["field_meta"]["name"] = default_field_meta("user")

        with self.lock:
            self.data["products"].append(product)

            if not self.data.get("active_product_id"):
                self.data["active_product_id"] = product["id"]

            self.save()
            return deepcopy(product)

    def update(
        self,
        product_id: str,
        *,
        manual_fields: list[str] | None = None,
        **changes,
    ) -> dict:
        with self.lock:
            product = self._find_mutable(product_id)
            manual = set(manual_fields or [])

            for field, value in changes.items():
                if field in PERMANENT_FIELDS:
                    product[field] = self._normalize(field, value)

                    if field in manual:
                        product["field_meta"][field] = default_field_meta(
                            "user"
                        )

                elif field in LIVE_FIELDS:
                    product["live_conditions"][field] = self._normalize(
                        field,
                        value,
                    )

                    if field in manual:
                        product["live_meta"][field] = default_field_meta(
                            "user"
                        )

            if not str(product.get("name") or "").strip():
                raise ValueError("O nome do produto é obrigatório.")

            product["updated_at"] = now_iso()
            self.save()
            return deepcopy(product)

    def apply_research(
        self,
        product_id: str,
        *,
        values: dict,
        field_sources: dict | None = None,
        confidence: dict | None = None,
        research_summary: dict | None = None,
    ) -> dict:
        """Aplica pesquisa sem sobrescrever campos travados pelo usuário."""
        field_sources = field_sources or {}
        confidence = confidence or {}

        with self.lock:
            product = self._find_mutable(product_id)

            for field, value in (values or {}).items():
                if field not in PERMANENT_FIELDS:
                    continue

                meta = product["field_meta"].get(field) or {}
                if meta.get("locked_by_user"):
                    continue

                normalized = self._normalize(field, value)
                if normalized in (None, ""):
                    continue

                product[field] = normalized
                product["field_meta"][field] = {
                    "origin": "research",
                    "confidence": confidence.get(field),
                    "locked_by_user": False,
                    "sources": deepcopy(field_sources.get(field) or []),
                    "updated_at": now_iso(),
                }

            if research_summary:
                product["research"] = {
                    **product.get("research", {}),
                    **deepcopy(research_summary),
                    "status": research_summary.get("status", "completed"),
                    "last_run_at": now_iso(),
                }

            product["updated_at"] = now_iso()
            self.save()
            return deepcopy(product)

    def unlock_field(self, product_id: str, field: str) -> dict:
        """Permite que uma futura pesquisa volte a atualizar um campo."""
        with self.lock:
            product = self._find_mutable(product_id)

            if field in PERMANENT_FIELDS:
                meta = product["field_meta"].setdefault(
                    field,
                    default_field_meta("unknown"),
                )
                meta["locked_by_user"] = False
                meta["updated_at"] = now_iso()

            elif field in LIVE_FIELDS:
                meta = product["live_meta"].setdefault(
                    field,
                    default_field_meta("unknown"),
                )
                meta["locked_by_user"] = False
                meta["updated_at"] = now_iso()

            else:
                raise KeyError("Campo não encontrado.")

            product["updated_at"] = now_iso()
            self.save()
            return deepcopy(product)

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

    def presenter_context(self) -> dict:
        product = self.active_for_presenter()

        if not product:
            return {
                "ready": False,
                "message": "Nenhum produto ativo.",
            }

        return {
            "ready": True,
            "product": product,
        }

    def _find_mutable(self, product_id: str) -> dict:
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

        return product

    def _normalize(self, field: str, value):
        if field in NUMBER_FIELDS:
            return self._number_or_none(value)

        if field in BOOL_FIELDS:
            return self._bool_value(value)

        if field in TEXT_FIELDS:
            return str(value or "").strip()

        return value

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
            "1",
            "true",
            "sim",
            "yes",
            "on",
        }

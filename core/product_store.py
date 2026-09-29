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
    explicit = os.getenv("AGCN_DATA_DIR")
    if explicit:
        data_dir = Path(explicit)
    else:
        appdata = os.getenv("APPDATA")
        if appdata:
            data_dir = (
                Path(appdata)
                / "AGCN Live Voice"
                / "data"
            )
        else:
            data_dir = (
                Path.home()
                / ".agcn-live-voice"
                / "data"
            )
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "products.json"


class ProductStore:
    """Product Intelligence Store V3.

    Preserva origem/confiança das informações e garante que pesquisa
    automática nunca sobrescreva silenciosamente um campo travado pelo usuário.
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
        research_meta = deepcopy(payload.pop("research_meta", {}) or {})
        research_summary = deepcopy(
            payload.pop("research_summary", {}) or {}
        )

        for field in PERMANENT_FIELDS:
            if field not in payload:
                continue

            value = self._normalize(field, payload.get(field))
            product[field] = value

            if value in (None, "", False):
                continue

            if field in manual_fields:
                product["field_meta"][field] = default_field_meta("user")
            elif field in research_meta:
                product["field_meta"][field] = self._normalize_research_meta(
                    research_meta[field]
                )
            else:
                product["field_meta"][field] = default_field_meta("user")

        live = product["live_conditions"]

        for field in LIVE_FIELDS:
            if field not in payload:
                continue

            value = self._normalize(field, payload.get(field))
            live[field] = value

            if value in (None, "", False):
                continue

            if field in manual_fields:
                product["live_meta"][field] = default_field_meta("user")
            elif field in research_meta:
                product["live_meta"][field] = self._normalize_research_meta(
                    research_meta[field]
                )
            else:
                product["live_meta"][field] = default_field_meta("user")

        product["name"] = name

        if "name" in manual_fields:
            product["field_meta"]["name"] = default_field_meta("user")
        elif "name" in research_meta:
            product["field_meta"]["name"] = self._normalize_research_meta(
                research_meta["name"]
            )
        else:
            product["field_meta"]["name"] = default_field_meta("user")

        if research_summary:
            product["research"] = {
                **product.get("research", {}),
                **research_summary,
                "status": research_summary.get("status", "completed"),
                "last_run_at": research_summary.get(
                    "last_run_at"
                ) or now_iso(),
            }

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
        research_meta: dict | None = None,
        research_summary: dict | None = None,
        **changes,
    ) -> dict:
        with self.lock:
            product = self._find_mutable(product_id)
            manual = set(manual_fields or [])
            research_meta = deepcopy(research_meta or {})

            for field, value in changes.items():
                if field in PERMANENT_FIELDS:
                    normalized = self._normalize(field, value)
                    existing_meta = product["field_meta"].get(field) or {}

                    if (
                        field in research_meta
                        and existing_meta.get("locked_by_user")
                        and field not in manual
                    ):
                        continue

                    product[field] = normalized

                    if field in manual:
                        product["field_meta"][field] = default_field_meta(
                            "user"
                        )
                    elif (
                        field in research_meta
                        and normalized not in (None, "", False)
                    ):
                        product["field_meta"][field] = (
                            self._normalize_research_meta(
                                research_meta[field]
                            )
                        )

                elif field in LIVE_FIELDS:
                    normalized = self._normalize(field, value)
                    existing_meta = product["live_meta"].get(field) or {}

                    if (
                        field in research_meta
                        and existing_meta.get("locked_by_user")
                        and field not in manual
                    ):
                        continue

                    product["live_conditions"][field] = normalized

                    if field in manual:
                        product["live_meta"][field] = default_field_meta(
                            "user"
                        )
                    elif (
                        field in research_meta
                        and normalized not in (None, "", False)
                    ):
                        product["live_meta"][field] = (
                            self._normalize_research_meta(
                                research_meta[field]
                            )
                        )

            if not str(product.get("name") or "").strip():
                raise ValueError("O nome do produto é obrigatório.")

            if research_summary:
                product["research"] = {
                    **product.get("research", {}),
                    **deepcopy(research_summary),
                    "status": research_summary.get(
                        "status",
                        "completed",
                    ),
                    "last_run_at": research_summary.get(
                        "last_run_at"
                    ) or now_iso(),
                }

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
        """Aplica pesquisa salva sem sobrescrever campos travados."""
        field_sources = field_sources or {}
        confidence = confidence or {}

        with self.lock:
            product = self._find_mutable(product_id)

            for field, value in (values or {}).items():
                target_meta = (
                    product["field_meta"]
                    if field in PERMANENT_FIELDS
                    else product["live_meta"]
                    if field in LIVE_FIELDS
                    else None
                )
                if target_meta is None:
                    continue

                meta = target_meta.get(field) or {}
                if meta.get("locked_by_user"):
                    continue

                normalized = self._normalize(field, value)
                if normalized in (None, "", False):
                    continue

                if field in PERMANENT_FIELDS:
                    product[field] = normalized
                else:
                    product["live_conditions"][field] = normalized

                target_meta[field] = self._normalize_research_meta({
                    "origin": "research",
                    "confidence": confidence.get(field),
                    "sources": deepcopy(field_sources.get(field) or []),
                })

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
        with self.lock:
            product = self._find_mutable(product_id)

            if field in PERMANENT_FIELDS:
                meta = product["field_meta"].setdefault(
                    field,
                    default_field_meta("unknown"),
                )
            elif field in LIVE_FIELDS:
                meta = product["live_meta"].setdefault(
                    field,
                    default_field_meta("unknown"),
                )
            else:
                raise KeyError("Campo não encontrado.")

            meta["locked_by_user"] = False
            meta["updated_at"] = now_iso()
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
    def _normalize_research_meta(meta: dict | None) -> dict:
        meta = deepcopy(meta or {})
        return {
            "origin": "research",
            "confidence": meta.get("confidence"),
            "locked_by_user": False,
            "sources": deepcopy(meta.get("sources") or []),
            "updated_at": meta.get("updated_at") or now_iso(),
        }

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

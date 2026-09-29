from __future__ import annotations

from copy import deepcopy
from datetime import datetime


PERMANENT_FIELDS = [
    "product_url",
    "name",
    "brand",
    "model",
    "category",
    "description",
    "key_benefits",
    "problems_solved",
    "differentials",
    "included_items",
    "compatibility",
    "size_info",
    "battery_info",
    "usage_info",
    "warranty",
    "limitations",
    "additional_info",
    "image_url",
]

LIVE_FIELDS = [
    "regular_price",
    "current_price",
    "discount",
    "stock",
    "shipping_info",
    "coupon",
    "live_offer",
    "live_offer_text",
    "promotion_note",
]

TEXT_FIELDS = set(PERMANENT_FIELDS) | {
    "shipping_info",
    "coupon",
    "live_offer_text",
    "promotion_note",
}

NUMBER_FIELDS = {
    "regular_price",
    "current_price",
    "discount",
    "stock",
}

BOOL_FIELDS = {"live_offer"}


def now_iso() -> str:
    """Timestamp local do sistema sem depender do banco IANA de fusos.

    No Windows empacotado, `zoneinfo.ZoneInfo("America/Araguaina")` pode
    falhar quando o banco tzdata não está presente. `astimezone()` usa o
    fuso configurado no próprio Windows e mantém o offset no ISO.
    """
    return datetime.now().astimezone().isoformat(timespec="seconds")


def default_field_meta(origin: str = "unknown") -> dict:
    return {
        "origin": origin,
        "confidence": 1.0 if origin == "user" else None,
        "locked_by_user": origin == "user",
        "sources": [],
        "updated_at": now_iso(),
    }


def empty_research() -> dict:
    return {
        "status": "not_analyzed",
        "last_run_at": None,
        "source_count": 0,
        "review_count": 0,
        "faq": [],
        "review_summary": {
            "positives": [],
            "negatives": [],
            "recurring_questions": [],
        },
        "sources": [],
        "notes": [],
    }


def empty_live_conditions() -> dict:
    return {
        "regular_price": None,
        "current_price": None,
        "discount": None,
        "stock": None,
        "shipping_info": "",
        "coupon": "",
        "live_offer": False,
        "live_offer_text": "",
        "promotion_note": "",
    }


def empty_product() -> dict:
    product = {
        "product_url": "",
        "name": "",
        "brand": "",
        "model": "",
        "category": "",
        "description": "",
        "key_benefits": "",
        "problems_solved": "",
        "differentials": "",
        "included_items": "",
        "compatibility": "",
        "size_info": "",
        "battery_info": "",
        "usage_info": "",
        "warranty": "",
        "limitations": "",
        "additional_info": "",
        "image_url": "",
        "live_conditions": empty_live_conditions(),
        "field_meta": {},
        "live_meta": {},
        "research": empty_research(),
    }
    return product


def migrate_product(product: dict) -> dict:
    """Migra produtos antigos sem perder dados."""
    p = deepcopy(product or {})
    base = empty_product()

    for field in PERMANENT_FIELDS:
        if field not in p:
            p[field] = base[field]

    live = p.get("live_conditions")
    if not isinstance(live, dict):
        live = empty_live_conditions()
    else:
        live = {**empty_live_conditions(), **live}

    # Migração da estrutura antiga, onde condições da LIVE ficavam no topo.
    for field in LIVE_FIELDS:
        if field in p and p.get(field) not in (None, "", False):
            live[field] = p.get(field)

    p["live_conditions"] = live

    if not isinstance(p.get("field_meta"), dict):
        p["field_meta"] = {}
    if not isinstance(p.get("live_meta"), dict):
        p["live_meta"] = {}
    if not isinstance(p.get("research"), dict):
        p["research"] = empty_research()
    else:
        p["research"] = {**empty_research(), **p["research"]}

    return p


def flatten_for_presenter(product: dict | None) -> dict:
    if not product:
        return {}

    p = migrate_product(product)
    flat = {field: p.get(field) for field in PERMANENT_FIELDS}

    for field, value in p["live_conditions"].items():
        flat[field] = value

    flat.update({
        "id": p.get("id"),
        "created_at": p.get("created_at"),
        "updated_at": p.get("updated_at"),
        "research": deepcopy(p.get("research") or {}),
        "field_meta": deepcopy(p.get("field_meta") or {}),
        "live_meta": deepcopy(p.get("live_meta") or {}),
    })
    return flat

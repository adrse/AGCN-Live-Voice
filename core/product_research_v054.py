from __future__ import annotations

import re
from copy import deepcopy
from urllib.parse import urlparse

from core.product_enrichment import MarketplaceEnrichmentEngine
from core.product_research import (
    ProductResearchEngine,
    _clean,
    _first,
)


GENERIC_DESCRIPTIONS = (
    "descubra ótimos preços",
    "descubra otimos precos",
    "compre agora para obter ofertas",
    "receba frete grátis para itens qualificados",
    "receba frete gratis para itens qualificados",
    "shop now",
    "great prices",
)

GENERIC_BRANDS = {
    "fritadeira",
    "frigideira",
    "frigideiras",
    "panela",
    "panelas",
    "smartwatch",
    "relógio",
    "relogio",
    "conjunto",
    "kit",
    "pote",
    "potes",
    "marmita",
    "fitness",
    "calça",
    "calca",
    "legging",
    "fone",
    "bluetooth",
    "air",
    "fryer",
    "espátula",
    "espatula",
    "antiaderente",
}


class ProductResearchEngineV054(ProductResearchEngine):
    """V0.5.4 — TikTok para identidade; marketplaces para enriquecimento.

    O link do TikTok define a identidade principal. Marketplaces públicos
    servem apenas para completar fatos permanentes e especificações técnicas.
    Preços externos nunca alimentam a condição da LIVE.
    """

    def __init__(self):
        super().__init__()
        self.enrichment = MarketplaceEnrichmentEngine()

    def analyze(self, url: str, hint: str = "") -> dict:
        url = _clean(url)
        if not url.startswith(("http://", "https://")):
            raise ValueError("Informe um link válido do produto.")

        native = {}
        if "tiktok.com" in urlparse(url).netloc.casefold():
            try:
                native = self.tiktok_native.extract(url)
            except Exception as exc:
                native = {
                    "ok": False,
                    "notes": [
                        "TikTok nativo indisponível: "
                        + _clean(str(exc))[:160]
                    ],
                }

        direct = self._fetch_source(
            url,
            source_type="submitted_link",
        )
        resolved_url = direct.get("final_url") or url

        metadata = {}
        candidate_urls = [
            url,
            *(direct.get("redirect_urls") or []),
            resolved_url,
        ]

        for candidate_url in candidate_urls:
            found = self._metadata_from_url(candidate_url)
            if found:
                metadata = {**metadata, **found}

        # Identidade: TikTok/URL sempre vence pesquisa externa.
        title = _clean(
            _first(
                native.get("title"),
                metadata.get("name"),
                (direct.get("product") or {}).get("name"),
                direct.get("title"),
            )
        )
        if hint:
            title = _clean(hint)

        image_url = _clean(
            _first(
                native.get("image_url"),
                metadata.get("image_url"),
                (direct.get("product") or {}).get("image_url"),
                direct.get("image_url"),
            )
        )

        native_brand = _clean(native.get("brand"))
        native_model = _clean(native.get("model"))
        native_category = _clean(native.get("category"))

        identity_guess = self._identity_from_title(title)
        brand = native_brand or _clean(identity_guess.get("brand"))
        model = native_model or _clean(identity_guess.get("model"))
        category = (
            native_category
            or _clean(identity_guess.get("category"))
            or self._category_from_title(title)
        )

        if brand.casefold() in GENERIC_BRANDS:
            brand = ""

        # Produtos genéricos sem modelo não recebem marca inventada do título.
        if (
            not model
            and category in {
                "Panelas e frigideiras",
                "Potes e Marmitas",
                "Moda Fitness",
                "Calça",
            }
        ):
            brand = native_brand

        description = _clean(native.get("description"))
        if self._is_generic_description(description):
            description = ""

        values = {
            "product_url": resolved_url,
            "name": title,
            "image_url": image_url,
        }
        confidence = {
            "product_url": 0.99,
            "name": 0.98 if title else 0.0,
            "image_url": 0.98 if image_url else 0.0,
        }

        tiktok_source = {
            "url": resolved_url,
            "host": "shop.tiktok.com",
            "marketplace": "TikTok Shop",
            "title": title,
            "source_type": "tiktok_identity",
            "status_code": direct.get("status_code"),
        }

        field_sources = {
            "product_url": [tiktok_source],
            "name": [tiktok_source] if title else [],
            "image_url": [tiktok_source] if image_url else [],
        }

        if brand:
            values["brand"] = brand
            confidence["brand"] = 0.98 if native_brand else 0.84
            field_sources["brand"] = [tiktok_source]

        if model:
            values["model"] = model
            confidence["model"] = 0.98 if native_model else 0.88
            field_sources["model"] = [tiktok_source]

        if category:
            values["category"] = category
            confidence["category"] = 0.96 if native_category else 0.86
            field_sources["category"] = [tiktok_source]

        if description:
            values["description"] = description
            confidence["description"] = 0.98
            field_sources["description"] = [tiktok_source]

        # Condição da LIVE: somente TikTok nativo, nunca marketplace externo.
        for field in (
            "current_price",
            "regular_price",
            "discount",
            "stock",
        ):
            value = native.get(field)
            if value not in (None, ""):
                values[field] = value
                confidence[field] = 0.99
                field_sources[field] = [tiktok_source]

        if native.get("benefits"):
            values["key_benefits"] = _clean(native["benefits"])
            confidence["key_benefits"] = 0.97
            field_sources["key_benefits"] = [tiktok_source]

        if native.get("care_instructions"):
            values["usage_info"] = _clean(
                native["care_instructions"]
            )
            confidence["usage_info"] = 0.96
            field_sources["usage_info"] = [tiktok_source]

        native_specs = self._normalize_native_specs(
            native.get("attributes") or []
        )

        # A partir daqui, usamos marketplaces apenas para ENRIQUECER.
        enrichment = self.enrichment.enrich({
            "name": title,
            "brand": brand,
            "model": model,
            "category": category,
            "image_url": image_url,
        })

        for field, value in (
            enrichment.get("values") or {}
        ).items():
            if value in (None, "", [], {}):
                continue

            external_conf = (
                enrichment.get("confidence") or {}
            ).get(field, 0.0)

            should_fill = field not in values or values.get(field) in (
                None,
                "",
                [],
                {},
            )

            if field == "description":
                should_fill = (
                    not values.get("description")
                    or self._is_generic_description(
                        values.get("description", "")
                    )
                )

            if field in ("brand", "model"):
                # External só completa campos ausentes; não substitui a
                # identidade já obtida do TikTok.
                should_fill = not values.get(field)

            if field in (
                "current_price",
                "regular_price",
                "discount",
                "stock",
            ):
                continue

            if should_fill:
                values[field] = value
                confidence[field] = external_conf
                field_sources[field] = deepcopy(
                    (enrichment.get("field_sources") or {}).get(
                        field,
                        [],
                    )
                )

        external_specs = enrichment.get(
            "technical_specs"
        ) or []
        technical_specs = self._merge_specs(
            native_specs,
            external_specs,
        )

        # Distribui especificações dinâmicas nos campos gerais existentes.
        mapped = self._map_specs_to_fields(technical_specs)
        for field, payload in mapped.items():
            if not values.get(field):
                values[field] = payload["value"]
                confidence[field] = payload["confidence"]
                field_sources[field] = payload["sources"]

        if technical_specs:
            values["additional_info"] = (
                "Especificações técnicas: "
                + "; ".join(
                    f"{item['name']}: {item['value']}"
                    for item in technical_specs[:20]
                )
            )[:2800]
            confidence["additional_info"] = max(
                item.get("confidence", 0.7)
                for item in technical_specs
            )
            field_sources["additional_info"] = self._merge_source_cards(
                [
                    item.get("sources") or []
                    for item in technical_specs
                ]
            )

        reviews = enrichment.get("review_texts") or []
        review_summary = self._analyze_reviews(
            reviews,
            [],
        )
        faq = self._extract_faq([], reviews)

        marketplace_sources = enrichment.get("sources") or []
        sources = [tiktok_source] + marketplace_sources

        notes = []
        notes.extend(native.get("notes") or [])
        notes.extend(enrichment.get("notes") or [])

        if native.get("raw_sources"):
            notes.append(
                "TikTok usado para identidade: "
                + ", ".join(native.get("raw_sources") or [])
            )

        notes.append(
            "Enriquecimento externo restrito a marketplaces públicos compatíveis."
        )
        notes.append(
            "Preço, desconto e estoque de outros marketplaces não entram na condição da LIVE."
        )

        return {
            "ok": bool(title),
            "submitted_url": url,
            "resolved_url": resolved_url,
            "values": values,
            "confidence": confidence,
            "field_sources": field_sources,
            "research_summary": {
                "status": "completed",
                "source_count": len(sources),
                "review_count": len(reviews),
                "faq": faq,
                "review_summary": review_summary,
                "sources": sources,
                "notes": notes,
                "search_query": enrichment.get("query") or "",
                "technical_specs": technical_specs,
                "identifiers": {
                    "tiktok_product_id": _first(
                        native.get("product_id"),
                        metadata.get("product_id"),
                    ),
                    "group_id": _first(
                        native.get("group_id"),
                        metadata.get("group_id"),
                    ),
                },
                "tiktok_native": {
                    "used": bool(native.get("ok")),
                    "browser_used": "tiktok_browser"
                    in (native.get("raw_sources") or []),
                    "attribute_count": len(
                        native.get("attributes") or []
                    ),
                    "sku_count": len(
                        native.get("skus") or []
                    ),
                    "rating": native.get("rating"),
                    "review_count": native.get("review_count"),
                    "sold_count": native.get("sold_count"),
                    "seller": native.get("seller") or {},
                },
                "enrichment": {
                    "used": True,
                    "marketplace_source_count": len(
                        marketplace_sources
                    ),
                    "technical_spec_count": len(
                        technical_specs
                    ),
                    "query": enrichment.get("query") or "",
                    "discovery": enrichment.get("discovery") or {},
                    "confirmed_match_count": enrichment.get(
                        "confirmed_match_count",
                        0,
                    ),
                    "needs_confirmation": bool(
                        enrichment.get("needs_confirmation")
                    ),
                    "candidate_matches": enrichment.get(
                        "candidate_matches"
                    ) or [],
                },
            },
        }

    def _category_from_title(self, title: str) -> str:
        low = _clean(title).casefold()

        if any(
            token in low
            for token in (
                "fritadeira",
                "air fryer",
                "airfryer",
            )
        ):
            return "Fritadeira elétrica / Air Fryer"

        if any(
            token in low
            for token in (
                "frigideira",
                "frigideiras",
                "panela",
                "panelas",
            )
        ):
            return "Panelas e frigideiras"

        if (
            "pote" in low
            and "vidro" in low
        ):
            return "Potes e Marmitas"

        if any(
            token in low
            for token in (
                "smartwatch",
                "relógio inteligente",
                "relogio inteligente",
            )
        ):
            return "Smartwatch"

        if (
            "fitness" in low
            and any(
                token in low
                for token in (
                    "calça",
                    "calca",
                    "legging",
                    "top",
                )
            )
        ):
            return "Moda Fitness"

        return ""

    def _is_generic_description(self, value: str) -> bool:
        low = _clean(value).casefold()
        if not low:
            return True
        return any(
            marker in low
            for marker in GENERIC_DESCRIPTIONS
        )

    def _normalize_native_specs(
        self,
        attributes: list[dict],
    ) -> list[dict]:
        out = []
        seen = set()

        for item in attributes:
            name = _clean(item.get("name"))
            value = _clean(item.get("value"))
            if not name or not value:
                continue

            key = (
                name.casefold(),
                value.casefold(),
            )
            if key in seen:
                continue
            seen.add(key)

            out.append({
                "name": name,
                "value": value,
                "confidence": 0.98,
                "source_count": 1,
                "sources": [{
                    "marketplace": "TikTok Shop",
                    "host": "shop.tiktok.com",
                    "title": "Página do produto",
                }],
            })

        return out

    def _merge_specs(
        self,
        native_specs: list[dict],
        external_specs: list[dict],
    ) -> list[dict]:
        merged = []
        by_name = {}

        for item in [
            *native_specs,
            *external_specs,
        ]:
            name = _clean(item.get("name"))
            value = _clean(item.get("value"))
            if not name or not value:
                continue

            key = name.casefold()

            if key not in by_name:
                copy = deepcopy(item)
                copy["name"] = name
                copy["value"] = value
                by_name[key] = copy
                merged.append(copy)
                continue

            current = by_name[key]

            if (
                item.get("confidence", 0)
                > current.get("confidence", 0)
            ):
                current["value"] = value
                current["confidence"] = item.get(
                    "confidence",
                    current.get("confidence"),
                )

            current["sources"] = self._merge_source_cards([
                current.get("sources") or [],
                item.get("sources") or [],
            ])
            current["source_count"] = len({
                source.get("marketplace")
                or source.get("host")
                for source in current["sources"]
                if source.get("marketplace")
                or source.get("host")
            })

        return merged[:50]

    def _map_specs_to_fields(
        self,
        specs: list[dict],
    ) -> dict:
        groups = {
            "size_info": (
                "capacidade",
                "dimens",
                "peso",
                "volume",
                "tamanho",
            ),
            "compatibility": (
                "voltagem",
                "tensão",
                "tensao",
                "compatib",
                "bluetooth",
                "sistema operacional",
            ),
            "battery_info": (
                "bateria",
                "autonomia",
                "carregamento",
            ),
            "warranty": (
                "garantia",
            ),
        }

        result = {}

        for field, keywords in groups.items():
            selected = [
                item
                for item in specs
                if any(
                    keyword in item["name"].casefold()
                    for keyword in keywords
                )
            ]

            if not selected:
                continue

            result[field] = {
                "value": "; ".join(
                    f"{item['name']}: {item['value']}"
                    for item in selected[:6]
                ),
                "confidence": max(
                    item.get("confidence", 0.7)
                    for item in selected
                ),
                "sources": self._merge_source_cards(
                    [
                        item.get("sources") or []
                        for item in selected
                    ]
                ),
            }

        return result

    def _merge_source_cards(
        self,
        groups: list[list[dict]],
    ) -> list[dict]:
        out = []
        seen = set()

        for group in groups:
            for source in group:
                key = (
                    source.get("url")
                    or (
                        str(source.get("marketplace"))
                        + "|"
                        + str(source.get("title"))
                    )
                )
                if not key or key in seen:
                    continue
                seen.add(key)
                out.append(deepcopy(source))

        return out[:8]

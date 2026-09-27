from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from urllib.parse import parse_qs, quote_plus, unquote, urlparse

import httpx
from bs4 import BeautifulSoup

from core.visual_product_discovery import (
    GoogleLensDiscovery,
    VisualImageMatcher,
    lens_enabled_for_current_machine,
)


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0 Safari/537.36"
)

MARKETPLACES = {
    "mercadolivre.com.br": "Mercado Livre",
    "amazon.com.br": "Amazon",
    "magazineluiza.com.br": "Magazine Luiza",
    "casasbahia.com.br": "Casas Bahia",
    "carrefour.com.br": "Carrefour",
    "ponto.com.br": "Ponto",
    "extra.com.br": "Extra",
    "kabum.com.br": "KaBuM!",
    "americanas.com.br": "Americanas",
    "shopee.com.br": "Shopee",
}

SEARCH_DOMAINS = [
    "mercadolivre.com.br",
    "magazineluiza.com.br",
    "amazon.com.br",
    "casasbahia.com.br",
    "carrefour.com.br",
    "ponto.com.br",
    "extra.com.br",
    "kabum.com.br",
    "americanas.com.br",
    "shopee.com.br",
]

STOPWORDS = {
    "para", "com", "sem", "uma", "um", "de", "da", "do", "das", "dos",
    "e", "em", "no", "na", "nos", "nas", "por", "the", "a", "o", "of",
    "kit", "produto", "shop", "tiktok", "brasil", "oficial", "loja",
    "comprar", "compre", "oferta", "promoção", "promocao", "original",
    "novo", "nova", "frete", "grátis", "gratis",
}

GENERIC_BRAND_WORDS = {
    "fritadeira", "eletrica", "elétrica", "air", "fryer", "smartwatch",
    "relogio", "relógio", "kit", "conjunto", "pote", "potes", "vidro",
    "calca", "calça", "legging", "fitness", "marmita", "fone", "bluetooth",
    "panela", "jogo", "liquidificador", "cafeteira", "ventilador",
}

PT_HINTS = {
    "produto", "marca", "modelo", "capacidade", "potência", "potencia",
    "voltagem", "tensão", "tensao", "garantia", "dimensões", "dimensoes",
    "peso", "material", "temperatura", "benefícios", "beneficios",
    "descrição", "descricao", "acompanha", "inclui", "cor", "frequência",
    "frequencia", "uso", "fácil", "facil", "prático", "pratico",
}


def clean(value) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def host(url: str) -> str:
    try:
        return urlparse(url).netloc.casefold().removeprefix("www.")
    except Exception:
        return ""


def marketplace_root(value: str) -> str | None:
    h = (value or "").casefold().removeprefix("www.")
    for root in MARKETPLACES:
        if h == root or h.endswith("." + root):
            return root
    return None


def marketplace_name(value: str) -> str:
    root = marketplace_root(value)
    return MARKETPLACES.get(root or "", value or "Marketplace")


def tokens(text: str) -> set[str]:
    raw = re.findall(r"[\wÀ-ÿ-]{3,}", clean(text).casefold())
    return {x for x in raw if x not in STOPWORDS and not x.isdigit()}


def specific_tokens(text: str) -> set[str]:
    low = clean(text).casefold()
    out = set()

    for value, unit in re.findall(
        r"\b(\d+(?:[.,]\d+)?)\s*(ml|l|cm|mm|kg|g|mah|atm|hz|w|v)\b",
        low,
        flags=re.I,
    ):
        out.add(value.replace(",", ".") + unit.casefold())

    for token in re.findall(
        r"\b[a-z]{1,8}\d+[a-z0-9-]*\b",
        low,
        flags=re.I,
    ):
        out.add(token.casefold())

    return out


def normalize_label(label: str) -> str:
    low = clean(label).casefold().strip(": -")
    aliases = {
        "tensao": "Voltagem",
        "tensão": "Voltagem",
        "voltagem": "Voltagem",
        "potencia": "Potência",
        "potência": "Potência",
        "capacidade util": "Capacidade",
        "capacidade útil": "Capacidade",
        "capacidade": "Capacidade",
        "peso do produto": "Peso",
        "peso": "Peso",
        "material": "Material",
        "cor": "Cor",
        "modelo": "Modelo",
        "marca": "Marca",
        "garantia": "Garantia",
        "garantia (fabrica)": "Garantia",
        "garantia (fábrica)": "Garantia",
        "frequencia": "Frequência",
        "frequência": "Frequência",
        "temperatura": "Temperatura",
        "tipo de pino": "Tipo de pino",
        "padrao da tomada": "Padrão da tomada",
        "padrão da tomada": "Padrão da tomada",
    }

    if low in aliases:
        return aliases[low]

    if "dimens" in low and "embalagem" in low:
        return "Dimensões com embalagem"
    if "dimens" in low:
        return "Dimensões"
    if "peso" in low and "embalagem" in low:
        return "Peso com embalagem"
    if "bateria" in low:
        return "Bateria"
    if "autonomia" in low:
        return "Autonomia"
    if "bluetooth" in low:
        return "Bluetooth"
    if "resist" in low and ("agua" in low or "água" in low):
        return "Resistência à água"

    return clean(label)[:80]


def portuguese_score(text: str) -> float:
    low = clean(text).casefold()
    if not low:
        return 0.0
    hits = sum(1 for word in PT_HINTS if word in low)
    return min(1.0, hits / 5.0)


class MarketplaceEnrichmentEngine:
    """Enriquece a identidade do TikTok usando marketplaces públicos brasileiros.

    Não usa preço externo como preço da LIVE. O objetivo é completar fatos
    permanentes do produto e especificações técnicas.
    """

    def __init__(self):
        self.client = httpx.Client(
            follow_redirects=True,
            timeout=httpx.Timeout(12.0, connect=8.0),
            headers={
                "User-Agent": USER_AGENT,
                "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.5",
                "Accept": "text/html,application/xhtml+xml,application/json;q=0.8,*/*;q=0.5",
            },
        )
        self.lens = GoogleLensDiscovery(headless=True)
        self.image_matcher = VisualImageMatcher()

    def enrich(self, identity: dict) -> dict:
        name = clean(identity.get("name"))
        brand = clean(identity.get("brand"))
        model = clean(identity.get("model"))
        category = clean(identity.get("category"))
        image_url = clean(identity.get("image_url"))

        if not name:
            return {
                "values": {},
                "confidence": {},
                "field_sources": {},
                "technical_specs": [],
                "sources": [],
                "notes": ["Sem nome do produto para pesquisa externa."],
                "discovery": {
                    "lens_enabled": False,
                    "lens_used": False,
                    "lens_result_count": 0,
                },
            }

        query = self._build_query(name, brand, model, category)

        discovery = {
            "lens_enabled": lens_enabled_for_current_machine(),
            "lens_used": False,
            "lens_result_count": 0,
            "lens_marketplace_count": 0,
            "lens_reason": "",
        }

        lens_results = []
        if discovery["lens_enabled"] and image_url:
            lens_result = self.lens.search(
                image_url=image_url,
                title_hint=query,
                max_results=36,
            )
            discovery["lens_used"] = bool(lens_result.get("ok"))
            discovery["lens_result_count"] = len(
                lens_result.get("results") or []
            )
            discovery["lens_marketplace_count"] = int(
                lens_result.get("marketplace_count") or 0
            )
            discovery["lens_reason"] = clean(
                lens_result.get("reason")
            )

            for item in lens_result.get("results") or []:
                root = marketplace_root(item.get("host", ""))
                if not root:
                    continue
                lens_results.append({
                    "url": item["url"],
                    "host": item["host"],
                    "marketplace": MARKETPLACES[root],
                    "title": clean(item.get("title")),
                    "snippet": "",
                    "source": "google_lens",
                    "lens_rank": item.get("rank"),
                })

        text_results = self._search_marketplaces(
            query=query,
            brand=brand,
            model=model,
        )

        search_results = self._merge_discovery_results(
            lens_results,
            text_results,
        )

        accepted = self._accept_candidates(
            identity={
                "name": name,
                "brand": brand,
                "model": model,
                "category": category,
            },
            candidates=search_results,
            limit=12,
        )

        verified_sources = []
        candidate_matches = []

        strong_identity = bool(brand and model)

        for candidate in accepted:
            fetched = self._fetch_marketplace_page(candidate)
            if not fetched.get("ok"):
                continue

            text_score = float(candidate["match_score"])
            match_score = text_score
            image_match = {
                "ok": False,
                "score": None,
                "same_catalog_photo": False,
            }

            if image_url and fetched.get("image_url"):
                image_match = self.image_matcher.compare_urls(
                    image_url,
                    fetched["image_url"],
                )

                if image_match.get("ok"):
                    visual_score = float(
                        image_match.get("score") or 0
                    )
                    match_score = min(
                        1.0,
                        (text_score * 0.68)
                        + (visual_score * 0.32),
                    )

                    if image_match.get("same_catalog_photo"):
                        match_score = max(match_score, 0.96)

            from_lens = (
                candidate.get("source") == "google_lens"
            )
            same_photo = bool(
                image_match.get("same_catalog_photo")
            )

            if strong_identity:
                verification = "confirmed"
                reason = "marca e modelo conferidos"
            elif same_photo:
                verification = "confirmed"
                reason = "mesma foto ou foto de catálogo quase idêntica"
            elif from_lens:
                verification = "needs_confirmation"
                reason = "correspondência visual do Google Lens"
            else:
                verification = "needs_confirmation"
                reason = "correspondência textual sem identidade única"

            fetched["match_score"] = round(
                match_score,
                3,
            )
            fetched["text_match_score"] = round(
                text_score,
                3,
            )
            fetched["discovery_source"] = candidate.get(
                "source",
                "text_search",
            )
            fetched["lens_rank"] = candidate.get("lens_rank")
            fetched["image_match"] = image_match
            fetched["verification"] = verification
            fetched["verification_reason"] = reason

            card = self._source_card(fetched)
            card["verification"] = verification
            card["verification_reason"] = reason
            card["image_url"] = fetched.get("image_url")
            candidate_matches.append(card)

            if verification == "confirmed":
                verified_sources.append(fetched)

        fused = self._fuse(
            identity={
                "name": name,
                "brand": brand,
                "model": model,
                "category": category,
            },
            sources=verified_sources,
            query=query,
        )
        fused["discovery"] = discovery
        fused["candidate_matches"] = candidate_matches[:12]
        fused["confirmed_match_count"] = len(
            verified_sources
        )
        fused["needs_confirmation"] = any(
            item.get("verification") == "needs_confirmation"
            for item in candidate_matches
        )

        if (
            not verified_sources
            and fused["needs_confirmation"]
        ):
            fused.setdefault("notes", []).insert(
                0,
                "Foram encontrados produtos visualmente parecidos, mas a identidade não é forte o suficiente para copiar dados automaticamente. Confirme um candidato."
            )

        return fused

    def enrich_confirmed_candidate(
        self,
        identity: dict,
        candidate: dict,
    ) -> dict:
        """Completa a ficha depois que o usuário confirma um candidato visual."""
        url = clean(candidate.get("url"))
        h = host(url)
        root = marketplace_root(h)

        if not url or not root:
            raise ValueError(
                "O candidato confirmado precisa ser de um marketplace suportado."
            )

        fetched = self._fetch_marketplace_page({
            "url": url,
            "host": h,
            "marketplace": MARKETPLACES[root],
            "title": clean(candidate.get("title")),
            "snippet": "",
        })

        if not fetched.get("ok"):
            raise ValueError(
                "Não foi possível ler a página do produto confirmado."
            )

        image_url = clean(identity.get("image_url"))
        image_match = {
            "ok": False,
            "score": None,
            "same_catalog_photo": False,
        }

        if image_url and fetched.get("image_url"):
            image_match = self.image_matcher.compare_urls(
                image_url,
                fetched["image_url"],
            )

        fetched["match_score"] = 1.0
        fetched["text_match_score"] = 1.0
        fetched["discovery_source"] = "user_confirmation"
        fetched["image_match"] = image_match
        fetched["verification"] = "confirmed"
        fetched["verification_reason"] = "confirmado pelo usuário"

        query = self._build_query(
            clean(identity.get("name")),
            clean(identity.get("brand")),
            clean(identity.get("model")),
            clean(identity.get("category")),
        )

        fused = self._fuse(
            identity={
                "name": clean(identity.get("name")),
                "brand": clean(identity.get("brand")),
                "model": clean(identity.get("model")),
                "category": clean(identity.get("category")),
            },
            sources=[fetched],
            query=query,
        )
        fused["confirmed_match_count"] = 1
        fused["needs_confirmation"] = False
        fused["candidate_matches"] = [
            self._source_card(fetched)
        ]
        fused["discovery"] = {
            "lens_enabled": lens_enabled_for_current_machine(),
            "lens_used": bool(
                candidate.get("discovery_source") == "google_lens"
                or candidate.get("source") == "google_lens"
            ),
            "confirmed_by_user": True,
        }
        return fused

    def _build_query(
        self,
        name: str,
        brand: str,
        model: str,
        category: str,
    ) -> str:
        if brand and model:
            return clean(f"{brand} {model} {category}")

        words = clean(name).split()
        # Mantém capacidades/modelos e corta textos promocionais muito longos.
        return " ".join(words[:16])

    def _search_marketplaces(
        self,
        *,
        query: str,
        brand: str,
        model: str,
    ) -> list[dict]:
        seen = set()
        results = []

        searches = []
        for domain in SEARCH_DOMAINS:
            if brand and model:
                searches.append(
                    (domain, f'site:{domain} "{brand}" "{model}"')
                )
            searches.append(
                (domain, f'site:{domain} "{query}"')
            )

        for domain, search_query in searches:
            try:
                response = self.client.get(
                    "https://html.duckduckgo.com/html/?q="
                    + quote_plus(search_query)
                )
                if response.status_code >= 400:
                    continue

                soup = BeautifulSoup(response.text, "html.parser")

                for row in soup.select(".result"):
                    link = row.select_one(".result__a")
                    snippet = row.select_one(".result__snippet")
                    if not link:
                        continue

                    href = link.get("href") or ""
                    if href.startswith("//"):
                        href = "https:" + href

                    if "duckduckgo.com/l/" in href:
                        try:
                            parsed = urlparse(href)
                            target = parse_qs(parsed.query).get(
                                "uddg",
                                [None],
                            )[0]
                            if target:
                                href = unquote(target)
                        except Exception:
                            pass

                    h = host(href)
                    root = marketplace_root(h)
                    if not root or root != domain:
                        continue

                    key = href.split("#")[0]
                    if key in seen:
                        continue
                    seen.add(key)

                    results.append({
                        "url": key,
                        "host": h,
                        "marketplace": MARKETPLACES[root],
                        "title": clean(link.get_text(" ", strip=True)),
                        "snippet": clean(
                            snippet.get_text(" ", strip=True)
                            if snippet
                            else ""
                        ),
                    })

                    if len(results) >= 36:
                        return results
            except Exception:
                continue

        return results

    def _merge_discovery_results(
        self,
        lens_results: list[dict],
        text_results: list[dict],
    ) -> list[dict]:
        merged = []
        seen = set()

        for item in [*lens_results, *text_results]:
            url = (item.get("url") or "").split("#")[0]
            if not url or url in seen:
                continue
            seen.add(url)

            copy = dict(item)
            copy["url"] = url
            copy.setdefault("source", "text_search")
            merged.append(copy)

        return merged

    def _accept_candidates(
        self,
        *,
        identity: dict,
        candidates: list[dict],
        limit: int,
    ) -> list[dict]:
        base_tokens = tokens(identity["name"])
        base_specific = specific_tokens(identity["name"])
        brand = identity.get("brand", "")
        model = identity.get("model", "")

        scored = []

        for item in candidates:
            text = clean(
                (item.get("title") or "")
                + " "
                + (item.get("snippet") or "")
            )
            low = text.casefold()
            item_tokens = tokens(text)
            item_specific = specific_tokens(text)
            common = base_tokens & item_tokens
            overlap = len(common) / max(
                1,
                min(len(base_tokens), len(item_tokens)),
            )

            brand_match = bool(
                brand and brand.casefold() in low
            )
            model_match = bool(
                model and model.casefold() in low
            )

            from_lens = item.get("source") == "google_lens"

            if brand and model:
                if not (brand_match and model_match):
                    continue
            else:
                minimum_common = 2 if from_lens else 3
                minimum_overlap = 0.24 if from_lens else 0.40

                if len(common) < minimum_common and not (
                    base_specific & item_specific
                ):
                    continue

                if overlap < minimum_overlap and not (
                    base_specific & item_specific
                ):
                    continue

                if (
                    not from_lens
                    and base_specific
                    and item_specific
                    and not (base_specific & item_specific)
                ):
                    continue

            score = overlap

            if from_lens:
                rank = item.get("lens_rank")
                try:
                    rank = int(rank)
                except Exception:
                    rank = 20
                score += max(0.08, 0.24 - (rank - 1) * 0.012)
            if brand_match:
                score += 0.28
            if model_match:
                score += 0.34
            score += min(
                0.24,
                len(base_specific & item_specific) * 0.08,
            )

            item = dict(item)
            item["match_score"] = round(min(1.0, score), 3)
            scored.append(item)

        scored.sort(
            key=lambda item: item["match_score"],
            reverse=True,
        )

        selected = []
        per_marketplace = Counter()
        for item in scored:
            root = marketplace_root(item.get("host", ""))
            if per_marketplace[root] >= 2:
                continue
            selected.append(item)
            per_marketplace[root] += 1
            if len(selected) >= limit:
                break

        return selected

    def _fetch_marketplace_page(self, candidate: dict) -> dict:
        record = {
            "ok": False,
            "url": candidate["url"],
            "host": candidate["host"],
            "marketplace": candidate["marketplace"],
            "title": candidate.get("title", ""),
            "snippet": candidate.get("snippet", ""),
            "description": "",
            "brand": "",
            "model": "",
            "category": "",
            "image_url": "",
            "attributes": [],
            "benefit_texts": [],
            "included_texts": [],
            "reviews": [],
        }

        try:
            response = self.client.get(candidate["url"])
            if response.status_code >= 400:
                return record

            if "html" not in response.headers.get(
                "content-type",
                "",
            ).casefold():
                return record

            parsed = self._parse_html(
                response.text,
                str(response.url),
            )
            record.update(parsed)
            record["url"] = str(response.url)
            record["host"] = host(str(response.url))
            record["marketplace"] = marketplace_name(
                record["host"]
            )
            record["ok"] = True
        except Exception:
            pass

        return record

    def _parse_html(self, html: str, url: str) -> dict:
        soup = BeautifulSoup(html, "html.parser")

        title = clean(
            first(
                self._meta(soup, 'meta[property="og:title"]'),
                self._meta(soup, 'meta[name="twitter:title"]'),
                soup.title.string if soup.title else "",
            )
        )
        description = clean(
            first(
                self._meta(
                    soup,
                    'meta[property="og:description"]',
                ),
                self._meta(soup, 'meta[name="description"]'),
            )
        )
        image_url = clean(
            first(
                self._meta(soup, 'meta[property="og:image"]'),
                self._meta(soup, 'meta[name="twitter:image"]'),
            )
        )

        product_nodes = []
        reviews = []
        attributes = []

        for script in soup.find_all(
            "script",
            attrs={"type": re.compile(r"ld\+json", re.I)},
        ):
            try:
                raw = json.loads(
                    script.string or script.get_text() or "{}"
                )
            except Exception:
                continue

            for node in self._walk(raw):
                node_type = node.get("@type")
                types = (
                    node_type
                    if isinstance(node_type, list)
                    else [node_type]
                )
                if any(
                    clean(x).casefold() == "product"
                    for x in types
                ):
                    product_nodes.append(node)

        product = {}
        for node in product_nodes:
            product["name"] = first(
                product.get("name"),
                clean(node.get("name")),
            )
            product["description"] = first(
                product.get("description"),
                clean(node.get("description")),
            )
            product["brand"] = first(
                product.get("brand"),
                self._brand(node.get("brand")),
                self._brand(node.get("manufacturer")),
            )
            product["model"] = first(
                product.get("model"),
                clean(node.get("model")),
                clean(node.get("mpn")),
            )
            product["category"] = first(
                product.get("category"),
                clean(node.get("category")),
            )

            image = node.get("image")
            if isinstance(image, list):
                image = image[0] if image else ""
            if isinstance(image, dict):
                image = first(
                    image.get("url"),
                    image.get("contentUrl"),
                )
            product["image_url"] = first(
                product.get("image_url"),
                clean(image),
            )

            props = node.get("additionalProperty")
            if not isinstance(props, list):
                props = [props] if props else []
            for prop in props:
                if not isinstance(prop, dict):
                    continue
                label = clean(
                    first(prop.get("name"), prop.get("propertyID"))
                )
                value = clean(
                    first(prop.get("value"), prop.get("description"))
                )
                if label and value:
                    attributes.append({
                        "name": label,
                        "value": value,
                    })

            node_reviews = node.get("review")
            if not isinstance(node_reviews, list):
                node_reviews = (
                    [node_reviews] if node_reviews else []
                )
            for review in node_reviews:
                if not isinstance(review, dict):
                    continue
                body = clean(
                    first(
                        review.get("reviewBody"),
                        review.get("description"),
                    )
                )
                if body:
                    reviews.append(body)

        attributes.extend(self._extract_visible_specs(soup))

        page_text = clean(soup.get_text(" ", strip=True))
        benefit_texts = self._sentences_matching(
            page_text,
            (
                "benefício", "beneficio", "prático", "pratico",
                "fácil", "facil", "rapidez", "economia",
                "conforto", "saudável", "saudavel",
                "crocante", "sem óleo", "sem oleo",
            ),
        )
        included_texts = self._sentences_matching(
            page_text,
            (
                "acompanha", "inclui", "conteúdo da embalagem",
                "conteudo da embalagem", "vem com", "itens inclusos",
            ),
        )

        return {
            "title": clean(first(product.get("name"), title)),
            "description": clean(
                first(
                    product.get("description"),
                    description,
                )
            ),
            "brand": clean(product.get("brand")),
            "model": clean(product.get("model")),
            "category": clean(product.get("category")),
            "image_url": clean(
                first(product.get("image_url"), image_url)
            ),
            "attributes": self._dedupe_attributes(attributes),
            "benefit_texts": benefit_texts[:6],
            "included_texts": included_texts[:4],
            "reviews": reviews[:60],
        }

    def _extract_visible_specs(self, soup) -> list[dict]:
        found = []

        # Tabelas.
        for row in soup.select("tr"):
            cells = [
                clean(x.get_text(" ", strip=True))
                for x in row.find_all(["th", "td"])
            ]
            if len(cells) >= 2 and cells[0] and cells[1]:
                found.append({
                    "name": cells[0],
                    "value": cells[1],
                })

        # Definition lists.
        for dt in soup.find_all("dt"):
            dd = dt.find_next_sibling("dd")
            if dd:
                found.append({
                    "name": clean(dt.get_text(" ", strip=True)),
                    "value": clean(dd.get_text(" ", strip=True)),
                })

        # Linhas de texto "Campo: valor".
        for element in soup.find_all(
            ["li", "p", "div", "span"],
            limit=5000,
        ):
            text = clean(element.get_text(" ", strip=True))
            if not (4 <= len(text) <= 180):
                continue

            match = re.match(
                r"^[-•]?\s*([^:]{2,55}):\s*(.{1,110})$",
                text,
            )
            if not match:
                continue

            label = clean(match.group(1))
            value = clean(match.group(2))
            if self._is_spec_label(label):
                found.append({
                    "name": label,
                    "value": value,
                })

        return found

    def _is_spec_label(self, label: str) -> bool:
        low = clean(label).casefold()
        return any(
            token in low
            for token in (
                "marca", "modelo", "capacidade", "potência", "potencia",
                "voltagem", "tensão", "tensao", "material", "cor",
                "dimens", "peso", "garantia", "temperatura",
                "frequência", "frequencia", "bateria", "autonomia",
                "resistência", "resistencia", "bluetooth",
                "sistema operacional", "tamanho", "volume",
                "tipo de pino", "tomada",
            )
        )

    def _fuse(
        self,
        *,
        identity: dict,
        sources: list[dict],
        query: str,
    ) -> dict:
        values = {}
        confidence = {}
        field_sources = {}
        notes = []
        source_cards = []

        for source in sources:
            source_cards.append({
                "url": source["url"],
                "host": source["host"],
                "marketplace": source["marketplace"],
                "title": source.get("title", ""),
                "match_score": source.get("match_score"),
                "discovery_source": source.get("discovery_source"),
                "lens_rank": source.get("lens_rank"),
                "image_match": source.get("image_match") or {},
            })

        # Só completa marca/modelo quando existe confirmação forte.
        brand_votes = Counter(
            clean(s.get("brand"))
            for s in sources
            if clean(s.get("brand"))
        )
        model_votes = Counter(
            clean(s.get("model"))
            for s in sources
            if clean(s.get("model"))
        )

        if not identity.get("brand") and brand_votes:
            brand, count = brand_votes.most_common(1)[0]
            if count >= 2 or (
                len(sources) == 1
                and sources[0].get("match_score", 0) >= 0.9
            ):
                if brand.casefold() not in GENERIC_BRAND_WORDS:
                    values["brand"] = brand
                    confidence["brand"] = 0.88 if count >= 2 else 0.76
                    field_sources["brand"] = self._sources_with_value(
                        sources,
                        "brand",
                        brand,
                    )

        if not identity.get("model") and model_votes:
            model, count = model_votes.most_common(1)[0]
            if count >= 2:
                values["model"] = model
                confidence["model"] = 0.9
                field_sources["model"] = self._sources_with_value(
                    sources,
                    "model",
                    model,
                )

        # Descrição: prioriza português + forte identidade.
        description_options = []
        for source in sources:
            description = clean(source.get("description"))
            if not description:
                continue
            score = (
                source.get("match_score", 0)
                + portuguese_score(description) * 0.25
            )
            description_options.append((score, source, description))

        if description_options:
            description_options.sort(
                key=lambda x: x[0],
                reverse=True,
            )
            score, source, description = description_options[0]
            if portuguese_score(description) >= 0.2:
                values["description"] = description[:2400]
                confidence["description"] = round(
                    min(0.9, 0.55 + score * 0.28),
                    2,
                )
                field_sources["description"] = [
                    self._source_card(source)
                ]

        # Especificações dinâmicas com consenso.
        spec_buckets = defaultdict(list)

        for source in sources:
            for attr in source.get("attributes") or []:
                label = normalize_label(attr.get("name"))
                value = clean(attr.get("value"))
                if not label or not value:
                    continue
                if len(value) > 180:
                    continue
                spec_buckets[label].append({
                    "value": value,
                    "source": source,
                })

        technical_specs = []

        for label, entries in spec_buckets.items():
            normalized_votes = Counter(
                self._normalize_value(x["value"])
                for x in entries
            )
            normalized, count = normalized_votes.most_common(1)[0]
            matching = [
                x for x in entries
                if self._normalize_value(x["value"]) == normalized
            ]
            best = max(
                matching,
                key=lambda x: x["source"].get("match_score", 0),
            )
            source_count = len({
                marketplace_root(x["source"].get("host", ""))
                for x in matching
            })

            confidence_value = (
                0.92
                if source_count >= 2
                else 0.76
            )

            technical_specs.append({
                "name": label,
                "value": best["value"],
                "confidence": confidence_value,
                "source_count": source_count,
                "sources": [
                    self._source_card(x["source"])
                    for x in matching[:5]
                ],
            })

        technical_specs.sort(
            key=lambda x: (
                -x["source_count"],
                x["name"].casefold(),
            )
        )

        # Mapeia algumas especificações para os campos existentes.
        spec_map = {
            item["name"].casefold(): item
            for item in technical_specs
        }

        size_labels = [
            "capacidade", "dimensões", "peso", "volume", "tamanho",
        ]
        size_parts = [
            f"{item['name']}: {item['value']}"
            for item in technical_specs
            if any(
                key in item["name"].casefold()
                for key in size_labels
            )
        ][:6]
        if size_parts:
            values["size_info"] = "; ".join(size_parts)
            confidence["size_info"] = max(
                item["confidence"]
                for item in technical_specs
                if any(
                    key in item["name"].casefold()
                    for key in size_labels
                )
            )
            field_sources["size_info"] = self._merge_sources(
                [
                    item["sources"]
                    for item in technical_specs
                    if any(
                        key in item["name"].casefold()
                        for key in size_labels
                    )
                ]
            )

        compatibility_labels = [
            "voltagem", "tensão", "bluetooth",
            "sistema operacional", "compatibilidade",
        ]
        compatibility_parts = [
            f"{item['name']}: {item['value']}"
            for item in technical_specs
            if any(
                key in item["name"].casefold()
                for key in compatibility_labels
            )
        ][:6]
        if compatibility_parts:
            values["compatibility"] = "; ".join(
                compatibility_parts
            )
            confidence["compatibility"] = 0.84
            field_sources["compatibility"] = self._merge_sources(
                [
                    item["sources"]
                    for item in technical_specs
                    if any(
                        key in item["name"].casefold()
                        for key in compatibility_labels
                    )
                ]
            )

        warranty = next(
            (
                item
                for item in technical_specs
                if "garantia" in item["name"].casefold()
            ),
            None,
        )
        if warranty:
            values["warranty"] = warranty["value"]
            confidence["warranty"] = warranty["confidence"]
            field_sources["warranty"] = warranty["sources"]

        battery_items = [
            item
            for item in technical_specs
            if any(
                key in item["name"].casefold()
                for key in ("bateria", "autonomia", "carregamento")
            )
        ]
        if battery_items:
            values["battery_info"] = "; ".join(
                f"{x['name']}: {x['value']}"
                for x in battery_items[:5]
            )
            confidence["battery_info"] = max(
                x["confidence"] for x in battery_items
            )
            field_sources["battery_info"] = self._merge_sources(
                [x["sources"] for x in battery_items]
            )

        # Benefícios: apenas frases encontradas nas páginas aceitas.
        benefits = []
        for source in sources:
            for text in source.get("benefit_texts") or []:
                if text not in benefits:
                    benefits.append(text)
        if benefits:
            values["key_benefits"] = "; ".join(benefits[:4])[:1800]
            confidence["key_benefits"] = 0.66
            field_sources["key_benefits"] = source_cards[:4]

        included = []
        for source in sources:
            for text in source.get("included_texts") or []:
                if text not in included:
                    included.append(text)
        if included:
            values["included_items"] = "; ".join(included[:3])[:1200]
            confidence["included_items"] = 0.68
            field_sources["included_items"] = source_cards[:4]

        if not sources:
            notes.append(
                "Nenhum marketplace público compatível foi encontrado nesta tentativa."
            )
        elif len(sources) == 1:
            notes.append(
                "Apenas um marketplace compatível foi acessível; campos de fonte única ficam com confiança moderada."
            )

        notes.append(
            "Preços externos não são usados na condição da LIVE."
        )

        return {
            "values": values,
            "confidence": confidence,
            "field_sources": field_sources,
            "technical_specs": technical_specs,
            "sources": source_cards,
            "query": query,
            "notes": notes,
            "review_texts": self._collect_reviews(sources),
        }

    def _sources_with_value(
        self,
        sources: list[dict],
        field: str,
        value: str,
    ) -> list[dict]:
        target = clean(value).casefold()
        return [
            self._source_card(source)
            for source in sources
            if clean(source.get(field)).casefold() == target
        ][:5]

    def _source_card(self, source: dict) -> dict:
        return {
            "url": source.get("url"),
            "host": source.get("host"),
            "marketplace": source.get("marketplace"),
            "title": source.get("title"),
            "match_score": source.get("match_score"),
            "discovery_source": source.get("discovery_source"),
            "lens_rank": source.get("lens_rank"),
            "image_match": source.get("image_match") or {},
            "image_url": source.get("image_url"),
            "verification": source.get("verification"),
            "verification_reason": source.get("verification_reason"),
        }

    def _merge_sources(
        self,
        groups: list[list[dict]],
    ) -> list[dict]:
        out = []
        seen = set()
        for group in groups:
            for source in group:
                url = source.get("url")
                if not url or url in seen:
                    continue
                seen.add(url)
                out.append(source)
        return out[:6]

    def _collect_reviews(self, sources: list[dict]) -> list[str]:
        out = []
        for source in sources:
            for review in source.get("reviews") or []:
                text = clean(review)
                if text and text not in out:
                    out.append(text)
        return out[:250]

    def _dedupe_attributes(
        self,
        attributes: list[dict],
    ) -> list[dict]:
        out = []
        seen = set()

        for item in attributes:
            label = normalize_label(item.get("name"))
            value = clean(item.get("value"))
            if not label or not value:
                continue

            key = (
                label.casefold(),
                self._normalize_value(value),
            )
            if key in seen:
                continue
            seen.add(key)
            out.append({
                "name": label,
                "value": value,
            })

        return out[:100]

    def _normalize_value(self, value: str) -> str:
        low = clean(value).casefold()
        low = low.replace(" ", "")
        low = low.replace(",", ".")
        low = re.sub(r"[^a-z0-9à-ÿ./x°-]", "", low)
        return low

    def _sentences_matching(
        self,
        text: str,
        keywords: tuple[str, ...],
    ) -> list[str]:
        pieces = [
            clean(x)
            for x in re.split(r"(?<=[.!?;])\s+", clean(text))
            if 24 <= len(clean(x)) <= 320
        ]

        out = []
        for piece in pieces:
            low = piece.casefold()
            if any(keyword in low for keyword in keywords):
                if piece not in out:
                    out.append(piece)
        return out

    def _meta(
        self,
        soup: BeautifulSoup,
        selector: str,
    ) -> str:
        tag = soup.select_one(selector)
        return clean(tag.get("content")) if tag else ""

    def _brand(self, value) -> str:
        if isinstance(value, dict):
            return clean(
                first(
                    value.get("name"),
                    value.get("brand"),
                    value.get("value"),
                )
            )
        return clean(value)

    def _walk(self, value):
        if isinstance(value, dict):
            yield value
            for nested in value.values():
                yield from self._walk(nested)
        elif isinstance(value, list):
            for item in value:
                yield from self._walk(item)


def first(*values):
    for value in values:
        if value not in (None, "", [], {}):
            return value
    return None

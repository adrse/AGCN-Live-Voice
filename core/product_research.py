from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from urllib.parse import parse_qs, quote_plus, unquote, unquote_plus, urlparse

import httpx
from bs4 import BeautifulSoup


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0 Safari/537.36"
)

BLOCKED_HOST_FRAGMENTS = {
    "facebook.com",
    "instagram.com",
    "pinterest.com",
    "youtube.com",
    "wikipedia.org",
    "simple.wikipedia.org",
}

COMMERCE_HOSTS = {
    "shopee.com.br",
    "mercadolivre.com.br",
    "mercadolivre.com",
    "amazon.com.br",
    "magazineluiza.com.br",
    "casasbahia.com.br",
    "carrefour.com.br",
    "ponto.com.br",
    "extra.com.br",
    "kabum.com.br",
    "americanas.com.br",
    "aliexpress.com",
}

COMMERCE_LABELS = {
    "shopee.com.br": "Shopee",
    "mercadolivre.com.br": "Mercado Livre",
    "mercadolivre.com": "Mercado Livre",
    "amazon.com.br": "Amazon",
    "magazineluiza.com.br": "Magazine Luiza",
    "casasbahia.com.br": "Casas Bahia",
    "carrefour.com.br": "Carrefour",
    "ponto.com.br": "Ponto",
    "extra.com.br": "Extra",
    "kabum.com.br": "KaBuM!",
    "americanas.com.br": "Americanas",
    "aliexpress.com": "AliExpress",
}

STOPWORDS = {
    "para", "com", "sem", "uma", "um", "de", "da", "do", "das", "dos",
    "e", "em", "no", "na", "nos", "nas", "por", "the", "a", "o", "of",
    "kit", "produto", "shop", "tiktok", "brasil", "oficial", "loja",
}

POSITIVE_WORDS = {
    "bom", "boa", "ótimo", "otimo", "excelente", "prático", "pratico",
    "fácil", "facil", "rápido", "rapido", "resistente", "qualidade",
    "gostei", "amei", "recomendo", "perfeito", "funciona", "bonito",
    "custo-benefício", "custo beneficio",
}

NEGATIVE_WORDS = {
    "ruim", "fraco", "difícil", "dificil", "problema", "defeito",
    "quebrou", "parou", "pequeno", "caro", "demora", "atraso",
    "não funciona", "nao funciona", "bateria ruim", "decepcion",
}


def _clean(value) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _host(url: str) -> str:
    try:
        return urlparse(url).netloc.casefold().removeprefix("www.")
    except Exception:
        return ""


def _commerce_root(host: str) -> str | None:
    host = (host or "").casefold().removeprefix("www.")
    for root in COMMERCE_HOSTS:
        if host == root or host.endswith("." + root):
            return root
    return None


def _is_commerce_host(host: str) -> bool:
    return _commerce_root(host) is not None


def _specific_tokens(text: str) -> set[str]:
    """Tokens que ajudam a distinguir produtos parecidos."""
    low = _clean(text).casefold()
    out = set()

    for value, unit in re.findall(
        r"\b(\d+(?:[.,]\d+)?)\s*(ml|l|cm|mm|kg|g|mah|atm|hz|w|v)\b",
        low,
        flags=re.I,
    ):
        out.add((value.replace(",", ".") + unit).casefold())

    for token in re.findall(r"\b[a-z]{1,5}\d+[a-z0-9-]*\b", low, flags=re.I):
        out.add(token.casefold())

    return out


def _meaningful_product_tokens(text: str) -> set[str]:
    tokens = _tokens(text)
    generic = {
        "compre", "comprar", "oferta", "promoção", "promocao", "preço",
        "preco", "frete", "grátis", "gratis", "original", "premium",
        "unidade", "unidades", "até", "ate", "kit", "conjunto",
    }
    return {x for x in tokens if x not in generic}


def _tokens(text: str) -> set[str]:
    raw = re.findall(r"[\wÀ-ÿ-]{3,}", _clean(text).casefold())
    return {x for x in raw if x not in STOPWORDS and not x.isdigit()}


def _similarity(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / max(1, min(len(ta), len(tb)))


def _first(*values):
    for value in values:
        if value not in (None, "", [], {}):
            return value
    return None


def _safe_float(value):
    if value in (None, ""):
        return None
    try:
        raw = str(value).strip().replace("R$", "").replace(" ", "")
        if "," in raw and "." in raw:
            raw = raw.replace(".", "").replace(",", ".")
        elif "," in raw:
            raw = raw.replace(",", ".")
        return float(raw)
    except Exception:
        return None


def _iter_jsonld(value):
    if isinstance(value, dict):
        yield value
        for nested in value.values():
            yield from _iter_jsonld(nested)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_jsonld(item)


def _type_contains(node: dict, expected: str) -> bool:
    value = node.get("@type")
    if isinstance(value, list):
        return expected.casefold() in {
            str(x).casefold() for x in value
        }
    return str(value or "").casefold() == expected.casefold()


def _brand_value(value):
    if isinstance(value, dict):
        return _clean(value.get("name"))
    if isinstance(value, list):
        for item in value:
            found = _brand_value(item)
            if found:
                return found
        return ""
    return _clean(value)


def _offers_price(offers):
    if isinstance(offers, list):
        for offer in offers:
            value = _offers_price(offer)
            if value is not None:
                return value
        return None
    if not isinstance(offers, dict):
        return None
    return _safe_float(
        _first(
            offers.get("price"),
            offers.get("lowPrice"),
            offers.get("highPrice"),
        )
    )


def _review_texts(node: dict) -> list[str]:
    reviews = node.get("review")
    if not reviews:
        return []
    if not isinstance(reviews, list):
        reviews = [reviews]

    out = []
    for review in reviews:
        if not isinstance(review, dict):
            continue
        body = _first(
            review.get("reviewBody"),
            review.get("description"),
            review.get("name"),
        )
        if body:
            out.append(_clean(body))
    return out


class ProductResearchEngine:
    """Pesquisa pública e conservadora para montar um rascunho de produto.

    Não tenta contornar login, captcha ou bloqueios. Quando uma fonte não é
    publicamente acessível, ela é registrada como indisponível e a pesquisa
    continua com outras fontes.
    """

    def __init__(self):
        self.client = httpx.Client(
            follow_redirects=True,
            timeout=httpx.Timeout(12.0, connect=8.0),
            headers={
                "User-Agent": USER_AGENT,
                "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.7",
                "Accept": "text/html,application/xhtml+xml,application/json;q=0.8,*/*;q=0.5",
            },
        )

    def analyze(self, url: str, hint: str = "") -> dict:
        url = _clean(url)
        if not url.startswith(("http://", "https://")):
            raise ValueError("Informe um link válido do produto.")

        direct = self._fetch_source(url, source_type="submitted_link")
        resolved_url = direct.get("final_url") or url

        # O TikTok inclui no próprio link compartilhado metadados muito úteis
        # (og_info/ec_search_share_params). Eles são mais confiáveis para
        # IDENTIFICAR o produto do que o HTML de uma página anti-bot.
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

        if metadata:
            product = direct.setdefault("product", {})
            if metadata.get("name"):
                product["name"] = metadata["name"]
                direct["title"] = metadata["name"]
            if metadata.get("image_url"):
                product["image_url"] = metadata["image_url"]
                direct["image_url"] = metadata["image_url"]
            direct["url_metadata"] = metadata

        seed = self._seed_from_source(direct)

        if not seed.get("name"):
            inferred_name = self._name_from_description(
                direct.get("description") or ""
            )
            if inferred_name:
                seed["name"] = inferred_name

        if metadata.get("name"):
            seed["name"] = metadata["name"]
        if metadata.get("image_url"):
            seed["image_url"] = metadata["image_url"]
        if metadata.get("product_url"):
            seed["product_url"] = metadata["product_url"]

        if hint:
            seed["name"] = _clean(hint)

        identity = self._identity_from_title(seed.get("name") or "")

        for key in ("brand", "model", "category"):
            if not seed.get(key) and identity.get(key):
                seed[key] = identity[key]

        if identity.get("brand") and identity.get("model"):
            search_name = identity.get("search_name")
        else:
            search_name = _first(
                self._canonical_search_name(seed.get("name") or ""),
                seed.get("name"),
                self._title_hint_from_url(resolved_url),
            )

        sources = [direct]
        search_results = []

        if search_name:
            search_results = self._search_public_web(
                search_name,
                brand=seed.get("brand") or "",
                model=seed.get("model") or "",
                category=seed.get("category") or "",
            )
            candidates = self._select_candidates(
                search_name,
                seed.get("brand") or "",
                seed.get("model") or "",
                search_results,
                limit=8,
            )

            for candidate in candidates:
                fetched = self._fetch_source(
                    candidate["url"],
                    source_type="public_web",
                    snippet=candidate.get("snippet"),
                    search_title=candidate.get("title"),
                )
                sources.append(fetched)

        values, confidence, field_sources, reviews = self._aggregate(
            sources,
            seed,
        )

        review_summary = self._analyze_reviews(
            reviews,
            search_results,
        )

        faq = self._extract_faq(search_results, reviews)

        usable_sources = [
            self._public_source_record(s)
            for s in sources
            if s.get("ok")
        ]

        notes = []
        if not direct.get("ok"):
            notes.append(
                "O link original não pôde ser lido publicamente; "
                "a pesquisa usou apenas as fontes que estavam acessíveis."
            )
        if not search_name:
            notes.append(
                "Não foi possível identificar automaticamente o nome do produto. "
                "Informe o nome/modelo manualmente e tente novamente."
            )
        if not usable_sources:
            notes.append(
                "Nenhuma fonte pública foi acessível nesta tentativa."
            )

        return {
            "ok": bool(values.get("name") or usable_sources),
            "submitted_url": url,
            "resolved_url": resolved_url,
            "values": values,
            "confidence": confidence,
            "field_sources": field_sources,
            "research_summary": {
                "status": "completed",
                "source_count": len(usable_sources),
                "review_count": len(reviews),
                "faq": faq,
                "review_summary": review_summary,
                "sources": usable_sources,
                "notes": notes,
                "search_query": search_name or "",
                "identifiers": {
                    "tiktok_product_id": metadata.get("product_id"),
                    "group_id": metadata.get("group_id"),
                },
            },
        }

    def _decode_json_query_param(self, url: str, key: str) -> dict:
        try:
            values = parse_qs(
                urlparse(url).query,
                keep_blank_values=True,
            ).get(key)
        except Exception:
            return {}

        if not values:
            return {}

        raw = values[0]
        for _ in range(5):
            try:
                decoded = json.loads(raw)
                return decoded if isinstance(decoded, dict) else {}
            except Exception:
                pass

            new_raw = unquote_plus(raw)
            if new_raw == raw:
                break
            raw = new_raw

        return {}

    def _metadata_from_url(self, url: str) -> dict:
        if not url:
            return {}

        og = self._decode_json_query_param(url, "og_info")
        share = self._decode_json_query_param(
            url,
            "ec_search_share_params",
        )

        parsed = urlparse(url)
        path_match = re.search(r"/pdp/(\d+)", parsed.path)

        product_id = _first(
            share.get("product_id"),
            path_match.group(1) if path_match else None,
        )
        group_id = share.get("group_id")

        name = self._clean_product_title(
            _clean(og.get("title"))
        )
        image_url = _clean(og.get("image"))

        if not any((name, image_url, product_id, group_id)):
            return {}

        return {
            "name": name,
            "image_url": image_url,
            "product_id": str(product_id) if product_id else None,
            "group_id": str(group_id) if group_id else None,
            "product_url": url,
        }

    def _fetch_source(
        self,
        url: str,
        *,
        source_type: str,
        snippet: str = "",
        search_title: str = "",
    ) -> dict:
        record = {
            "url": url,
            "final_url": url,
            "host": _host(url),
            "source_type": source_type,
            "ok": False,
            "status_code": None,
            "title": _clean(search_title),
            "description": _clean(snippet),
            "image_url": "",
            "product": {},
            "reviews": [],
            "error": None,
            "redirect_urls": [],
        }

        try:
            response = self.client.get(url)
            record["status_code"] = response.status_code
            record["redirect_urls"] = [
                str(item.next_request.url)
                for item in response.history
                if getattr(item, "next_request", None) is not None
            ]
            record["final_url"] = str(response.url)
            record["host"] = _host(str(response.url))

            if response.status_code >= 400:
                record["error"] = f"HTTP {response.status_code}"
                return record

            content_type = response.headers.get("content-type", "")
            if "html" not in content_type and "json" not in content_type:
                record["error"] = "Conteúdo não suportado"
                return record

            if "json" in content_type:
                record["ok"] = True
                return record

            parsed = self._parse_html(
                response.text,
                str(response.url),
            )
            record.update(parsed)
            record["ok"] = True
            return record
        except Exception as exc:
            record["error"] = str(exc)[:180]
            return record

    def _parse_html(self, html: str, url: str) -> dict:
        soup = BeautifulSoup(html, "html.parser")

        def meta(*selectors):
            for selector, attr in selectors:
                tag = soup.select_one(selector)
                if tag:
                    value = tag.get(attr)
                    if value:
                        return _clean(value)
            return ""

        title = _first(
            meta(('meta[property="og:title"]', "content")),
            meta(('meta[name="twitter:title"]', "content")),
            _clean(soup.title.string if soup.title else ""),
        ) or ""

        description = _first(
            meta(('meta[property="og:description"]', "content")),
            meta(('meta[name="description"]', "content")),
            meta(('meta[name="twitter:description"]', "content")),
        ) or ""

        image_url = _first(
            meta(('meta[property="og:image"]', "content")),
            meta(('meta[name="twitter:image"]', "content")),
        ) or ""

        product_nodes = []
        all_nodes = []

        for script in soup.find_all(
            "script",
            attrs={"type": re.compile(r"ld\+json", re.I)},
        ):
            try:
                raw = json.loads(script.string or script.get_text() or "{}")
            except Exception:
                continue

            for node in _iter_jsonld(raw):
                all_nodes.append(node)
                if _type_contains(node, "Product"):
                    product_nodes.append(node)

        product = {}
        reviews = []

        for node in product_nodes:
            product["name"] = _first(
                product.get("name"),
                _clean(node.get("name")),
            )
            product["description"] = _first(
                product.get("description"),
                _clean(node.get("description")),
            )
            product["brand"] = _first(
                product.get("brand"),
                _brand_value(node.get("brand")),
                _brand_value(node.get("manufacturer")),
            )
            product["model"] = _first(
                product.get("model"),
                _clean(node.get("model")),
                _clean(node.get("mpn")),
                _clean(node.get("sku")),
            )
            product["category"] = _first(
                product.get("category"),
                _clean(node.get("category")),
            )
            image = node.get("image")
            if isinstance(image, list):
                image = image[0] if image else ""
            if isinstance(image, dict):
                image = image.get("url")
            product["image_url"] = _first(
                product.get("image_url"),
                _clean(image),
            )
            product["price"] = _first(
                product.get("price"),
                _offers_price(node.get("offers")),
            )

            rating = node.get("aggregateRating")
            if isinstance(rating, dict):
                product["rating"] = _first(
                    product.get("rating"),
                    _safe_float(rating.get("ratingValue")),
                )
                product["review_count"] = _first(
                    product.get("review_count"),
                    _safe_float(
                        _first(
                            rating.get("reviewCount"),
                            rating.get("ratingCount"),
                        )
                    ),
                )

            reviews.extend(_review_texts(node))

        # TikTok e algumas lojas colocam os dados do produto em JSON
        # de hidratação, sem JSON-LD padrão.
        embedded_product = self._extract_embedded_product(soup)
        for key, value in embedded_product.items():
            if value not in (None, "", [], {}):
                product[key] = _first(product.get(key), value)

        # Alguns sites usam FAQPage em JSON-LD.
        faq = []
        for node in all_nodes:
            if not _type_contains(node, "FAQPage"):
                continue
            main = node.get("mainEntity")
            if not isinstance(main, list):
                main = [main] if main else []
            for item in main:
                if not isinstance(item, dict):
                    continue
                question = _clean(item.get("name"))
                accepted = item.get("acceptedAnswer")
                answer = (
                    _clean(accepted.get("text"))
                    if isinstance(accepted, dict)
                    else ""
                )
                if question:
                    faq.append({
                        "question": question,
                        "answer": answer,
                        "source_url": url,
                    })

        return {
            "title": title,
            "description": description,
            "image_url": image_url,
            "product": product,
            "reviews": reviews[:80],
            "faq": faq[:30],
        }

    def _extract_embedded_product(self, soup) -> dict:
        candidates = []

        for script in soup.find_all("script"):
            raw = script.string or script.get_text() or ""
            if len(raw) < 80:
                continue

            script_id = str(script.get("id") or "").casefold()
            script_type = str(script.get("type") or "").casefold()

            if (
                "json" not in script_type
                and "universal" not in script_id
                and "sigi" not in script_id
                and "next_data" not in script_id
            ):
                continue

            try:
                data = json.loads(raw)
            except Exception:
                continue

            for node in _iter_jsonld(data):
                keys = {str(k).casefold() for k in node.keys()}
                has_product_id = any(
                    k in keys
                    for k in (
                        "product_id",
                        "productid",
                        "product_id_str",
                        "item_id",
                    )
                )
                has_product_name = any(
                    k in keys
                    for k in (
                        "product_name",
                        "productname",
                        "product_title",
                        "title",
                    )
                )

                if not (has_product_id and has_product_name):
                    continue

                name = _first(
                    node.get("product_name"),
                    node.get("productName"),
                    node.get("product_title"),
                    node.get("title"),
                    node.get("name"),
                )

                if not name:
                    continue

                candidate = {
                    "name": _clean(name),
                    "brand": _clean(
                        _first(
                            node.get("brand_name"),
                            node.get("brandName"),
                            node.get("brand"),
                        )
                    ),
                    "model": _clean(
                        _first(
                            node.get("model"),
                            node.get("sku_name"),
                            node.get("skuName"),
                        )
                    ),
                    "description": _clean(
                        _first(
                            node.get("description"),
                            node.get("product_description"),
                            node.get("productDescription"),
                        )
                    ),
                    "price": self._deep_price(node),
                    "image_url": self._deep_image(node),
                }
                candidates.append(candidate)

        if not candidates:
            return {}

        candidates.sort(
            key=lambda x: (
                bool(x.get("price")),
                bool(x.get("brand")),
                len(x.get("description") or ""),
            ),
            reverse=True,
        )
        return candidates[0]

    def _deep_price(self, node: dict):
        direct_keys = (
            "sale_price",
            "salePrice",
            "current_price",
            "currentPrice",
            "price",
        )
        for key in direct_keys:
            if key not in node:
                continue
            value = node.get(key)
            if isinstance(value, dict):
                for nested_key in (
                    "amount",
                    "price",
                    "value",
                    "min_price",
                    "minPrice",
                ):
                    parsed = _safe_float(value.get(nested_key))
                    if parsed is not None:
                        return parsed
            else:
                parsed = _safe_float(value)
                if parsed is not None:
                    return parsed
        return None

    def _deep_image(self, node: dict) -> str:
        for key in (
            "image_url",
            "imageUrl",
            "cover_url",
            "coverUrl",
            "image",
            "images",
            "cover",
        ):
            value = node.get(key)
            if isinstance(value, str) and value.startswith("http"):
                return value
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, str) and item.startswith("http"):
                        return item
                    if isinstance(item, dict):
                        found = self._deep_image(item)
                        if found:
                            return found
            if isinstance(value, dict):
                for nested in ("url", "url_list", "urlList"):
                    nested_value = value.get(nested)
                    if isinstance(nested_value, str) and nested_value.startswith("http"):
                        return nested_value
                    if isinstance(nested_value, list):
                        for item in nested_value:
                            if isinstance(item, str) and item.startswith("http"):
                                return item
        return ""

    def _seed_from_source(self, source: dict) -> dict:
        product = source.get("product") or {}
        title = _clean(
            _first(
                product.get("name"),
                source.get("title"),
            )
        )
        title = self._clean_product_title(title)

        return {
            "product_url": source.get("final_url") or source.get("url") or "",
            "name": title,
            "brand": _clean(product.get("brand")),
            "model": _clean(product.get("model")),
            "category": _clean(product.get("category")),
            "description": _clean(
                _first(
                    product.get("description"),
                    source.get("description"),
                )
            ),
            "image_url": _clean(
                _first(
                    product.get("image_url"),
                    source.get("image_url"),
                )
            ),
            "observed_price": product.get("price"),
        }

    def _clean_product_title(self, title: str) -> str:
        original = _clean(title)
        low = original.casefold()
        blocked_titles = {
            "tiktok",
            "tiktok - make your day",
            "tiktok shop",
            "make your day | tiktok",
            "security check",
            "access denied",
            "just a moment...",
            "just a moment",
            "verify you are human",
            "are you a robot?",
            "robot or human?",
        }
        if low in blocked_titles or any(
            marker in low
            for marker in (
                "security check",
                "verify you are human",
                "captcha",
                "access denied",
                "attention required",
            )
        ):
            return ""

        title = re.sub(
            r"\s*[|·-]\s*(TikTok Shop|TikTok).*?$",
            "",
            title,
            flags=re.I,
        )
        title = re.sub(
            r"^(TikTok Shop\s*[-|:]\s*)",
            "",
            title,
            flags=re.I,
        )
        return _clean(title)[:220]

    def _name_from_description(self, description: str) -> str:
        text = _clean(description)
        if not text:
            return ""

        # Páginas de marketplace às vezes expõem apenas uma meta description:
        # "Compre NOME DO PRODUTO na Shopee/TikTok Shop...".
        text = re.sub(
            r"^(compre|comprar|oferta de|encontre)\s+",
            "",
            text,
            flags=re.I,
        )

        separators = [
            r"\s+no\s+tiktok\s+shop\b",
            r"\s+na\s+shopee\b",
            r"\s+na\s+amazon\b",
            r"\s+no\s+mercado\s+livre\b",
            r"\.\s*descubra\b",
            r"\.\s*aproveite\b",
            r"\s+por\s+apenas\b",
        ]

        for pattern in separators:
            parts = re.split(pattern, text, maxsplit=1, flags=re.I)
            if len(parts) > 1:
                text = parts[0]
                break

        text = _clean(text).strip(" -|:;,.")
        if not (5 <= len(text) <= 180):
            return ""

        # Rejeita descrições genéricas de segurança/erro.
        if self._clean_product_title(text) == "":
            return ""

        return text

    def _identity_from_title(self, title: str) -> dict:
        text = self._clean_product_title(title)
        if not text:
            return {}

        # Ex.: "Aurafit G6 Smartwatch para Esportes Relógio: ..."
        # A identidade é deliberadamente curta para evitar contaminar a busca
        # com dezenas de atributos promocionais do anúncio.
        words = re.findall(r"[A-Za-zÀ-ÿ0-9-]+", text)
        if not words:
            return {}

        brand = ""
        model = ""
        category = ""

        # O primeiro token costuma ser a marca quando o título vem da própria
        # ficha do produto. Evitamos termos genéricos.
        generic_first = {
            "smartwatch", "relogio", "relógio", "kit", "produto",
            "oferta", "novo", "original",
        }
        first = words[0]
        if first.casefold() not in generic_first and not first.isdigit():
            brand = first

        for token in words[1:8]:
            if re.fullmatch(r"[A-Za-z]{1,5}\d+[A-Za-z0-9-]*", token):
                model = token
                break

        low = text.casefold()
        if "smartwatch" in low or "relógio" in low or "relogio" in low:
            category = "Smartwatch"
        elif (
            "fitness" in low
            and any(x in low for x in ("calça", "calca", "top", "legging"))
        ):
            category = "Moda Fitness"
        elif any(x in low for x in ("calça", "calca", "legging")):
            category = "Calça"
        elif any(x in low for x in ("fone", "earbud", "headphone")):
            category = "Áudio"
        elif any(x in low for x in ("mop", "rodo", "limpeza")):
            category = "Casa e Limpeza"
        elif (
            "pote" in low
            and "vidro" in low
            and any(x in low for x in ("hermético", "hermetico", "marmita"))
        ):
            category = "Potes e Marmitas"
        elif any(x in low for x in ("pote", "marmita", "mantimento")):
            category = "Cozinha e Armazenamento"

        parts = [x for x in (brand, model, category) if x]
        search_name = " ".join(parts[:3]).strip()

        if not search_name:
            search_name = " ".join(words[:6])

        return {
            "brand": brand,
            "model": model,
            "category": category,
            "search_name": search_name,
        }

    def _canonical_search_name(self, title: str) -> str:
        text = self._clean_product_title(title)
        if not text:
            return ""

        # Mantém substantivos e medidas que identificam o produto e remove
        # linguagem puramente promocional.
        text = re.sub(
            r"\b(compre|comprar|oferta|promoção|promocao|frete grátis|frete gratis|"
            r"leve o|na sua aventura|monitor de performance completo)\b.*$",
            "",
            text,
            flags=re.I,
        )
        text = re.sub(r"\s+", " ", text).strip(" -|:;,.")
        words = text.split()

        # Para títulos longos, 14 termos costumam preservar produto + variantes.
        return " ".join(words[:14])

    def _title_hint_from_url(self, url: str) -> str:
        path = urlparse(url).path
        chunks = [
            x for x in re.split(r"[/_-]+", path)
            if len(x) >= 3 and not x.isdigit()
        ]
        return _clean(" ".join(chunks[-8:]))[:140]

    def _search_public_web(
        self,
        query: str,
        *,
        brand: str = "",
        model: str = "",
        category: str = "",
    ) -> list[dict]:
        compact = " ".join(
            x for x in (brand, model, category) if x
        ).strip() or query

        canonical = self._canonical_search_name(query) or compact
        commerce_domains = [
            "shopee.com.br",
            "mercadolivre.com.br",
            "magazineluiza.com.br",
            "amazon.com.br",
            "casasbahia.com.br",
            "carrefour.com.br",
        ]

        searches = [
            f'site:{domain} "{canonical}"'
            for domain in commerce_domains
        ]

        if brand and model:
            searches.insert(
                0,
                f'"{brand}" "{model}" produto',
            )

        seen = set()
        results = []

        for search_query in searches:
            try:
                url = (
                    "https://html.duckduckgo.com/html/?q="
                    + quote_plus(search_query)
                )
                response = self.client.get(url)
                if response.status_code >= 400:
                    continue

                soup = BeautifulSoup(response.text, "html.parser")

                for result in soup.select(".result"):
                    link = result.select_one(".result__a")
                    snippet = result.select_one(".result__snippet")
                    if not link:
                        continue

                    href = link.get("href") or ""
                    title = _clean(link.get_text(" ", strip=True))
                    snippet_text = _clean(
                        snippet.get_text(" ", strip=True)
                        if snippet
                        else ""
                    )

                    if href.startswith("//"):
                        href = "https:" + href

                    # DuckDuckGo costuma retornar um redirect com o destino
                    # real no parâmetro uddg.
                    if "duckduckgo.com/l/" in href:
                        try:
                            parsed = urlparse(href)
                            target = parse_qs(parsed.query).get("uddg", [None])[0]
                            if target:
                                href = unquote(target)
                        except Exception:
                            pass

                    if not href.startswith("http"):
                        continue

                    host = _host(href)
                    if (
                        not host
                        or any(
                            blocked in host
                            for blocked in BLOCKED_HOST_FRAGMENTS
                        )
                        or not _is_commerce_host(host)
                    ):
                        continue

                    key = href.split("#")[0]
                    if key in seen:
                        continue

                    seen.add(key)
                    results.append({
                        "url": key,
                        "host": host,
                        "title": title,
                        "snippet": snippet_text,
                        "query": search_query,
                    })

                    if len(results) >= 20:
                        return results
            except Exception:
                continue

        return results

    def _select_candidates(
        self,
        name: str,
        brand: str,
        model: str,
        results: list[dict],
        limit: int,
    ) -> list[dict]:
        scored = []
        identity_tokens = _meaningful_product_tokens(name)
        identity_specific = _specific_tokens(name)

        for result in results:
            host = result.get("host", "")
            if not _is_commerce_host(host):
                continue

            haystack = (
                result.get("title", "")
                + " "
                + result.get("snippet", "")
            )
            low_haystack = haystack.casefold()
            result_tokens = _meaningful_product_tokens(haystack)
            result_specific = _specific_tokens(haystack)

            brand_match = bool(
                brand and brand.casefold() in low_haystack
            )
            model_match = bool(
                model and model.casefold() in low_haystack
            )

            # Produto com marca/modelo claros: ambos precisam aparecer.
            if brand and model and not (brand_match and model_match):
                continue

            overlap = (
                len(identity_tokens & result_tokens)
                / max(1, min(len(identity_tokens), len(result_tokens)))
            )

            # Produtos genéricos (potes, roupas etc.) precisam bater em vários
            # termos do título. Uma coincidência numérica isolada não basta.
            common_terms = identity_tokens & result_tokens
            if not (brand and model):
                if len(common_terms) < 3:
                    continue
                if overlap < 0.34:
                    continue

                # Quando o título tem capacidades/medidas, pelo menos uma deve
                # coincidir. Isso evita misturar potes 640 ml com produtos sem relação.
                if identity_specific and not (identity_specific & result_specific):
                    continue

            score = overlap

            if brand_match:
                score += 0.30
            if model_match:
                score += 0.35

            specific_matches = len(identity_specific & result_specific)
            score += min(0.24, specific_matches * 0.08)

            scored.append((score, result))

        scored.sort(key=lambda x: x[0], reverse=True)

        # Diversifica por marketplace: evita 8 resultados quase iguais da mesma loja.
        selected = []
        per_root = Counter()
        for score, result in scored:
            root = _commerce_root(result.get("host", "")) or result.get("host", "")
            if per_root[root] >= 2:
                continue
            selected.append(result)
            per_root[root] += 1
            if len(selected) >= limit:
                break

        return selected

    def _aggregate(
        self,
        sources: list[dict],
        seed: dict,
    ):
        candidates = defaultdict(list)
        reviews = []

        def add(field, value, score, source):
            if value in (None, "", [], {}):
                return
            candidates[field].append({
                "value": value,
                "score": score,
                "source": self._public_source_record(source),
            })

        # O link fornecido pelo usuário é nossa melhor pista de identidade,
        # mas não recebe confiança máxima caso não exponha dados estruturados.
        direct = sources[0] if sources else {}
        direct_score = 0.88 if direct.get("ok") else 0.45

        for field, value in seed.items():
            if field == "observed_price":
                continue
            score = direct_score
            if field == "brand" and value:
                score = max(score, 0.93)
            elif field == "model" and value:
                score = max(score, 0.94)
            elif field == "category" and value:
                score = max(score, 0.86)
            add(field, value, score, direct)

        for source in sources:
            if not source.get("ok"):
                continue

            if (
                source.get("source_type") != "submitted_link"
                and not _is_commerce_host(source.get("host", ""))
            ):
                continue

            product = source.get("product") or {}
            source_name = _first(
                product.get("name"),
                source.get("title"),
            ) or ""
            match = _similarity(
                seed.get("name") or source_name,
                source_name + " " + source.get("description", ""),
            )

            base = 0.58 + min(0.25, match * 0.25)
            if source.get("source_type") == "submitted_link":
                base = max(base, 0.88)

            add("name", self._clean_product_title(source_name), base, source)

            external_brand = _clean(product.get("brand"))
            external_model = _clean(product.get("model"))

            if source.get("source_type") == "submitted_link":
                add(
                    "brand",
                    external_brand,
                    min(0.96, base + 0.08),
                    source,
                )
                add(
                    "model",
                    external_model,
                    min(0.96, base + 0.08),
                    source,
                )
            else:
                # Marketplace externo serve para CONFIRMAR marca/modelo já
                # identificados. Uma única loja parecida não pode batizar o produto.
                if (
                    seed.get("brand")
                    and external_brand
                    and external_brand.casefold() == str(seed["brand"]).casefold()
                ):
                    add(
                        "brand",
                        external_brand,
                        min(0.94, base + 0.08),
                        source,
                    )

                if (
                    seed.get("model")
                    and external_model
                    and external_model.casefold() == str(seed["model"]).casefold()
                ):
                    add(
                        "model",
                        external_model,
                        min(0.94, base + 0.08),
                        source,
                    )

            add("category", product.get("category"), base, source)
            source_description = _first(
                product.get("description"),
                source.get("description"),
            )

            if source_description:
                identity_anchor = " ".join(
                    x for x in (
                        seed.get("brand"),
                        seed.get("model"),
                        seed.get("name"),
                    )
                    if x
                )
                description_match = _similarity(
                    identity_anchor,
                    source_description,
                )
                brand_in_description = bool(
                    seed.get("brand")
                    and str(seed.get("brand")).casefold()
                    in str(source_description).casefold()
                )
                model_in_description = bool(
                    seed.get("model")
                    and str(seed.get("model")).casefold()
                    in str(source_description).casefold()
                )

                # Não deixa uma meta description não relacionada da página
                # substituir os dados do produto identificado pelo link.
                if (
                    source.get("source_type") != "submitted_link"
                    or description_match >= 0.20
                    or brand_in_description
                    or model_in_description
                ):
                    add(
                        "description",
                        source_description,
                        base,
                        source,
                    )
            add(
                "image_url",
                _first(
                    product.get("image_url"),
                    source.get("image_url"),
                ),
                base,
                source,
            )

            reviews.extend(source.get("reviews") or [])

        values = {}
        confidence = {}
        field_sources = {}

        for field, items in candidates.items():
            best = max(items, key=lambda x: x["score"])
            values[field] = best["value"]
            confidence[field] = round(float(best["score"]), 2)

            deduped = []
            seen = set()
            for item in sorted(
                items,
                key=lambda x: x["score"],
                reverse=True,
            ):
                src = item["source"]
                url = src.get("url")
                if not url or url in seen:
                    continue
                seen.add(url)
                deduped.append(src)
                if len(deduped) >= 5:
                    break

            field_sources[field] = deduped

        derived = self._derive_structured_fields(
            sources,
            seed,
        )

        for field, payload in derived.items():
            if field in values:
                continue
            values[field] = payload["value"]
            confidence[field] = payload["confidence"]
            field_sources[field] = payload["sources"]

        return values, confidence, field_sources, reviews[:250]

    def _source_text_for_identity(
        self,
        source: dict,
        seed: dict,
    ) -> str:
        if not source.get("ok"):
            return ""

        product = source.get("product") or {}
        title = _clean(
            _first(
                product.get("name"),
                source.get("title"),
            )
        )
        description = _clean(
            _first(
                product.get("description"),
                source.get("description"),
            )
        )

        if source.get("source_type") == "submitted_link":
            # O título vindo de og_info é confiável para identidade.
            safe_parts = [title]
            anchor = " ".join(
                x for x in (
                    seed.get("brand"),
                    seed.get("model"),
                    seed.get("name"),
                )
                if x
            )
            if (
                description
                and (
                    _similarity(anchor, description) >= 0.20
                    or (
                        seed.get("brand")
                        and str(seed["brand"]).casefold()
                        in description.casefold()
                    )
                    or (
                        seed.get("model")
                        and str(seed["model"]).casefold()
                        in description.casefold()
                    )
                )
            ):
                safe_parts.append(description)
            return _clean(" ".join(x for x in safe_parts if x))

        return _clean(" ".join(x for x in (title, description) if x))

    def _derive_structured_fields(
        self,
        sources: list[dict],
        seed: dict,
    ) -> dict:
        evidence = []
        source_records = []

        for source in sources:
            text = self._source_text_for_identity(source, seed)
            if not text:
                continue
            evidence.append(text)
            source_records.append(self._public_source_record(source))

        # O próprio título identificado pelo link sempre entra como evidência.
        if seed.get("name"):
            evidence.insert(0, _clean(seed["name"]))

        combined = " ".join(evidence)
        if not combined:
            return {}

        low = combined.casefold()
        sentences = [
            _clean(x)
            for x in re.split(r"(?<=[.!?;])\s+|\s+[|•]\s+", combined)
            if 12 <= len(_clean(x)) <= 300
        ]

        def unique_sentences(keys, limit=4):
            out = []
            seen = set()
            for sentence in sentences:
                sl = sentence.casefold()
                if not any(k in sl for k in keys):
                    continue
                norm = re.sub(r"\W+", " ", sl).strip()
                if norm in seen:
                    continue
                seen.add(norm)
                out.append(sentence)
                if len(out) >= limit:
                    break
            return out

        derived = {}
        sources_out = source_records[:5]

        benefit_sentences = unique_sentences(
            (
                "ideal", "permite", "fácil", "facil", "prático", "pratico",
                "confort", "resistente", "rápid", "rapido", "performance",
                "cintura alta", "compress", "flex", "respir", "leve",
            ),
            limit=4,
        )
        if benefit_sentences:
            derived["key_benefits"] = {
                "value": "; ".join(benefit_sentences),
                "confidence": 0.62,
                "sources": sources_out,
            }

        included = unique_sentences(
            (
                "acompanha", "inclui", "vem com", "itens inclus",
                "conteúdo da embalagem", "conteudo da embalagem",
                "brinde", "kit contém", "kit contem",
            ),
            limit=4,
        )
        if included:
            derived["included_items"] = {
                "value": "; ".join(included),
                "confidence": 0.68,
                "sources": sources_out,
            }

        compatibility = unique_sentences(
            (
                "compatível", "compativel", "android", "iphone", "ios",
                "strava", "whatsapp", "bluetooth", "indução", "inducao",
            ),
            limit=4,
        )
        if compatibility:
            derived["compatibility"] = {
                "value": "; ".join(compatibility),
                "confidence": 0.66,
                "sources": sources_out,
            }

        battery = unique_sentences(
            (
                "bateria", "autonomia", "mah", "carregamento", "carga",
            ),
            limit=4,
        )
        if battery:
            derived["battery_info"] = {
                "value": "; ".join(battery),
                "confidence": 0.70,
                "sources": sources_out,
            }

        warranty = unique_sentences(
            ("garantia", "warranty"),
            limit=3,
        )
        if warranty:
            derived["warranty"] = {
                "value": "; ".join(warranty),
                "confidence": 0.72,
                "sources": sources_out,
            }

        usage = unique_sentences(
            (
                "como usar", "modo de uso", "ideal para", "indicado para",
                "treino", "esporte", "corrida", "academia", "monitoramento",
            ),
            limit=4,
        )
        if usage:
            derived["usage_info"] = {
                "value": "; ".join(usage),
                "confidence": 0.60,
                "sources": sources_out,
            }

        limitations = unique_sentences(
            (
                "não possui", "nao possui", "não compatível", "nao compativel",
                "não suporta", "nao suporta", "não acompanha", "nao acompanha",
            ),
            limit=3,
        )
        if limitations:
            derived["limitations"] = {
                "value": "; ".join(limitations),
                "confidence": 0.72,
                "sources": sources_out,
            }

        measurement_patterns = (
            r"\b\d+(?:[.,]\d+)?\s?(?:mah|atm|hz|cm|mm|ml|kg|g|w|v)\b",
            r"\b\d+(?:[.,]\d+)?\s?(?:polegadas|litros|l)\b",
        )
        measurement_sentences = []
        for sentence in sentences:
            sl = sentence.casefold()
            if any(re.search(p, sl, re.I) for p in measurement_patterns):
                measurement_sentences.append(sentence)
            if len(measurement_sentences) >= 5:
                break

        if measurement_sentences:
            derived["size_info"] = {
                "value": "; ".join(measurement_sentences),
                "confidence": 0.64,
                "sources": sources_out,
            }

        # Diferenciais: extrai apenas atributos explicitamente mencionados.
        feature_patterns = [
            (r"\bgps\s+interno\b", "GPS interno"),
            (r"\bstrava\b", "Integração com Strava"),
            (r"\bwhatsapp\b", "Recurso com WhatsApp"),
            (r"\b5\s?atm\b", "Resistência à água 5ATM"),
            (r"\bamoled\b", "Tela AMOLED"),
            (r"\b60\s?hz\b", "Tela 60 Hz"),
            (r"\b150\s+modos\b", "150 modos esportivos"),
            (r"\bchatgpt\b", "Recurso ChatGPT anunciado"),
            (r"\bcintura\s+alta\b", "Cintura alta"),
        ]
        features = []
        for pattern, label in feature_patterns:
            if re.search(pattern, low, re.I):
                features.append(label)

        if features:
            derived["differentials"] = {
                "value": "; ".join(dict.fromkeys(features)),
                "confidence": 0.74,
                "sources": sources_out,
            }

        # Só gera "problemas que resolve" quando a própria fonte usa linguagem
        # explícita de solução/dor; não inventa benefícios.
        problem_sentences = unique_sentences(
            (
                "ajuda a", "resolve", "evita", "reduz", "melhora",
                "para quem sofre", "para quem precisa",
            ),
            limit=3,
        )
        if problem_sentences:
            derived["problems_solved"] = {
                "value": "; ".join(problem_sentences),
                "confidence": 0.58,
                "sources": sources_out,
            }

        # Regras factuais para categorias comuns. Só usam termos que aparecem
        # explicitamente no título/fontes correspondentes.
        if "pote" in low and "vidro" in low:
            capacities = []
            for value, unit in re.findall(
                r"\b(\d+(?:[.,]\d+)?)\s*(ml|l)\b",
                low,
                flags=re.I,
            ):
                normalized = f"{value} {unit}".replace(".", ",")
                if normalized not in capacities:
                    capacities.append(normalized)

            qty_match = re.search(
                r"\b(?:kit\s+)?(?:até\s+)?(\d+)\s+potes?\b",
                low,
                flags=re.I,
            )

            included_bits = []
            if qty_match:
                included_bits.append(
                    f"kit anunciado com até {qty_match.group(1)} potes"
                )
            if "tampa" in low:
                included_bits.append("potes com tampa")
            if "trava" in low:
                included_bits.append("tampa com trava")

            if included_bits and "included_items" not in derived:
                derived["included_items"] = {
                    "value": "; ".join(included_bits),
                    "confidence": 0.76,
                    "sources": sources_out,
                }

            if capacities and "size_info" not in derived:
                derived["size_info"] = {
                    "value": "Capacidades anunciadas: " + ", ".join(capacities),
                    "confidence": 0.80,
                    "sources": sources_out,
                }

            explicit_benefits = []
            if "hermético" in low or "hermetico" in low:
                explicit_benefits.append("fechamento hermético anunciado")
            if "antivazamento" in low or "anti-vazamento" in low:
                explicit_benefits.append("característica antivazamento anunciada")
            if "trava" in low:
                explicit_benefits.append("tampa com trava")

            if explicit_benefits and "key_benefits" not in derived:
                derived["key_benefits"] = {
                    "value": "; ".join(explicit_benefits),
                    "confidence": 0.74,
                    "sources": sources_out,
                }

            use_cases = []
            for keyword, label in (
                ("marmita", "uso como marmita"),
                ("freezer", "armazenamento no freezer"),
                ("microondas", "uso em micro-ondas quando confirmado pela fonte"),
                ("micro-ondas", "uso em micro-ondas quando confirmado pela fonte"),
                ("airfryer", "uso em air fryer quando confirmado pela fonte"),
                ("mantimento", "armazenamento de alimentos"),
            ):
                if keyword in low and label not in use_cases:
                    use_cases.append(label)

            if use_cases and "usage_info" not in derived:
                derived["usage_info"] = {
                    "value": "; ".join(use_cases),
                    "confidence": 0.66,
                    "sources": sources_out,
                }

        return derived

    def _analyze_reviews(
        self,
        reviews: list[str],
        search_results: list[dict],
    ) -> dict:
        corpus = [
            _clean(x)
            for x in reviews
            if len(_clean(x)) >= 12
        ]

        # Snippets de páginas de avaliações são tratados como contexto público,
        # não como avaliações verificadas.
        snippet_context = [
            _clean(r.get("snippet"))
            for r in search_results
            if any(
                k in (r.get("query") or "").casefold()
                for k in ("avalia", "review")
            )
            and len(_clean(r.get("snippet"))) >= 20
        ]

        positives = []
        negatives = []

        for text in corpus:
            low = text.casefold()
            if any(word in low for word in POSITIVE_WORDS):
                positives.append(text)
            if any(word in low for word in NEGATIVE_WORDS):
                negatives.append(text)

        return {
            "positives": positives[:8],
            "negatives": negatives[:8],
            "recurring_questions": self._question_candidates(
                corpus + snippet_context
            )[:10],
            "context_snippets": snippet_context[:8],
        }

    def _extract_faq(
        self,
        search_results: list[dict],
        reviews: list[str],
    ) -> list[dict]:
        questions = self._question_candidates(
            reviews
            + [
                r.get("snippet", "")
                for r in search_results
            ]
        )

        return [
            {
                "question": question,
                "answer": "",
                "origin": "public_context",
            }
            for question in questions[:12]
        ]

    def _question_candidates(self, texts: list[str]) -> list[str]:
        found = []
        counts = Counter()

        for text in texts:
            clean = _clean(text)
            if not clean:
                continue

            pieces = re.split(r"(?<=[?])\s+|[•|]", clean)
            for piece in pieces:
                p = _clean(piece)
                low = p.casefold()

                looks_question = (
                    "?" in p
                    or low.startswith(
                        (
                            "como ", "qual ", "quanto ", "quantos ",
                            "tem ", "serve ", "funciona ", "pode ",
                            "vem ", "é compat", "e compat",
                        )
                    )
                )

                if looks_question and 8 <= len(p) <= 180:
                    normalized = re.sub(r"[^\wÀ-ÿ ]", "", low)
                    counts[normalized] += 1
                    found.append((normalized, p))

        unique = {}
        for normalized, original in found:
            unique.setdefault(normalized, original)

        ordered = sorted(
            unique,
            key=lambda key: counts[key],
            reverse=True,
        )
        return [unique[key] for key in ordered]

    def _public_source_record(self, source: dict) -> dict:
        host = source.get("host")
        root = _commerce_root(host or "")
        return {
            "url": source.get("final_url") or source.get("url"),
            "host": host,
            "marketplace": COMMERCE_LABELS.get(root) if root else None,
            "title": source.get("title"),
            "description": source.get("description"),
            "source_type": source.get("source_type"),
            "status_code": source.get("status_code"),
        }

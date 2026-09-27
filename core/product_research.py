from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from urllib.parse import quote_plus, urlparse

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
        seed = self._seed_from_source(direct)

        if hint:
            seed["name"] = _clean(hint)

        search_name = _first(
            seed.get("name"),
            self._title_hint_from_url(resolved_url),
        )

        sources = [direct]
        search_results = []

        if search_name:
            search_results = self._search_public_web(search_name)
            candidates = self._select_candidates(
                search_name,
                seed.get("brand") or "",
                search_results,
                limit=6,
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
            },
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
        }

        try:
            response = self.client.get(url)
            record["status_code"] = response.status_code
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
            attrs={"type": re.compile("ld\+json", re.I)},
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
            "current_price": product.get("price"),
        }

    def _clean_product_title(self, title: str) -> str:
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

    def _title_hint_from_url(self, url: str) -> str:
        path = urlparse(url).path
        chunks = [
            x for x in re.split(r"[/_-]+", path)
            if len(x) >= 3 and not x.isdigit()
        ]
        return _clean(" ".join(chunks[-8:]))[:140]

    def _search_public_web(self, query: str) -> list[dict]:
        searches = [
            f'"{query}" produto especificações',
            f'"{query}" avaliações review',
            f'"{query}" manual fabricante',
        ]

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

                    if not href.startswith("http"):
                        continue

                    host = _host(href)
                    if not host or any(
                        blocked in host
                        for blocked in BLOCKED_HOST_FRAGMENTS
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
        results: list[dict],
        limit: int,
    ) -> list[dict]:
        scored = []
        for result in results:
            haystack = (
                result.get("title", "")
                + " "
                + result.get("snippet", "")
            )
            score = _similarity(name, haystack)

            if brand and brand.casefold() in haystack.casefold():
                score += 0.25

            host = result.get("host", "")
            if any(k in host for k in (
                "amazon.", "mercadolivre.", "magazineluiza.",
                "shopee.", "kabum.", "carrefour.", "casasbahia.",
            )):
                score += 0.05

            if score >= 0.28:
                scored.append((score, result))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:limit]]

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
            add(field, value, direct_score, direct)

        for source in sources:
            if not source.get("ok"):
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
            add("brand", product.get("brand"), min(0.94, base + 0.08), source)
            add("model", product.get("model"), min(0.92, base + 0.06), source)
            add("category", product.get("category"), base, source)
            add(
                "description",
                _first(
                    product.get("description"),
                    source.get("description"),
                ),
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

            # Preço pesquisado é apenas rascunho; a LIVE pode ter outro valor.
            add(
                "current_price",
                product.get("price"),
                0.82 if source.get("source_type") == "submitted_link" else 0.55,
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

        # Esses campos são inferências de venda e não são fabricados a partir
        # de uma única descrição. Só montamos rascunhos quando há texto útil.
        descriptions = [
            _clean(
                _first(
                    (s.get("product") or {}).get("description"),
                    s.get("description"),
                )
            )
            for s in sources
            if s.get("ok")
        ]
        combined = " ".join(x for x in descriptions if x)

        if combined:
            sentences = [
                _clean(x)
                for x in re.split(r"(?<=[.!?])\s+", combined)
                if 25 <= len(_clean(x)) <= 240
            ]

            benefit_candidates = [
                s for s in sentences
                if any(
                    key in s.casefold()
                    for key in (
                        "ideal", "permite", "facil", "fácil", "prático",
                        "pratico", "confort", "econom", "resistente",
                        "rápid", "rapido", "benef", "ajuda", "melhor",
                    )
                )
            ]

            if benefit_candidates:
                values["key_benefits"] = "; ".join(
                    benefit_candidates[:4]
                )
                confidence["key_benefits"] = 0.58
                field_sources["key_benefits"] = [
                    self._public_source_record(s)
                    for s in sources
                    if s.get("ok") and s.get("description")
                ][:4]

        return values, confidence, field_sources, reviews[:250]

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
        return {
            "url": source.get("final_url") or source.get("url"),
            "host": source.get("host"),
            "title": source.get("title"),
            "description": source.get("description"),
            "source_type": source.get("source_type"),
            "status_code": source.get("status_code"),
        }

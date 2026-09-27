from __future__ import annotations

import json
import os
import re
from collections import defaultdict
from copy import deepcopy
from urllib.parse import parse_qs, unquote_plus, urlparse

import httpx
from bs4 import BeautifulSoup

try:
    from playwright.sync_api import sync_playwright
except Exception:  # pragma: no cover
    sync_playwright = None


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0 Safari/537.36"
)


def clean(value) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def first(*values):
    for value in values:
        if value not in (None, "", [], {}):
            return value
    return None


def safe_float(value):
    if value in (None, ""):
        return None
    if isinstance(value, dict):
        for key in (
            "sale_price_decimal",
            "price_decimal",
            "price",
            "amount",
            "min_price",
            "max_price",
            "value",
        ):
            found = safe_float(value.get(key))
            if found is not None:
                return found
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


def walk(value):
    if isinstance(value, dict):
        yield value
        for nested in value.values():
            yield from walk(nested)
    elif isinstance(value, list):
        for item in value:
            yield from walk(item)


class TikTokNativeProductExtractor:
    """Extrai o máximo possível da própria página pública do TikTok Shop.

    Estratégia:
    1. resolve o link curto e lê metadados presentes no próprio link;
    2. tenta SSR/HTML sem navegador;
    3. usa Chromium/Playwright para observar a página renderizada e respostas
       JSON feitas pelo próprio TikTok;
    4. normaliza produto, preço, variantes e atributos.

    Não tenta burlar login, CAPTCHA ou challenge. Quando a página entrega um
    challenge, registra a limitação e retorna apenas os dados realmente vistos.
    """

    def __init__(self):
        self.client = httpx.Client(
            follow_redirects=True,
            timeout=httpx.Timeout(15.0, connect=8.0),
            headers={
                "User-Agent": USER_AGENT,
                "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.7",
                "Accept": "text/html,application/xhtml+xml,application/json;q=0.8,*/*;q=0.5",
            },
        )

    def extract(self, url: str) -> dict:
        url = clean(url)
        if not url.startswith(("http://", "https://")):
            raise ValueError("Link TikTok inválido.")

        response = self.client.get(url)
        final_url = str(response.url)
        redirect_urls = [
            str(item.next_request.url)
            for item in response.history
            if getattr(item, "next_request", None) is not None
        ]

        metadata = {}
        for candidate in [url, *redirect_urls, final_url]:
            metadata.update(self._metadata_from_url(candidate))

        result = {
            "ok": False,
            "source": "tiktok_native",
            "submitted_url": url,
            "resolved_url": final_url,
            "product_id": metadata.get("product_id"),
            "group_id": metadata.get("group_id"),
            "title": metadata.get("name") or "",
            "description": "",
            "brand": "",
            "model": "",
            "category": "",
            "image_url": metadata.get("image_url") or "",
            "images": [],
            "current_price": None,
            "regular_price": None,
            "discount": None,
            "rating": None,
            "review_count": None,
            "sold_count": None,
            "stock": None,
            "seller": {},
            "skus": [],
            "sale_properties": [],
            "attributes": [],
            "shipping": {},
            "raw_sources": [],
            "notes": [],
        }

        if response.status_code < 400 and "html" in response.headers.get(
            "content-type",
            "",
        ):
            html_result = self._extract_from_html(
                response.text,
                final_url,
            )
            self._merge(result, html_result)
            result["raw_sources"].append("tiktok_html")

        browser_enabled = os.getenv(
            "AGCN_TIKTOK_BROWSER_ENABLED",
            "1",
        ).strip().casefold() in {"1", "true", "yes", "sim", "on"}

        needs_browser = (
            browser_enabled
            and self._needs_browser(result, response.text)
        )

        if needs_browser:
            browser_result = self._extract_with_browser(final_url)
            self._merge(result, browser_result)
            if browser_result.get("browser_used"):
                result["raw_sources"].append("tiktok_browser")

        result["images"] = list(dict.fromkeys(
            x for x in result.get("images", [])
            if isinstance(x, str) and x.startswith("http")
        ))[:20]

        if not result.get("image_url") and result["images"]:
            result["image_url"] = result["images"][0]

        result["ok"] = bool(
            result.get("title")
            or result.get("product_id")
            or result.get("description")
        )

        if not result.get("description"):
            result["notes"].append(
                "A descrição completa não foi exposta diretamente nesta tentativa."
            )

        if not result.get("attributes"):
            result["notes"].append(
                "O TikTok não expôs atributos técnicos estruturados nesta tentativa."
            )

        return result

    def _needs_browser(self, result: dict, html: str) -> bool:
        text = (html or "").casefold()
        challenge = any(
            marker in text
            for marker in (
                "security check",
                "verify you are human",
                "captcha",
                "access denied",
            )
        )

        return (
            challenge
            or not result.get("description")
            or not result.get("attributes")
            or not result.get("skus")
        )

    def _extract_with_browser(self, url: str) -> dict:
        if sync_playwright is None:
            return {
                "browser_used": False,
                "notes": [
                    "Playwright não está disponível neste ambiente."
                ],
            }

        network_json = []
        response_urls = []
        html = ""
        body_text = ""
        final_url = url
        title = ""

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=[
                        "--disable-dev-shm-usage",
                        "--no-sandbox",
                        "--disable-blink-features=AutomationControlled",
                    ],
                )
                context = browser.new_context(
                    locale="pt-BR",
                    timezone_id="America/Sao_Paulo",
                    user_agent=USER_AGENT,
                    viewport={"width": 390, "height": 844},
                    is_mobile=True,
                    has_touch=True,
                )
                page = context.new_page()

                def on_response(resp):
                    try:
                        ctype = (
                            resp.headers.get("content-type")
                            or ""
                        ).casefold()
                        lower_url = resp.url.casefold()

                        interesting = any(
                            token in lower_url
                            for token in (
                                "product",
                                "pdp",
                                "oec",
                                "sku",
                                "review",
                                "shop",
                            )
                        )

                        if "json" in ctype and interesting:
                            data = resp.json()
                            network_json.append(data)
                            response_urls.append(resp.url)
                    except Exception:
                        return

                page.on("response", on_response)

                page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=35000,
                )
                page.wait_for_timeout(2500)

                # TikTok Shop carrega descrição, atributos e avaliações de
                # forma preguiçosa conforme a página rola. Percorremos a
                # página antes de capturar o DOM/rede.
                try:
                    for _ in range(8):
                        page.mouse.wheel(0, 950)
                        page.wait_for_timeout(450)
                except Exception:
                    pass

                # Abre blocos colapsáveis quando existirem.
                for label in (
                    "Sobre este produto",
                    "Descrição do produto",
                    "Avaliações dos clientes",
                    "Especificações",
                    "Detalhes do produto",
                ):
                    try:
                        locator = page.get_by_text(label, exact=False).first
                        if locator.count() and locator.is_visible():
                            locator.click(timeout=1200)
                            page.wait_for_timeout(500)
                    except Exception:
                        pass

                try:
                    for _ in range(4):
                        page.mouse.wheel(0, 1100)
                        page.wait_for_timeout(450)
                except Exception:
                    pass

                final_url = page.url
                title = clean(page.title())

                try:
                    body_text = page.locator("body").inner_text(timeout=5000)
                except Exception:
                    body_text = ""

                html = page.content()

                # Scripts JSON renderizados no DOM.
                scripts = page.locator("script")
                count = min(scripts.count(), 160)
                for index in range(count):
                    try:
                        script = scripts.nth(index)
                        stype = clean(script.get_attribute("type")).casefold()
                        sid = clean(script.get_attribute("id")).casefold()

                        if not (
                            "json" in stype
                            or "universal" in sid
                            or "sigi" in sid
                            or "next_data" in sid
                        ):
                            continue

                        raw = script.text_content() or ""
                        if len(raw) < 20:
                            continue
                        data = json.loads(raw)
                        network_json.append(data)
                    except Exception:
                        continue

                context.close()
                browser.close()

        except Exception:
            return {
                "browser_used": False,
                "notes": [
                    "Navegador renderizado do TikTok não ficou disponível nesta tentativa."
                ],
            }

        result = self._extract_from_html(html, final_url)
        from_json = self._extract_from_json_documents(network_json)
        self._merge(result, from_json)

        if not result.get("title"):
            result["title"] = self._clean_page_title(title)

        if body_text:
            visible = self._extract_from_visible_text(body_text)
            self._merge(result, visible)

            if not result.get("description"):
                result["description"] = self._description_from_visible_text(
                    body_text,
                    result.get("title") or "",
                )

        result["browser_used"] = True
        result["network_response_count"] = len(response_urls)
        result["network_urls"] = response_urls[:30]
        return result

    def _extract_from_html(self, html: str, url: str) -> dict:
        soup = BeautifulSoup(html or "", "html.parser")
        result = {
            "title": "",
            "description": "",
            "brand": "",
            "model": "",
            "category": "",
            "image_url": "",
            "images": [],
            "current_price": None,
            "regular_price": None,
            "discount": None,
            "rating": None,
            "review_count": None,
            "sold_count": None,
            "stock": None,
            "seller": {},
            "skus": [],
            "sale_properties": [],
            "attributes": [],
            "shipping": {},
            "notes": [],
        }

        def meta(selector, attr="content"):
            tag = soup.select_one(selector)
            if not tag:
                return ""
            return clean(tag.get(attr))

        result["title"] = self._clean_page_title(
            first(
                meta('meta[property="og:title"]'),
                meta('meta[name="twitter:title"]'),
                soup.title.string if soup.title else "",
            )
        )
        result["description"] = clean(first(
            meta('meta[property="og:description"]'),
            meta('meta[name="description"]'),
            meta('meta[name="twitter:description"]'),
        ))
        result["image_url"] = clean(first(
            meta('meta[property="og:image"]'),
            meta('meta[name="twitter:image"]'),
        ))

        if result["image_url"]:
            result["images"].append(result["image_url"])

        json_docs = []

        for script in soup.find_all("script"):
            raw = script.string or script.get_text() or ""
            if len(raw) < 20:
                continue

            stype = clean(script.get("type")).casefold()
            sid = clean(script.get("id")).casefold()

            if not (
                "json" in stype
                or "universal" in sid
                or "sigi" in sid
                or "next_data" in sid
                or "rehydration" in raw[:500].casefold()
            ):
                continue

            try:
                json_docs.append(json.loads(raw))
            except Exception:
                continue

        parsed = self._extract_from_json_documents(json_docs)
        self._merge(result, parsed)
        return result

    def _extract_from_json_documents(self, docs: list) -> dict:
        result = {
            "title": "",
            "description": "",
            "brand": "",
            "model": "",
            "category": "",
            "image_url": "",
            "images": [],
            "current_price": None,
            "regular_price": None,
            "discount": None,
            "rating": None,
            "review_count": None,
            "sold_count": None,
            "stock": None,
            "seller": {},
            "skus": [],
            "sale_properties": [],
            "attributes": [],
            "shipping": {},
            "notes": [],
        }

        product_candidates = []
        attribute_candidates = []
        sku_candidates = []
        sale_property_candidates = []
        category_candidates = []
        seller_candidates = []
        price_candidates = []
        sold_candidates = []
        review_candidates = []
        image_candidates = []

        for doc in docs:
            for node in walk(doc):
                keys = {str(k).casefold() for k in node.keys()}

                if (
                    "product_model" in keys
                    and isinstance(node.get("product_model"), dict)
                ):
                    product_candidates.append(node["product_model"])

                if any(k in keys for k in (
                    "product_id",
                    "productid",
                )) and any(k in keys for k in (
                    "title",
                    "product_name",
                    "productname",
                    "description",
                )):
                    product_candidates.append(node)

                for key in (
                    "product_attributes",
                    "attributes",
                    "attribute_list",
                ):
                    value = node.get(key)
                    if isinstance(value, list):
                        attribute_candidates.extend(value)

                for key in ("skus", "sku_list", "sku_models"):
                    value = node.get(key)
                    if isinstance(value, list):
                        sku_candidates.extend(value)

                for key in (
                    "sale_properties",
                    "sale_property_list",
                ):
                    value = node.get(key)
                    if isinstance(value, list):
                        sale_property_candidates.extend(value)

                for key in ("categories", "category_path"):
                    value = node.get(key)
                    if isinstance(value, list):
                        category_candidates.extend(value)

                if isinstance(node.get("seller_model"), dict):
                    seller_candidates.append(node["seller_model"])

                if any(k in keys for k in (
                    "promotion_product_price",
                    "product_price_info",
                    "price_info",
                )):
                    price_candidates.append(node)

                if isinstance(node.get("sold_info"), dict):
                    sold_candidates.append(node["sold_info"])

                if any(k in keys for k in (
                    "review_count",
                    "rating_count",
                    "rating_value",
                )):
                    review_candidates.append(node)

                for key in (
                    "images",
                    "main_images",
                    "image_list",
                    "product_images",
                ):
                    value = node.get(key)
                    if isinstance(value, list):
                        image_candidates.extend(value)

        best_product = self._best_product_candidate(product_candidates)

        if best_product:
            result["title"] = clean(first(
                best_product.get("title"),
                best_product.get("product_name"),
                best_product.get("productName"),
                best_product.get("name"),
            ))
            result["description"] = self._plain_description(first(
                best_product.get("description"),
                best_product.get("product_description"),
                best_product.get("productDescription"),
            ))
            result["brand"] = self._brand_from_value(first(
                best_product.get("brand"),
                best_product.get("brand_name"),
                best_product.get("brandName"),
            ))
            result["model"] = clean(first(
                best_product.get("model"),
                best_product.get("model_name"),
                best_product.get("sku_name"),
            ))
            result["category"] = self._category_from_value(first(
                best_product.get("category"),
                best_product.get("category_name"),
                best_product.get("categoryName"),
            ))

            for key in ("images", "main_images", "image_list"):
                value = best_product.get(key)
                if isinstance(value, list):
                    image_candidates.extend(value)

        result["attributes"] = self._normalize_attributes(
            attribute_candidates
        )
        result["skus"] = self._normalize_skus(sku_candidates)
        result["sale_properties"] = self._normalize_sale_properties(
            sale_property_candidates
        )

        if not result["category"] and category_candidates:
            names = [
                self._category_from_value(x)
                for x in category_candidates
            ]
            names = [x for x in names if x]
            if names:
                result["category"] = " > ".join(
                    dict.fromkeys(names)
                )

        if seller_candidates:
            seller = seller_candidates[0]
            result["seller"] = {
                "id": clean(first(
                    seller.get("seller_id"),
                    seller.get("shop_id"),
                    seller.get("id"),
                )),
                "name": clean(first(
                    seller.get("seller_name"),
                    seller.get("shop_name"),
                    seller.get("name"),
                )),
            }

        prices = self._extract_prices(price_candidates, result["skus"])
        result.update(prices)

        if sold_candidates:
            sold = sold_candidates[0]
            result["sold_count"] = first(
                sold.get("sold_count"),
                sold.get("count"),
                sold.get("value"),
            )

        if review_candidates:
            for node in review_candidates:
                result["review_count"] = first(
                    result["review_count"],
                    node.get("review_count"),
                    node.get("rating_count"),
                )
                result["rating"] = first(
                    result["rating"],
                    node.get("rating_value"),
                    node.get("rating"),
                    node.get("score"),
                )

        normalized_images = []
        for item in image_candidates:
            image = self._image_from_value(item)
            if image:
                normalized_images.append(image)

        result["images"] = list(dict.fromkeys(normalized_images))[:20]
        if result["images"]:
            result["image_url"] = result["images"][0]

        if result["skus"]:
            stocks = [
                x.get("stock")
                for x in result["skus"]
                if isinstance(x.get("stock"), (int, float))
            ]
            if stocks:
                result["stock"] = sum(stocks)

        return result

    def _best_product_candidate(self, candidates: list[dict]) -> dict:
        if not candidates:
            return {}

        def score(node):
            points = 0
            for key in (
                "title", "product_name", "name",
                "description", "product_description",
                "brand", "brand_name",
                "product_id",
            ):
                if node.get(key) not in (None, "", [], {}):
                    points += 1
            return points

        return max(candidates, key=score)

    def _normalize_attributes(self, items: list) -> list[dict]:
        output = []
        seen = set()

        for item in items:
            if not isinstance(item, dict):
                continue

            name = clean(first(
                item.get("name"),
                item.get("attribute_name"),
                item.get("attributeName"),
                item.get("label"),
            ))

            raw_values = first(
                item.get("values"),
                item.get("value"),
                item.get("attribute_values"),
                item.get("attributeValues"),
            )

            values = []
            if isinstance(raw_values, list):
                for value in raw_values:
                    if isinstance(value, dict):
                        text = clean(first(
                            value.get("name"),
                            value.get("value"),
                            value.get("display_value"),
                        ))
                    else:
                        text = clean(value)
                    if text:
                        values.append(text)
            elif isinstance(raw_values, dict):
                text = clean(first(
                    raw_values.get("name"),
                    raw_values.get("value"),
                ))
                if text:
                    values.append(text)
            else:
                text = clean(raw_values)
                if text:
                    values.append(text)

            if not name or not values:
                continue

            key = (
                name.casefold(),
                tuple(x.casefold() for x in values),
            )
            if key in seen:
                continue
            seen.add(key)

            output.append({
                "name": name,
                "value": ", ".join(dict.fromkeys(values)),
            })

        return output[:80]

    def _normalize_skus(self, items: list) -> list[dict]:
        output = []
        seen = set()

        for item in items:
            if not isinstance(item, dict):
                continue

            sku_id = clean(first(
                item.get("sku_id"),
                item.get("id"),
                item.get("skuId"),
            ))
            if sku_id and sku_id in seen:
                continue
            if sku_id:
                seen.add(sku_id)

            props = first(
                item.get("sale_props"),
                item.get("sale_properties"),
                item.get("properties"),
            )
            prop_text = []

            if isinstance(props, list):
                for prop in props:
                    if isinstance(prop, dict):
                        pname = clean(first(
                            prop.get("prop_name"),
                            prop.get("name"),
                        ))
                        pvalue = clean(first(
                            prop.get("prop_value"),
                            prop.get("value_name"),
                            prop.get("value"),
                        ))
                        if pname or pvalue:
                            prop_text.append(
                                ": ".join(
                                    x for x in (pname, pvalue) if x
                                )
                            )

            stock = first(
                item.get("available_quantity"),
                item.get("stock"),
                item.get("availableQuantity"),
            )

            try:
                stock = int(stock) if stock is not None else None
            except Exception:
                stock = None

            price = safe_float(first(
                item.get("sale_price"),
                item.get("price"),
                item.get("salePrice"),
                item.get("product_price_info"),
            ))

            original = safe_float(first(
                item.get("original_price"),
                item.get("originalPrice"),
                item.get("list_price"),
            ))

            output.append({
                "id": sku_id or None,
                "variation": " / ".join(prop_text),
                "price": price,
                "original_price": original,
                "stock": stock,
            })

        return output[:120]

    def _normalize_sale_properties(self, items: list) -> list[dict]:
        output = []

        for item in items:
            if not isinstance(item, dict):
                continue

            name = clean(first(
                item.get("name"),
                item.get("prop_name"),
                item.get("property_name"),
            ))
            values_raw = first(
                item.get("values"),
                item.get("value_list"),
            )
            values = []

            if isinstance(values_raw, list):
                for value in values_raw:
                    if isinstance(value, dict):
                        text = clean(first(
                            value.get("name"),
                            value.get("value"),
                            value.get("prop_value"),
                        ))
                    else:
                        text = clean(value)
                    if text:
                        values.append(text)

            if name and values:
                output.append({
                    "name": name,
                    "values": list(dict.fromkeys(values)),
                })

        return output[:30]

    def _extract_prices(
        self,
        price_nodes: list[dict],
        skus: list[dict],
    ) -> dict:
        current = None
        regular = None
        discount = None

        for node in price_nodes:
            for key in (
                "promotion_product_price",
                "product_price_info",
                "price_info",
            ):
                price_obj = node.get(key)
                if not isinstance(price_obj, dict):
                    continue

                current = first(
                    current,
                    safe_float(price_obj.get("sale_price_decimal")),
                    safe_float(price_obj.get("sale_price")),
                    safe_float(price_obj.get("price")),
                    safe_float(price_obj.get("min_price")),
                )
                regular = first(
                    regular,
                    safe_float(price_obj.get("original_price")),
                    safe_float(price_obj.get("originalPrice")),
                    safe_float(price_obj.get("list_price")),
                )
                discount = first(
                    discount,
                    price_obj.get("discount"),
                    price_obj.get("discount_percent"),
                )

        if current is None:
            sku_prices = [
                x.get("price")
                for x in skus
                if isinstance(x.get("price"), (int, float))
            ]
            if sku_prices:
                current = min(sku_prices)

        if regular is None:
            sku_regular = [
                x.get("original_price")
                for x in skus
                if isinstance(x.get("original_price"), (int, float))
            ]
            if sku_regular:
                regular = min(sku_regular)

        return {
            "current_price": current,
            "regular_price": regular,
            "discount": discount,
        }

    def _extract_from_visible_text(self, text: str) -> dict:
        result = {
            "title": "",
            "description": "",
            "brand": "",
            "model": "",
            "category": "",
            "image_url": "",
            "images": [],
            "current_price": None,
            "regular_price": None,
            "discount": None,
            "rating": None,
            "review_count": None,
            "sold_count": None,
            "stock": None,
            "seller": {},
            "skus": [],
            "sale_properties": [],
            "attributes": [],
            "shipping": {},
            "benefits": "",
            "care_instructions": "",
            "notes": [],
        }

        raw = str(text or "")
        lines = [clean(x) for x in raw.splitlines() if clean(x)]
        joined = "\n".join(lines)

        # Preço e reputação exibidos no PDP.
        prices = re.findall(r"R\$\s*([0-9.]+,[0-9]{2})", joined)
        parsed_prices = [safe_float(x) for x in prices]
        parsed_prices = [x for x in parsed_prices if x is not None]
        if parsed_prices:
            result["current_price"] = min(parsed_prices)
            result["regular_price"] = max(parsed_prices) if len(parsed_prices) > 1 else None

        rating_match = re.search(
            r"\b([1-5](?:[.,]\d)?)\s*[★☆]",
            joined,
        )
        if rating_match:
            result["rating"] = safe_float(rating_match.group(1))

        review_match = re.search(
            r"(\d[\d.]*)\s+avalia(?:ç|c)ões",
            joined,
            flags=re.I,
        )
        if review_match:
            try:
                result["review_count"] = int(
                    review_match.group(1).replace(".", "")
                )
            except Exception:
                pass

        sold_match = re.search(
            r"([0-9.,]+\s*[KkMm]?)\s+vendido",
            joined,
            flags=re.I,
        )
        if sold_match:
            result["sold_count"] = clean(sold_match.group(1))

        seller_match = re.search(
            r"(?:Sold by|Vendido por)\s+([^\n]+)",
            joined,
            flags=re.I,
        )
        if seller_match:
            result["seller"] = {"name": clean(seller_match.group(1))}

        # Bloco "Descrição do produto" que aparece no próprio TikTok Shop.
        description_start = None
        for idx, line in enumerate(lines):
            if "descrição do produto" in line.casefold():
                description_start = idx + 1
                break

        if description_start is not None:
            desc_lines = []
            for line in lines[description_start:]:
                low = line.casefold()
                if any(
                    stop in low
                    for stop in (
                        "instruções de cuidado",
                        "informações sobre nossa forma",
                        "avaliações dos clientes",
                        "comprar agora",
                    )
                ):
                    break
                desc_lines.append(line)

            full_desc = "\n".join(desc_lines).strip()
            if full_desc:
                result["description"] = full_desc[:5000]

            benefit_index = next(
                (
                    i for i, line in enumerate(desc_lines)
                    if line.casefold().rstrip(":") == "benefícios"
                ),
                None,
            )
            spec_index = next(
                (
                    i for i, line in enumerate(desc_lines)
                    if "especificações técnicas" in line.casefold()
                ),
                None,
            )

            if benefit_index is not None:
                end = spec_index if spec_index is not None else len(desc_lines)
                benefits = [
                    x for x in desc_lines[benefit_index + 1:end]
                    if not x.startswith("-")
                ]
                result["benefits"] = " ".join(benefits).strip()[:1800]

        # Especificações em formato "- Marca: Arno", "- Voltagem: ...".
        attrs = []
        for line in lines:
            normalized = line.lstrip("-•> ").strip()
            match = re.match(
                r"([^:]{2,60}):\s*(.+)$",
                normalized,
            )
            if not match:
                continue

            label = clean(match.group(1))
            value = clean(match.group(2))
            low = label.casefold()

            if any(
                key in low
                for key in (
                    "marca", "modelo", "cor", "voltagem", "tensão",
                    "tensao", "potência", "potencia", "capacidade",
                    "material", "tomada", "tipo de pino", "frequência",
                    "frequencia", "temperatura", "dimens", "peso",
                    "garantia",
                )
            ):
                attrs.append({"name": label, "value": value})

                if low == "marca" and not result["brand"]:
                    result["brand"] = value
                elif low == "modelo" and not result["model"]:
                    result["model"] = value

        result["attributes"] = attrs[:80]

        # Cuidados/uso.
        care_start = None
        for idx, line in enumerate(lines):
            if "instruções de cuidado" in line.casefold():
                care_start = idx + 1
                break

        if care_start is not None:
            care = []
            for line in lines[care_start:]:
                low = line.casefold()
                if any(
                    stop in low
                    for stop in (
                        "informações sobre nossa forma",
                        "avaliações dos clientes",
                        "comprar agora",
                    )
                ):
                    break
                care.append(line.lstrip("> ").strip())
            result["care_instructions"] = " ".join(care).strip()[:1800]

        return result

    def _description_from_visible_text(
        self,
        text: str,
        title: str,
    ) -> str:
        if not text:
            return ""

        low = text.casefold()
        if any(
            marker in low
            for marker in (
                "security check",
                "verify you are human",
                "captcha",
            )
        ):
            return ""

        # Mantém apenas uma janela útil próxima ao título quando possível.
        if title:
            idx = low.find(title.casefold()[:40])
            if idx >= 0:
                text = text[idx: idx + 5000]

        # Evita usar toda a interface como descrição.
        pieces = [
            clean(x)
            for x in re.split(r"[\n\r]+", text)
            if 30 <= len(clean(x)) <= 700
        ]

        return " ".join(pieces[:4])[:2400]

    def _plain_description(self, value) -> str:
        if value in (None, ""):
            return ""
        if isinstance(value, str):
            soup = BeautifulSoup(value, "html.parser")
            return clean(soup.get_text(" ", strip=True))
        if isinstance(value, list):
            parts = []
            for item in value:
                if isinstance(item, dict):
                    text = first(
                        item.get("text"),
                        item.get("content"),
                        item.get("value"),
                    )
                else:
                    text = item
                text = clean(text)
                if text:
                    parts.append(text)
            return clean(" ".join(parts))
        if isinstance(value, dict):
            return clean(first(
                value.get("text"),
                value.get("content"),
                value.get("value"),
            ))
        return clean(value)

    def _brand_from_value(self, value) -> str:
        if isinstance(value, dict):
            return clean(first(
                value.get("name"),
                value.get("brand_name"),
                value.get("value"),
            ))
        return clean(value)

    def _category_from_value(self, value) -> str:
        if isinstance(value, dict):
            return clean(first(
                value.get("name"),
                value.get("category_name"),
                value.get("value"),
            ))
        return clean(value)

    def _image_from_value(self, value) -> str:
        if isinstance(value, str):
            return value if value.startswith("http") else ""

        if isinstance(value, dict):
            for key in (
                "url",
                "image_url",
                "imageUrl",
                "url_list",
                "urlList",
            ):
                nested = value.get(key)
                if isinstance(nested, str) and nested.startswith("http"):
                    return nested
                if isinstance(nested, list):
                    for item in nested:
                        image = self._image_from_value(item)
                        if image:
                            return image

        return ""

    def _metadata_from_url(self, url: str) -> dict:
        if not url:
            return {}

        parsed = urlparse(url)
        query = parse_qs(parsed.query, keep_blank_values=True)

        def decode_json(key):
            values = query.get(key)
            if not values:
                return {}
            raw = values[0]
            for _ in range(5):
                try:
                    data = json.loads(raw)
                    return data if isinstance(data, dict) else {}
                except Exception:
                    pass
                new_raw = unquote_plus(raw)
                if new_raw == raw:
                    break
                raw = new_raw
            return {}

        og = decode_json("og_info")
        share = decode_json("ec_search_share_params")

        match = re.search(r"/pdp/(?:[^/]+/)?(\d{15,22})", parsed.path)

        product_id = first(
            share.get("product_id"),
            match.group(1) if match else None,
        )

        return {
            "name": clean(og.get("title")),
            "image_url": clean(og.get("image")),
            "product_id": clean(product_id),
            "group_id": clean(share.get("group_id")),
        }

    def _clean_page_title(self, value: str) -> str:
        title = clean(value)
        low = title.casefold()

        if any(
            marker in low
            for marker in (
                "security check",
                "verify you are human",
                "captcha",
                "access denied",
                "tiktok - make your day",
            )
        ):
            return ""

        title = re.sub(
            r"\s*[|·-]\s*(TikTok Shop|TikTok).*?$",
            "",
            title,
            flags=re.I,
        )
        return clean(title)

    def _merge(self, target: dict, source: dict) -> None:
        if not source:
            return

        scalar_fields = (
            "product_id",
            "group_id",
            "title",
            "description",
            "brand",
            "model",
            "category",
            "image_url",
            "current_price",
            "regular_price",
            "discount",
            "rating",
            "review_count",
            "sold_count",
            "stock",
            "benefits",
            "care_instructions",
        )

        for field in scalar_fields:
            if target.get(field) in (None, "", [], {}) and source.get(field) not in (
                None,
                "",
                [],
                {},
            ):
                target[field] = deepcopy(source[field])

        for field in (
            "images",
            "skus",
            "sale_properties",
            "attributes",
            "raw_sources",
            "notes",
        ):
            if source.get(field):
                current = target.setdefault(field, [])
                for item in source[field]:
                    if item not in current:
                        current.append(deepcopy(item))

        for field in ("seller", "shipping"):
            if not target.get(field) and source.get(field):
                target[field] = deepcopy(source[field])

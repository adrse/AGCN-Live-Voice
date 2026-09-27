from __future__ import annotations

import io
import os
import re
import tempfile
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse

import httpx

try:
    from PIL import Image
    import imagehash
except Exception:  # pragma: no cover
    Image = None
    imagehash = None

try:
    from playwright.sync_api import sync_playwright
except Exception:  # pragma: no cover
    sync_playwright = None


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0 Safari/537.36"
)

MARKETPLACE_ROOTS = {
    "mercadolivre.com.br",
    "amazon.com.br",
    "magazineluiza.com.br",
    "casasbahia.com.br",
    "carrefour.com.br",
    "ponto.com.br",
    "extra.com.br",
    "kabum.com.br",
    "americanas.com.br",
    "shopee.com.br",
    "aliexpress.com",
}

BLOCKED_ROOTS = {
    "google.com",
    "google.com.br",
    "gstatic.com",
    "youtube.com",
    "facebook.com",
    "instagram.com",
    "pinterest.com",
    "tiktok.com",
}


def _clean(value) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _host(url: str) -> str:
    try:
        return urlparse(url).netloc.casefold().removeprefix("www.")
    except Exception:
        return ""


def _root_matches(host: str, roots: set[str]) -> bool:
    host = (host or "").casefold().removeprefix("www.")
    return any(
        host == root or host.endswith("." + root)
        for root in roots
    )


class VisualImageMatcher:
    """Comparação local de imagens.

    pHash/dHash são muito bons para reconhecer a mesma foto redimensionada,
    recomprimida ou com pequenas alterações. O Google Lens faz a descoberta
    visual mais ampla; este comparador serve como evidência adicional.
    """

    def __init__(self):
        self.client = httpx.Client(
            timeout=httpx.Timeout(12.0, connect=8.0),
            follow_redirects=True,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
            },
        )

    def compare_urls(
        self,
        source_url: str,
        candidate_url: str,
    ) -> dict:
        if not source_url or not candidate_url:
            return {
                "ok": False,
                "score": None,
                "reason": "imagem ausente",
            }

        if Image is None or imagehash is None:
            return {
                "ok": False,
                "score": None,
                "reason": "Pillow/ImageHash indisponível",
            }

        try:
            source = self._download_image(source_url)
            candidate = self._download_image(candidate_url)

            if source is None or candidate is None:
                return {
                    "ok": False,
                    "score": None,
                    "reason": "não foi possível baixar uma das imagens",
                }

            source_phash = imagehash.phash(source)
            candidate_phash = imagehash.phash(candidate)
            source_dhash = imagehash.dhash(source)
            candidate_dhash = imagehash.dhash(candidate)

            hash_bits = len(source_phash.hash) ** 2
            phash_score = 1.0 - (
                (source_phash - candidate_phash)
                / max(1, hash_bits)
            )

            dhash_bits = len(source_dhash.hash) ** 2
            dhash_score = 1.0 - (
                (source_dhash - candidate_dhash)
                / max(1, dhash_bits)
            )

            score = max(
                0.0,
                min(
                    1.0,
                    (phash_score * 0.72)
                    + (dhash_score * 0.28),
                ),
            )

            return {
                "ok": True,
                "score": round(score, 4),
                "phash_score": round(phash_score, 4),
                "dhash_score": round(dhash_score, 4),
                "same_catalog_photo": score >= 0.88,
            }
        except Exception as exc:
            return {
                "ok": False,
                "score": None,
                "reason": _clean(str(exc))[:160],
            }

    def _download_image(self, url: str):
        response = self.client.get(url)
        if response.status_code >= 400:
            return None

        content_type = (
            response.headers.get("content-type") or ""
        ).casefold()

        if "image" not in content_type:
            return None

        image = Image.open(io.BytesIO(response.content))
        image.load()
        return image.convert("RGB")


class GoogleLensDiscovery:
    """Descoberta visual usando a interface web oficial do Google Lens.

    O módulo roda no próprio computador do usuário. Não depende de backend
    AGCN. Ele abre o Google, envia uma cópia temporária da imagem do produto,
    adiciona o título como refinamento quando o campo estiver disponível e
    coleta links externos exibidos nos resultados.

    Não usa endpoint privado do Lens e não tenta contornar CAPTCHA/login.
    """

    def __init__(
        self,
        *,
        headless: bool = True,
        timeout_ms: int = 35000,
    ):
        self.headless = headless
        self.timeout_ms = timeout_ms
        self.client = httpx.Client(
            timeout=httpx.Timeout(15.0, connect=8.0),
            follow_redirects=True,
            headers={
                "User-Agent": USER_AGENT,
                "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.5",
            },
        )

    @staticmethod
    def available() -> bool:
        return sync_playwright is not None

    def search(
        self,
        *,
        image_url: str,
        title_hint: str = "",
        max_results: int = 30,
    ) -> dict:
        if not image_url:
            return {
                "ok": False,
                "results": [],
                "reason": "imagem do produto ausente",
            }

        if sync_playwright is None:
            return {
                "ok": False,
                "results": [],
                "reason": "Playwright não está disponível",
            }

        # Quando já temos uma imagem pública do TikTok, tentamos primeiro o
        # fluxo direto do Lens por URL. Isso evita depender do seletor de
        # upload e funciona tanto no protótipo web quanto no Windows local.
        direct = self._search_public_image_url(
            image_url,
            title_hint=title_hint,
            max_results=max_results,
        )
        if direct.get("ok"):
            return direct

        # Fallback: baixa uma cópia temporária e usa o upload visual normal.
        temp_path = self._download_temp_image(image_url)
        if not temp_path:
            return {
                "ok": False,
                "results": [],
                "reason": direct.get("reason")
                or "não foi possível baixar a imagem do TikTok",
            }

        try:
            fallback = self._search_file(
                temp_path,
                title_hint=title_hint,
                max_results=max_results,
            )
            if not fallback.get("ok") and direct.get("reason"):
                fallback["reason"] = (
                    str(direct.get("reason"))
                    + " | fallback: "
                    + str(fallback.get("reason") or "sem resultado")
                )
            return fallback
        finally:
            try:
                Path(temp_path).unlink(missing_ok=True)
            except Exception:
                pass

    def _search_public_image_url(
        self,
        image_url: str,
        *,
        title_hint: str,
        max_results: int,
    ) -> dict:
        results = []
        final_url = ""

        try:
            lens_url = (
                "https://lens.google.com/uploadbyurl?hl=pt-BR&url="
                + quote(image_url, safe="")
            )

            # Primeiro resolvemos o redirecionamento do Lens. Quando o Google
            # devolve uma URL de resultados com vsrid, abrimos diretamente
            # essa página no navegador.
            resolved_url = lens_url
            try:
                probe = self.client.get(lens_url)
                if str(probe.url).startswith("http"):
                    resolved_url = str(probe.url)
            except Exception:
                pass

            with sync_playwright() as p:
                browser = self._launch_browser(p)
                context = browser.new_context(
                    locale="pt-BR",
                    timezone_id="America/Sao_Paulo",
                    user_agent=USER_AGENT,
                    viewport={"width": 1440, "height": 960},
                )
                page = context.new_page()
                page.goto(
                    resolved_url,
                    wait_until="domcontentloaded",
                    timeout=self.timeout_ms,
                )
                self._accept_consent(page)
                page.wait_for_timeout(3500)

                if title_hint:
                    self._add_text_hint(page, title_hint)

                page.wait_for_timeout(2500)
                final_url = page.url

                raw_links = page.locator("a").evaluate_all(
                    """els => els.map((a, i) => ({
                        href: a.href || "",
                        text: (a.innerText || a.textContent || "").trim(),
                        aria: a.getAttribute("aria-label") || "",
                        index: i
                    }))"""
                )

                seen = set()
                for item in raw_links:
                    href = self._decode_google_href(
                        item.get("href") or ""
                    )
                    if not href.startswith(("http://", "https://")):
                        continue

                    h = _host(href)
                    if not h or _root_matches(h, BLOCKED_ROOTS):
                        continue

                    key = href.split("#")[0]
                    if key in seen:
                        continue
                    seen.add(key)

                    results.append({
                        "url": key,
                        "host": h,
                        "title": _clean(
                            item.get("text")
                            or item.get("aria")
                        )[:240],
                        "rank": len(results) + 1,
                        "is_marketplace": _root_matches(
                            h,
                            MARKETPLACE_ROOTS,
                        ),
                        "source": "google_lens",
                    })

                    if len(results) >= max_results:
                        break

                context.close()
                browser.close()

        except Exception as exc:
            return {
                "ok": False,
                "results": [],
                "reason": _clean(str(exc))[:220],
                "final_url": final_url,
                "mode": "uploadbyurl",
            }

        return {
            "ok": bool(results),
            "results": results,
            "marketplace_count": sum(
                1
                for item in results
                if item.get("is_marketplace")
            ),
            "final_url": final_url,
            "notes": (
                []
                if results
                else ["Lens por URL abriu, mas não expôs links utilizáveis."]
            ),
            "mode": "uploadbyurl",
        }

    def _download_temp_image(self, image_url: str) -> str | None:
        try:
            response = self.client.get(image_url)
            if response.status_code >= 400:
                return None

            content_type = (
                response.headers.get("content-type") or ""
            ).casefold()

            suffix = ".jpg"
            if "png" in content_type:
                suffix = ".png"
            elif "webp" in content_type:
                suffix = ".webp"

            handle = tempfile.NamedTemporaryFile(
                delete=False,
                suffix=suffix,
            )
            handle.write(response.content)
            handle.close()
            return handle.name
        except Exception:
            return None

    def _search_file(
        self,
        path: str,
        *,
        title_hint: str,
        max_results: int,
    ) -> dict:
        results = []
        notes = []
        final_url = ""

        try:
            with sync_playwright() as p:
                browser = self._launch_browser(p)
                context = browser.new_context(
                    locale="pt-BR",
                    timezone_id="America/Sao_Paulo",
                    user_agent=USER_AGENT,
                    viewport={"width": 1440, "height": 960},
                )
                page = context.new_page()
                page.goto(
                    "https://www.google.com/?hl=pt-BR",
                    wait_until="domcontentloaded",
                    timeout=self.timeout_ms,
                )

                self._accept_consent(page)

                if not self._open_image_search(page):
                    context.close()
                    browser.close()
                    return {
                        "ok": False,
                        "results": [],
                        "reason": (
                            "o botão Pesquisa por imagem do Google "
                            "não foi encontrado"
                        ),
                    }

                file_input = page.locator('input[type="file"]').first
                file_input.wait_for(
                    state="attached",
                    timeout=7000,
                )
                file_input.set_input_files(path)

                page.wait_for_timeout(4500)

                # O Google permite refinar o Lens com texto depois do upload.
                if title_hint:
                    self._add_text_hint(page, title_hint)

                try:
                    page.wait_for_load_state(
                        "domcontentloaded",
                        timeout=7000,
                    )
                except Exception:
                    pass

                page.wait_for_timeout(3000)
                final_url = page.url

                raw_links = page.locator("a").evaluate_all(
                    """els => els.map((a, i) => ({
                        href: a.href || "",
                        text: (a.innerText || a.textContent || "").trim(),
                        aria: a.getAttribute("aria-label") || "",
                        index: i
                    }))"""
                )

                seen = set()
                for item in raw_links:
                    href = self._decode_google_href(
                        item.get("href") or ""
                    )
                    if not href.startswith(("http://", "https://")):
                        continue

                    h = _host(href)
                    if not h:
                        continue
                    if _root_matches(h, BLOCKED_ROOTS):
                        continue

                    key = href.split("#")[0]
                    if key in seen:
                        continue
                    seen.add(key)

                    results.append({
                        "url": key,
                        "host": h,
                        "title": _clean(
                            item.get("text")
                            or item.get("aria")
                        )[:240],
                        "rank": len(results) + 1,
                        "is_marketplace": _root_matches(
                            h,
                            MARKETPLACE_ROOTS,
                        ),
                        "source": "google_lens",
                    })

                    if len(results) >= max_results:
                        break

                context.close()
                browser.close()

        except Exception as exc:
            return {
                "ok": False,
                "results": [],
                "reason": _clean(str(exc))[:220],
                "final_url": final_url,
            }

        marketplace_count = sum(
            1
            for item in results
            if item.get("is_marketplace")
        )

        if not results:
            notes.append(
                "O Lens abriu, mas não expôs links externos utilizáveis."
            )

        return {
            "ok": bool(results),
            "results": results,
            "marketplace_count": marketplace_count,
            "final_url": final_url,
            "notes": notes,
        }

    def _launch_browser(self, playwright):
        common_args = [
            "--disable-dev-shm-usage",
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-gpu",
        ]

        # Em Railway/Linux usamos diretamente o Chromium instalado pelo
        # Playwright. Tentar o canal "chrome" primeiro nesse ambiente pode
        # encerrar o processo antes de criar a página.
        if os.getenv("RAILWAY_ENVIRONMENT"):
            return playwright.chromium.launch(
                headless=True,
                args=common_args,
            )

        # No Windows final, tenta usar o Chrome já instalado. Se não existir,
        # usa o Chromium empacotado pelo AGCN.
        try:
            return playwright.chromium.launch(
                channel="chrome",
                headless=self.headless,
                args=common_args,
            )
        except Exception:
            return playwright.chromium.launch(
                headless=self.headless,
                args=common_args,
            )

    def _accept_consent(self, page) -> None:
        labels = (
            "Aceitar tudo",
            "Accept all",
            "Concordo",
            "I agree",
        )

        for label in labels:
            try:
                button = page.get_by_role(
                    "button",
                    name=label,
                    exact=False,
                ).first
                if button.count() and button.is_visible():
                    button.click(timeout=1500)
                    page.wait_for_timeout(500)
                    return
            except Exception:
                continue

    def _open_image_search(self, page) -> bool:
        selectors = (
            '[aria-label="Pesquisa por imagem"]',
            '[aria-label="Pesquisar por imagem"]',
            '[aria-label="Search by image"]',
            '[aria-label*="Google Lens" i]',
            'div[role="button"][aria-label*="imagem" i]',
            'div[role="button"][aria-label*="image" i]',
            'button[aria-label*="imagem" i]',
            'button[aria-label*="image" i]',
        )

        for selector in selectors:
            try:
                locator = page.locator(selector).first
                if locator.count() and locator.is_visible():
                    locator.click(timeout=2500)
                    page.wait_for_timeout(900)
                    if page.locator('input[type="file"]').count():
                        return True
            except Exception:
                continue

        # Alguns layouts mantêm o input file no DOM antes do clique.
        return bool(page.locator('input[type="file"]').count())

    def _add_text_hint(self, page, title_hint: str) -> None:
        hint = _clean(title_hint)[:180]
        if not hint:
            return

        selectors = (
            'input[placeholder*="Adicionar à sua pesquisa" i]',
            'textarea[placeholder*="Adicionar à sua pesquisa" i]',
            'input[placeholder*="Add to your search" i]',
            'textarea[placeholder*="Add to your search" i]',
            'input[aria-label*="Adicionar à sua pesquisa" i]',
            'input[aria-label*="Add to your search" i]',
        )

        for selector in selectors:
            try:
                field = page.locator(selector).first
                if field.count() and field.is_visible():
                    field.fill(hint)
                    field.press("Enter")
                    page.wait_for_timeout(3000)
                    return
            except Exception:
                continue

    def _decode_google_href(self, href: str) -> str:
        if not href:
            return ""

        try:
            parsed = urlparse(href)
            h = parsed.netloc.casefold()

            if "google." in h:
                params = parse_qs(parsed.query)

                for key in ("q", "url", "imgurl"):
                    value = (params.get(key) or [None])[0]
                    if value and value.startswith(
                        ("http://", "https://")
                    ):
                        return unquote(value)
        except Exception:
            pass

        return href


def lens_enabled_for_current_machine() -> bool:
    """Local: ON por padrão. Railway/servidor: OFF por padrão."""
    explicit = os.getenv("AGCN_LENS_ENABLED")
    if explicit is not None:
        return explicit.strip().casefold() in {
            "1",
            "true",
            "yes",
            "sim",
            "on",
        }

    if os.getenv("RAILWAY_ENVIRONMENT"):
        return False

    return True

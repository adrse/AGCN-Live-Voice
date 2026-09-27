from core.product_enrichment import MarketplaceEnrichmentEngine
from core.visual_product_discovery import GoogleLensDiscovery


def test_google_redirect_decoder():
    lens = GoogleLensDiscovery()
    url = (
        "https://www.google.com/url?"
        "q=https%3A%2F%2Fwww.magazineluiza.com.br%2Fproduto%2Fp%2F123"
    )
    assert (
        lens._decode_google_href(url)
        == "https://www.magazineluiza.com.br/produto/p/123"
    )


def test_lens_results_merge_before_text_results():
    engine = MarketplaceEnrichmentEngine()
    lens = [{
        "url": "https://www.magazineluiza.com.br/item/p/1",
        "host": "magazineluiza.com.br",
        "marketplace": "Magazine Luiza",
        "title": "Produto visual",
        "snippet": "",
        "source": "google_lens",
        "lens_rank": 1,
    }]
    text = [{
        "url": "https://www.magazineluiza.com.br/item/p/1",
        "host": "magazineluiza.com.br",
        "marketplace": "Magazine Luiza",
        "title": "Produto textual",
        "snippet": "",
    }]
    merged = engine._merge_discovery_results(lens, text)
    assert len(merged) == 1
    assert merged[0]["source"] == "google_lens"


def test_generic_product_can_use_lens_with_two_matching_terms():
    engine = MarketplaceEnrichmentEngine()
    accepted = engine._accept_candidates(
        identity={
            "name": "Kit 3 Frigideiras Antiaderentes",
            "brand": "",
            "model": "",
            "category": "Panelas e frigideiras",
        },
        candidates=[{
            "url": "https://www.amazon.com.br/produto/1",
            "host": "amazon.com.br",
            "marketplace": "Amazon",
            "title": "Kit Frigideiras Antiaderentes",
            "snippet": "",
            "source": "google_lens",
            "lens_rank": 1,
        }],
        limit=10,
    )
    assert len(accepted) == 1
    assert accepted[0]["match_score"] > 0

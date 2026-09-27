from core.product_research import ProductResearchEngine


def test_extracts_jsonld_product_without_network():
    engine = ProductResearchEngine()
    html = """
    <html>
      <head>
        <meta property="og:title" content="Relógio Teste">
        <script type="application/ld+json">
        {
          "@context": "https://schema.org",
          "@type": "Product",
          "name": "Relógio S20",
          "brand": {"@type": "Brand", "name": "Marca X"},
          "model": "S20",
          "description": "Relógio com bateria de longa duração.",
          "image": "https://example.com/relogio.jpg",
          "offers": {"@type": "Offer", "price": "129.90"},
          "aggregateRating": {
            "@type": "AggregateRating",
            "ratingValue": "4.8",
            "reviewCount": "321"
          },
          "review": [
            {
              "@type": "Review",
              "reviewBody": "Muito bom, bateria dura bastante."
            }
          ]
        }
        </script>
      </head>
    </html>
    """
    parsed = engine._parse_html(
        html,
        "https://example.com/produto",
    )
    assert parsed["product"]["name"] == "Relógio S20"
    assert parsed["product"]["brand"] == "Marca X"
    assert parsed["product"]["model"] == "S20"
    assert parsed["product"]["price"] == 129.90
    assert parsed["reviews"][0].startswith("Muito bom")


def test_generic_tiktok_title_is_rejected():
    engine = ProductResearchEngine()
    assert engine._clean_product_title("TikTok - Make Your Day") == ""

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



def test_decodes_tiktok_share_metadata():
    engine = ProductResearchEngine()
    url = (
        "https://shop.tiktok.com/br/pdp/1737135918501169097"
        "?og_info=%257B%2522title%2522%253A%2522Aurafit%2BG6%2BSmartwatch%2Bpara%2BEsportes%2522%252C"
        "%2522image%2522%253A%2522https%253A%255C%252F%255C%252Fcdn.example.com%255C%252Fg6.png%2522%257D"
        "&ec_search_share_params=%257B%2522product_id%2522%253A%25221737135918501169097%2522%252C"
        "%2522group_id%2522%253A%25227690277782772845320%2522%257D"
    )

    meta = engine._metadata_from_url(url)

    assert meta["name"] == "Aurafit G6 Smartwatch para Esportes"
    assert meta["product_id"] == "1737135918501169097"
    assert meta["group_id"] == "7690277782772845320"
    assert meta["image_url"] == "https://cdn.example.com/g6.png"


def test_security_check_is_not_a_product_name():
    engine = ProductResearchEngine()
    assert engine._clean_product_title("Security Check") == ""

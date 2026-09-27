from __future__ import annotations

import argparse
import json
import os

from core.product_research_v054 import ProductResearchEngineV054


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Teste local do Product Identity: TikTok + Google Lens + "
            "marketplaces. Nenhum backend AGCN é utilizado."
        )
    )
    parser.add_argument("url", help="Link do produto TikTok")
    parser.add_argument(
        "--show-browser",
        action="store_true",
        help="Mantém o navegador do Lens visível durante o teste.",
    )
    args = parser.parse_args()

    os.environ["AGCN_LENS_ENABLED"] = "1"

    engine = ProductResearchEngineV054()

    if args.show_browser:
        engine.enrichment.lens.headless = False

    result = engine.analyze(args.url)

    summary = result.get("research_summary") or {}
    enrichment = summary.get("enrichment") or {}

    output = {
        "ok": result.get("ok"),
        "identity": {
            key: (result.get("values") or {}).get(key)
            for key in (
                "name",
                "brand",
                "model",
                "category",
                "image_url",
            )
        },
        "discovery": enrichment.get("discovery") or {},
        "confirmed_match_count": enrichment.get(
            "confirmed_match_count",
            0,
        ),
        "needs_confirmation": enrichment.get(
            "needs_confirmation",
            False,
        ),
        "candidates": enrichment.get(
            "candidate_matches"
        ) or [],
        "technical_specs": summary.get(
            "technical_specs"
        ) or [],
        "filled_values": result.get("values") or {},
        "notes": summary.get("notes") or [],
    }

    print(
        json.dumps(
            output,
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

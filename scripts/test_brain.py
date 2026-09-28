"""Teste manual do Presenter Brain sem precisar abrir uma LIVE.

Exemplos:
  python scripts/test_brain.py --provider qwen_local --proactive
  python scripts/test_brain.py --provider qwen_local --comment "quanto custa?"
  python scripts/test_brain.py --provider openai --comment "pega internet?"

O script usa o produto ativo do ProductStore.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from core.brain_factory import build_brain_provider
from core.presenter_v3 import PresenterV3
from core.product_store import ProductStore


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "desktop" / "config.example.json"


def load_config(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG),
        help="arquivo JSON de configuração",
    )
    parser.add_argument(
        "--provider",
        choices=["qwen_local", "openai", "openai_compatible"],
        help="sobrescreve brain.provider",
    )
    parser.add_argument("--comment", help="comentário para simular")
    parser.add_argument("--user", default="Cliente")
    parser.add_argument(
        "--proactive",
        action="store_true",
        help="gera uma fala proativa",
    )
    args = parser.parse_args()

    config = load_config(Path(args.config))
    if args.provider:
        config.setdefault("brain", {})["provider"] = args.provider

    store = ProductStore()
    product = store.active_for_presenter()
    if not product or not product.get("name"):
        print("ERRO: cadastre e ative um produto antes do teste.")
        return 2

    try:
        brain = build_brain_provider(config)
    except Exception as exc:
        print(f"ERRO AO CONFIGURAR BRAIN: {exc}")
        return 3

    ok, message = brain.healthcheck()
    print(f"Brain: {brain.name}")
    print(f"Healthcheck: {'OK' if ok else 'FALHOU'} - {message}")
    if not ok:
        return 4

    presenter = PresenterV3(product, brain)

    if args.comment:
        result = presenter.test_comment(args.user, args.comment)
    else:
        result = presenter.test_proactive()

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 5


if __name__ == "__main__":
    raise SystemExit(main())

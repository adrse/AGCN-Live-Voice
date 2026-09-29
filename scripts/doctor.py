from __future__ import annotations

import json

from core.diagnostics import diagnostics_text, run_diagnostics
from desktop.config_store import ConfigStore


def main() -> int:
    config = ConfigStore().load()
    result = run_diagnostics(config)
    print(diagnostics_text(result))
    print()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ready_for_live") else 1


if __name__ == "__main__":
    raise SystemExit(main())

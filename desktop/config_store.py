"""Persistência de configuração do programa Windows.

O arquivo distribuído desktop/config.example.json é apenas default público.
A configuração real do usuário fica em %APPDATA%/AGCN Live Voice/config.json.
Secrets continuam em variáveis de ambiente e nunca são persistidos aqui.
"""

from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = ROOT / "desktop" / "config.example.json"


def app_data_dir() -> Path:
    base = os.getenv("APPDATA")
    if base:
        root = Path(base)
    else:
        root = Path.home() / ".agcn-live-voice"
    path = root / "AGCN Live Voice"
    path.mkdir(parents=True, exist_ok=True)
    return path


def user_config_path() -> Path:
    return app_data_dir() / "config.json"


def _deep_merge(base: dict, overlay: dict) -> dict:
    result = deepcopy(base)
    for key, value in (overlay or {}).items():
        if (
            isinstance(value, dict)
            and isinstance(result.get(key), dict)
        ):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def _strip_secrets(value: Any) -> Any:
    """Remove qualquer chave sensível que alguém tente salvar por engano."""
    if isinstance(value, dict):
        clean = {}
        for key, item in value.items():
            folded = str(key).casefold()
            if folded in {
                "api_key",
                "apikey",
                "secret",
                "token",
                "access_token",
                "refresh_token",
            }:
                continue
            clean[key] = _strip_secrets(item)
        return clean
    if isinstance(value, list):
        return [_strip_secrets(item) for item in value]
    return value


class ConfigStore:
    def __init__(
        self,
        *,
        path: str | Path | None = None,
        defaults_path: str | Path | None = None,
    ) -> None:
        self.path = Path(path) if path else user_config_path()
        self.defaults_path = (
            Path(defaults_path)
            if defaults_path
            else DEFAULT_CONFIG_PATH
        )

    def defaults(self) -> dict:
        if not self.defaults_path.exists():
            return {}
        return json.loads(
            self.defaults_path.read_text(encoding="utf-8")
        )

    def load(self) -> dict:
        defaults = self.defaults()
        stored = {}
        if self.path.exists():
            try:
                raw = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    stored = raw
            except Exception:
                stored = {}
        return _deep_merge(defaults, stored)

    def save(self, config: dict[str, Any]) -> dict:
        safe = _strip_secrets(dict(config or {}))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(safe, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return safe

    def update(self, patch: dict[str, Any]) -> dict:
        current = self.load()
        merged = _deep_merge(current, patch or {})
        self.save(merged)
        return merged

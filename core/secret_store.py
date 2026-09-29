"""Secrets do AGCN.

Prioridade de leitura:
1. variável de ambiente;
2. keyring do sistema operacional (Windows Credential Manager no Windows).

Nunca grava secret em config.json.
"""

from __future__ import annotations

import os


SERVICE_NAME = "AGCN Live Voice"


def get_secret(name: str) -> str:
    name = str(name or "").strip()
    if not name:
        return ""

    value = str(os.getenv(name) or "").strip()
    if value:
        return value

    try:
        import keyring
        return str(
            keyring.get_password(SERVICE_NAME, name) or ""
        ).strip()
    except Exception:
        return ""


def set_secret(name: str, value: str) -> None:
    name = str(name or "").strip()
    if not name:
        raise ValueError("nome do secret é obrigatório")

    try:
        import keyring
    except ImportError as exc:
        raise RuntimeError(
            "keyring não instalado. Instale requirements-desktop.txt"
        ) from exc

    value = str(value or "")
    if value:
        keyring.set_password(SERVICE_NAME, name, value)
    else:
        try:
            keyring.delete_password(SERVICE_NAME, name)
        except Exception:
            pass


def has_secret(name: str) -> bool:
    return bool(get_secret(name))

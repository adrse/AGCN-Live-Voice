from __future__ import annotations

import re


_BRL_RE = re.compile(
    r"R\\$\\s*(\\d{1,3}(?:\\.\\d{3})*(?:,\\d{1,2})?|\\d+(?:[.,]\\d{1,2})?)",
    flags=re.IGNORECASE,
)


def _spoken_brl(match: re.Match[str]) -> str:
    raw = match.group(1).strip()
    if "," in raw:
        whole_raw, cents_raw = raw.rsplit(",", 1)
        whole = int(whole_raw.replace(".", "") or "0")
        cents = int((cents_raw + "00")[:2])
    elif raw.count(".") == 1 and len(raw.rsplit(".", 1)[1]) <= 2:
        whole_raw, cents_raw = raw.rsplit(".", 1)
        whole = int(whole_raw or "0")
        cents = int((cents_raw + "00")[:2])
    else:
        whole = int(raw.replace(".", "") or "0")
        cents = 0

    reais = "real" if whole == 1 else "reais"
    if cents:
        centavos = "centavo" if cents == 1 else "centavos"
        return f"{whole} {reais} e {cents} {centavos}"
    return f"{whole} {reais}"


def normalize_ptbr_for_tts(text: str) -> str:
    """Torna símbolos brasileiros inequívocos para qualquer motor de voz.

    Alguns TTS interpretam R$ como dólar. A UI pode continuar exibindo o
    símbolo, mas o texto enviado ao sintetizador usa explicitamente
    reais/centavos.
    """
    value = str(text or "").strip()
    if not value:
        return value
    return _BRL_RE.sub(_spoken_brl, value)

"""Perfis de voz do AGCN Live Voice.

Os perfis são independentes do Brain. O Brain decide O QUE falar;
o perfil define COMO a fala é vocalizada.
"""

from __future__ import annotations

from copy import deepcopy


VOICE_PROFILES = {
    "female_fast": {
        "id": "female_fast",
        "label": "Feminina — Vendas rápidas",
        "local_rate": 235,
        "local_keywords": [
            "female",
            "feminino",
            "feminina",
            "zira",
            "maria",
            "francisca",
            "helena",
        ],
        "qwen_speaker": "vivian",
        "qwen_style": (
            "Bright young female sales presenter. Brazilian Portuguese. "
            "Energetic, confident, fast-paced live-commerce delivery, crisp "
            "articulation, short pauses, persuasive but natural."
        ),
        "openai_voice": "marin",
        "default_speed": 1.28,
        "openai_instructions": (
            "Fale em português brasileiro com voz feminina clara, confiante e "
            "energética. Ritmo rápido de live commerce, dicção firme, frases "
            "curtas, pouca pausa e resposta imediata. Soe como uma apresentadora "
            "de vendas ao vivo muito proativa: mantenha energia alta, destaque "
            "preço, benefício ou resposta sem enrolar e não use ritmo de conversa "
            "casual ou atendimento lento."
        ),
    },
    "male_fast": {
        "id": "male_fast",
        "label": "Masculina — Vendas rápidas",
        "local_rate": 235,
        "local_keywords": [
            "male",
            "masculino",
            "masculina",
            "david",
            "daniel",
            "antonio",
            "paulo",
        ],
        "qwen_speaker": "ryan",
        "qwen_style": (
            "Dynamic male sales presenter. Brazilian Portuguese. Energetic, "
            "confident, fast-paced live-commerce delivery, strong rhythmic "
            "drive, crisp articulation, short pauses and immediate answers."
        ),
        "openai_voice": "cedar",
        "default_speed": 1.28,
        "openai_instructions": (
            "Fale em português brasileiro com voz masculina firme, confiante e "
            "energética. Ritmo rápido de live commerce, dicção firme, frases "
            "curtas, pouca pausa e resposta imediata. Soe como um apresentador "
            "de vendas ao vivo muito proativo: mantenha energia alta, destaque "
            "preço, benefício ou resposta sem enrolar e não use ritmo de conversa "
            "casual ou atendimento lento."
        ),
    },
}

DEFAULT_VOICE_PROFILE = "female_fast"


def get_voice_profile(profile_id: str | None) -> dict:
    key = str(profile_id or DEFAULT_VOICE_PROFILE).strip().casefold()
    if key not in VOICE_PROFILES:
        key = DEFAULT_VOICE_PROFILE
    return deepcopy(VOICE_PROFILES[key])


def list_voice_profiles() -> list[dict]:
    return [deepcopy(item) for item in VOICE_PROFILES.values()]

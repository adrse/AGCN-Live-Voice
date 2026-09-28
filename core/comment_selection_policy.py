"""Política central para decidir quais comentários merecem resposta.

Objetivo:
- o LLM NÃO recebe liberdade para responder qualquer coisa do chat;
- o código filtra ruído, usa a inteligência local e aplica prioridade comercial;
- um modelo semântico pode ser usado apenas nos casos ambíguos, com saída JSON;
- o Decision Engine continua sendo a autoridade final da fila.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Iterable

from core.comment_intelligence import CommentIntelligence, clean


HIGH_PRIORITY_INTENTS = {
    "safety_or_critical",
    "buying_intent",
    "price",
    "objection",
    "availability",
    "compatibility",
    "technical_question",
    "shipping",
    "warranty",
}

NEVER_DROP_FOR_RECENT_USER = {
    "safety_or_critical",
    "buying_intent",
    "price",
    "objection",
}


SEMANTIC_ROUTER_SYSTEM_INSTRUCTION = r"""
Você é o roteador semântico de comentários do AGCN Live Voice.

Sua função NÃO é responder ao público e NÃO é vender. Sua função é interpretar comentários ambíguos da LIVE para que o código decida se eles merecem resposta.

Prioridade comercial geral:
1. intenção de compra / como comprar;
2. preço, desconto, cupom, frete, disponibilidade e estoque;
3. objeção que pode impedir a compra;
4. pergunta técnica, compatibilidade e uso;
5. benefícios/diferenciais;
6. confirmação de compra;
7. comentário geral relevante;
8. saudação, emoji, elogio solto, spam e conversa paralela normalmente não exigem resposta.

Regras:
- não invente fatos do produto;
- não gere texto de fala;
- não marque tudo como importante;
- uma pergunta real sobre o produto é mais importante que um elogio;
- gírias, abreviações e erros de digitação devem ser entendidos;
- "quero", "como pega", "onde clica", "manda link", "vou levar" e equivalentes indicam intenção de compra;
- se o comentário não tiver relação clara com a venda/produto, should_answer=false;
- se houver dúvida, classifique como intent="direct_question" ou "unknown" e dê relevance conservadora.

Responda SOMENTE JSON válido:
{
  "items": [
    {
      "id": "id original",
      "intent": "buying_intent|price|objection|availability|compatibility|technical_question|shipping|warranty|included_items|size|battery|benefits|usage|purchase_confirmation|direct_question|engagement|unknown",
      "topic": "tema curto",
      "relevance": 0,
      "should_answer": false,
      "reason": "motivo curto"
    }
  ]
}
""".strip()


@dataclass(slots=True)
class RoutedComment:
    id: str
    user: str
    text: str
    intent: str
    topic: str
    priority: int
    should_answer: bool
    source: str = "local"
    reason: str = ""


def _letters_or_digits(text: str) -> str:
    return "".join(ch for ch in text if ch.isalnum())


def is_obvious_noise(text: str) -> bool:
    """Remove apenas ruído óbvio. Em caso de dúvida, deixa passar."""
    t = clean(text)
    if not t:
        return True

    if not _letters_or_digits(t):
        return True

    folded = t.casefold().strip()
    greeting_only = {
        "oi", "ola", "olá", "bom dia", "boa tarde", "boa noite",
        "top", "show", "lindo", "linda", "amei", "kkk", "kkkk",
    }
    if folded in greeting_only:
        return True

    compact = re.sub(r"\s+", "", folded)
    if len(compact) >= 8 and len(set(compact)) <= 2:
        return True

    return False


class CommentSelectionPolicy:
    """Pré-filtro e prioridade antes do Decision Engine."""

    def __init__(self, intelligence: CommentIntelligence | None = None):
        self.intelligence = intelligence or CommentIntelligence()

    def route_local(self, comment_id: str, user: str, text: str) -> RoutedComment | None:
        if is_obvious_noise(text):
            return None

        analyzed = self.intelligence.analyze(user, text)
        if analyzed is None:
            return RoutedComment(
                id=str(comment_id or ""),
                user=clean(user),
                text=clean(text),
                intent="unknown",
                topic="unknown",
                priority=0,
                should_answer=False,
                source="local_uncertain",
                reason="sem intenção comercial reconhecida localmente",
            )

        intent = str(analyzed.get("intent") or "unknown")
        priority = int(analyzed.get("priority") or 0)
        should_answer = intent != "engagement"

        return RoutedComment(
            id=str(comment_id or ""),
            user=str(analyzed.get("user") or clean(user)),
            text=str(analyzed.get("comment") or clean(text)),
            intent=intent,
            topic=str(analyzed.get("topic") or "general"),
            priority=priority,
            should_answer=should_answer,
            source="local",
            reason=str(analyzed.get("label") or intent),
        )

    def select_next(
        self,
        comments: Iterable[RoutedComment],
        *,
        recently_answered_users: set[str] | None = None,
    ) -> RoutedComment | None:
        recent = {str(x).casefold() for x in (recently_answered_users or set())}
        candidates: list[tuple[int, RoutedComment]] = []

        for item in comments:
            if not item.should_answer:
                continue

            score = int(item.priority)
            user_key = item.user.casefold()

            if (
                user_key
                and user_key in recent
                and item.intent not in NEVER_DROP_FOR_RECENT_USER
            ):
                score -= 8

            if item.intent in HIGH_PRIORITY_INTENTS:
                score += 2

            candidates.append((score, item))

        if not candidates:
            return None

        candidates.sort(key=lambda pair: pair[0], reverse=True)
        return candidates[0][1]


def build_semantic_router_payload(comments: Iterable[dict]) -> str:
    """Pacote curto para interpretação semântica dos itens ambíguos."""
    items = []
    for item in comments:
        items.append({
            "id": str(item.get("id") or ""),
            "user": clean(item.get("user") or ""),
            "text": clean(item.get("text") or item.get("comment") or ""),
        })
    return json.dumps({"comments": items[:20]}, ensure_ascii=False, separators=(",", ":"))

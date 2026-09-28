"""Orquestrador obrigatorio do Presenter Brain.

Todos os modelos passam por esta classe. O transport somente chama Qwen/API;
a politica de LIVE e aplicada aqui.
"""

from __future__ import annotations

import json
from typing import Any

from core.integration_contracts import BrainContext, BrainResult, TextModelTransport
from core.presenter_policy import build_system_instruction, build_turn_payload


class BrainOutputError(ValueError):
    pass


class PresenterBrain:
    def __init__(self, transport: TextModelTransport):
        self.transport = transport

    @property
    def name(self) -> str:
        return self.transport.name

    def healthcheck(self) -> tuple[bool, str]:
        return self.transport.healthcheck()

    def generate(self, context: BrainContext) -> BrainResult:
        system_instruction = build_system_instruction()
        user_payload = build_turn_payload(context)

        raw_text = self.transport.complete(
            system_instruction=system_instruction,
            user_payload=user_payload,
        )
        data = self._parse_json(raw_text)
        return self._to_result(data, context)

    @staticmethod
    def _parse_json(raw_text: str) -> dict[str, Any]:
        text = (raw_text or "").strip()
        if not text:
            raise BrainOutputError("O Brain retornou resposta vazia.")

        if text.startswith("~~~"):
            lines = text.splitlines()[1:]
            if lines and lines[-1].strip().startswith("~~~"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()

        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise BrainOutputError("O Brain nao retornou JSON valido.") from exc

        if not isinstance(data, dict):
            raise BrainOutputError("A saida do Brain precisa ser um objeto JSON.")
        return data

    @staticmethod
    def _to_result(data: dict[str, Any], context: BrainContext) -> BrainResult:
        speech = str(data.get("speech") or "").strip()
        if not speech:
            raise BrainOutputError("Campo speech ausente ou vazio.")

        used_facts_raw = data.get("used_facts") or []
        if not isinstance(used_facts_raw, list):
            raise BrainOutputError("Campo used_facts precisa ser uma lista.")

        used_facts = [
            str(item).strip()
            for item in used_facts_raw
            if str(item).strip()
        ]

        if used_facts and not context.allowed_facts:
            raise BrainOutputError("Brain declarou fatos sem ALLOWED_FACTS.")

        return BrainResult(
            speech=speech,
            topic=str(data.get("topic") or context.planner_topic or "").strip(),
            used_facts=used_facts,
            needs_fact=bool(data.get("needs_fact", False)),
            next_sales_thread=str(data.get("next_sales_thread") or "").strip(),
            raw=data,
        )

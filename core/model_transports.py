"""Transportes reais de modelo para o Presenter Brain.

O transporte só envia/recebe texto estruturado. Regras de venda, fatos e
comportamento permanecem em presenter_policy + brain_orchestrator.
"""

from __future__ import annotations

from typing import Any

import requests


BRAIN_RESULT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "speech": {"type": "string"},
        "topic": {"type": "string"},
        "used_facts": {
            "type": "array",
            "items": {"type": "string"},
        },
        "needs_fact": {"type": "boolean"},
        "next_sales_thread": {"type": "string"},
    },
    "required": [
        "speech",
        "topic",
        "used_facts",
        "needs_fact",
        "next_sales_thread",
    ],
    "additionalProperties": False,
}


class TransportError(RuntimeError):
    pass


def _raise_for_status(response, *, provider: str) -> None:
    try:
        response.raise_for_status()
    except Exception as exc:
        detail = ""
        try:
            payload = response.json()
            detail = str(
                payload.get("error")
                or payload.get("message")
                or payload
            )
        except Exception:
            detail = str(getattr(response, "text", "") or "")
        detail = detail.strip()
        if len(detail) > 500:
            detail = detail[:500] + "..."
        suffix = f": {detail}" if detail else ""
        raise TransportError(
            f"{provider} retornou HTTP {getattr(response, 'status_code', '?')}{suffix}"
        ) from exc


class OllamaTransport:
    """Qwen/Ollama local.

    Usa /api/chat com JSON Schema para que a saída já venha no contrato
    BrainResult. A PresenterPolicy continua sendo injetada pelo orquestrador.
    """

    def __init__(
        self,
        *,
        base_url: str = "http://127.0.0.1:11434",
        model: str = "qwen3:4b",
        timeout_seconds: float = 45,
        temperature: float = 0.25,
        keep_alive: str = "10m",
        session=None,
    ) -> None:
        self.base_url = str(base_url or "").rstrip("/")
        self.model = str(model or "").strip()
        self.timeout_seconds = float(timeout_seconds)
        self.temperature = float(temperature)
        self.keep_alive = str(keep_alive or "10m")
        self.session = session or requests.Session()

        if not self.base_url:
            raise ValueError("ollama base_url é obrigatório")
        if not self.model:
            raise ValueError("ollama model é obrigatório")

    @property
    def name(self) -> str:
        return f"Ollama/{self.model}"

    def healthcheck(self) -> tuple[bool, str]:
        try:
            response = self.session.get(
                f"{self.base_url}/api/tags",
                timeout=min(self.timeout_seconds, 8.0),
            )
            _raise_for_status(response, provider="Ollama")
            data = response.json()
            names = {
                str(item.get("name") or item.get("model") or "").strip()
                for item in (data.get("models") or [])
                if isinstance(item, dict)
            }
            if names and self.model not in names:
                return (
                    False,
                    f"Ollama ativo, mas modelo {self.model!r} não está instalado.",
                )
            return True, f"Ollama ativo com {self.model}."
        except Exception as exc:
            return False, f"Ollama indisponível: {exc}"

    def complete(self, *, system_instruction: str, user_payload: str) -> str:
        body = {
            "model": self.model,
            "stream": False,
            "messages": [
                {
                    "role": "system",
                    "content": system_instruction,
                },
                {
                    "role": "user",
                    "content": user_payload,
                },
            ],
            "format": BRAIN_RESULT_SCHEMA,
            "options": {
                "temperature": self.temperature,
            },
            "keep_alive": self.keep_alive,
        }

        try:
            response = self.session.post(
                f"{self.base_url}/api/chat",
                json=body,
                timeout=self.timeout_seconds,
            )
        except requests.RequestException as exc:
            raise TransportError(f"falha ao chamar Ollama: {exc}") from exc

        _raise_for_status(response, provider="Ollama")

        try:
            payload = response.json()
        except Exception as exc:
            raise TransportError("Ollama retornou JSON HTTP inválido") from exc

        content = str(
            (payload.get("message") or {}).get("content") or ""
        ).strip()
        if not content:
            raise TransportError("Ollama retornou resposta vazia")
        return content


class OpenAIResponsesTransport:
    """OpenAI Responses API com Structured Outputs.

    A chave nunca é embutida no programa. O factory lê OPENAI_API_KEY
    ou outra variável explicitamente configurada.
    """

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str = "https://api.openai.com/v1",
        timeout_seconds: float = 45,
        max_output_tokens: int = 500,
        session=None,
    ) -> None:
        self.api_key = str(api_key or "").strip()
        self.model = str(model or "").strip()
        self.base_url = str(base_url or "").rstrip("/")
        self.timeout_seconds = float(timeout_seconds)
        self.max_output_tokens = int(max_output_tokens)
        self.session = session or requests.Session()

        if not self.api_key:
            raise ValueError("api_key da OpenAI é obrigatória")
        if not self.model:
            raise ValueError("model da OpenAI é obrigatório")

    @property
    def name(self) -> str:
        return f"OpenAI Responses/{self.model}"

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def healthcheck(self) -> tuple[bool, str]:
        try:
            response = self.session.get(
                f"{self.base_url}/models/{self.model}",
                headers=self._headers(),
                timeout=min(self.timeout_seconds, 8.0),
            )
            _raise_for_status(response, provider="OpenAI")
            return True, f"OpenAI API acessível com {self.model}."
        except Exception as exc:
            return False, f"OpenAI API indisponível: {exc}"

    def complete(self, *, system_instruction: str, user_payload: str) -> str:
        body = {
            "model": self.model,
            "instructions": system_instruction,
            "input": user_payload,
            "store": False,
            "max_output_tokens": self.max_output_tokens,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "agcn_brain_result",
                    "strict": True,
                    "schema": BRAIN_RESULT_SCHEMA,
                }
            },
        }

        try:
            response = self.session.post(
                f"{self.base_url}/responses",
                headers=self._headers(),
                json=body,
                timeout=self.timeout_seconds,
            )
        except requests.RequestException as exc:
            raise TransportError(f"falha ao chamar OpenAI: {exc}") from exc

        _raise_for_status(response, provider="OpenAI")

        try:
            payload = response.json()
        except Exception as exc:
            raise TransportError("OpenAI retornou JSON HTTP inválido") from exc

        text = self._extract_output_text(payload)
        if not text:
            raise TransportError("OpenAI retornou resposta de texto vazia")
        return text

    @staticmethod
    def _extract_output_text(payload: dict[str, Any]) -> str:
        direct = payload.get("output_text")
        if isinstance(direct, str) and direct.strip():
            return direct.strip()

        pieces: list[str] = []
        for item in payload.get("output") or []:
            if not isinstance(item, dict):
                continue
            for content in item.get("content") or []:
                if not isinstance(content, dict):
                    continue
                value = content.get("text")
                if isinstance(value, str) and value.strip():
                    pieces.append(value.strip())
                elif isinstance(value, dict):
                    nested = value.get("value")
                    if isinstance(nested, str) and nested.strip():
                        pieces.append(nested.strip())
        return "\n".join(pieces).strip()


class OpenAICompatibleChatTransport:
    """Provider genérico que implemente /v1/chat/completions.

    Útil para outros serviços compatíveis com o formato OpenAI. Ainda assim,
    a política comercial vem do AGCN e não deste transporte.
    """

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str,
        timeout_seconds: float = 45,
        temperature: float = 0.25,
        session=None,
    ) -> None:
        self.api_key = str(api_key or "").strip()
        self.model = str(model or "").strip()
        self.base_url = str(base_url or "").rstrip("/")
        self.timeout_seconds = float(timeout_seconds)
        self.temperature = float(temperature)
        self.session = session or requests.Session()

        if not self.model:
            raise ValueError("model do provider compatível é obrigatório")
        if not self.base_url:
            raise ValueError("base_url do provider compatível é obrigatório")

    @property
    def name(self) -> str:
        return f"OpenAI-compatible/{self.model}"

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def healthcheck(self) -> tuple[bool, str]:
        try:
            response = self.session.get(
                f"{self.base_url}/models",
                headers=self._headers(),
                timeout=min(self.timeout_seconds, 8.0),
            )
            _raise_for_status(response, provider="API compatível")
            return True, f"API compatível acessível com {self.model}."
        except Exception as exc:
            return False, f"API compatível indisponível: {exc}"

    def complete(self, *, system_instruction: str, user_payload: str) -> str:
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_payload},
            ],
            "temperature": self.temperature,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "agcn_brain_result",
                    "strict": True,
                    "schema": BRAIN_RESULT_SCHEMA,
                },
            },
        }

        try:
            response = self.session.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=body,
                timeout=self.timeout_seconds,
            )
        except requests.RequestException as exc:
            raise TransportError(
                f"falha ao chamar API compatível: {exc}"
            ) from exc

        _raise_for_status(response, provider="API compatível")

        try:
            payload = response.json()
            content = (
                payload["choices"][0]["message"]["content"]
            )
        except Exception as exc:
            raise TransportError(
                "API compatível retornou formato inesperado"
            ) from exc

        content = str(content or "").strip()
        if not content:
            raise TransportError("API compatível retornou resposta vazia")
        return content

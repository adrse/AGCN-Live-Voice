"""Brain local embutido do AGCN usando llama.cpp + Qwen3 GGUF.

O cliente final não precisa instalar Ollama, Python ou qualquer outro runtime.
O pacote completo inclui llama-server.exe, DLLs e o modelo Qwen3-4B.
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

import requests

from core.model_transports import BRAIN_RESULT_SCHEMA, TransportError, _raise_for_status


DEFAULT_MODEL_FILE = "Qwen3-4B-Q4_K_M.gguf"
DEFAULT_LORA_FILE = "AGCN-Presenter-v0.1-F16.gguf"
DEFAULT_MODEL_ALIAS = "agcn-presenter-v0.1"
DEFAULT_PORT = 18766


def _resource_root() -> Path:
    frozen = getattr(sys, "_MEIPASS", None)
    if frozen:
        return Path(frozen)
    return Path(__file__).resolve().parents[1]


def default_local_brain_dir() -> Path:
    return _resource_root() / "brain_local"


def user_brain_model_dir() -> Path:
    base = os.getenv("LOCALAPPDATA") or os.getenv("APPDATA")
    if base:
        path = Path(base) / "AGCN Live Voice" / "models"
    else:
        path = Path.home() / ".agcn-live-voice" / "models"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _log_dir() -> Path:
    base = os.getenv("LOCALAPPDATA") or os.getenv("APPDATA")
    if base:
        path = Path(base) / "AGCN Live Voice" / "logs"
    else:
        path = Path.home() / ".agcn-live-voice" / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


class LlamaCppLocalTransport:
    """Gerencia um llama-server privado e expõe o contrato do Presenter Brain."""

    def __init__(
        self,
        *,
        pack_dir: str | Path | None = None,
        model_file: str = DEFAULT_MODEL_FILE,
        lora_file: str | Path | None = DEFAULT_LORA_FILE,
        require_lora: bool = False,
        model_alias: str = DEFAULT_MODEL_ALIAS,
        host: str = "127.0.0.1",
        port: int = DEFAULT_PORT,
        context_size: int = 4096,
        threads: int | None = None,
        startup_timeout_seconds: float = 180,
        timeout_seconds: float = 45,
        temperature: float = 0.25,
        max_output_tokens: int = 500,
        session=None,
    ) -> None:
        self.pack_dir = (
            Path(pack_dir) if pack_dir else default_local_brain_dir()
        ).resolve()
        self.bin_dir = self.pack_dir / "bin"
        self.model_dir = self.pack_dir / "models"
        self.engine_path = self.bin_dir / (
            "llama-server.exe" if os.name == "nt" else "llama-server"
        )
        self.model_path = self.model_dir / str(model_file or DEFAULT_MODEL_FILE)
        self.lora_file = str(lora_file or "").strip()
        self.require_lora = bool(require_lora)
        self.lora_path = self._resolve_lora_path(self.lora_file)
        self.model_alias = str(model_alias or DEFAULT_MODEL_ALIAS)
        self.host = str(host or "127.0.0.1")
        self.port = int(port or DEFAULT_PORT)
        self.context_size = max(1024, int(context_size or 4096))
        cpu_count = os.cpu_count() or 4
        self.threads = max(
            2,
            min(12, int(threads or max(2, cpu_count - 1))),
        )
        self.startup_timeout_seconds = float(startup_timeout_seconds or 180)
        self.timeout_seconds = float(timeout_seconds or 45)
        self.temperature = float(temperature)
        self.max_output_tokens = int(max_output_tokens or 500)
        self.session = session or requests.Session()

        self.process: subprocess.Popen | None = None
        self._started_by_us = False
        self._lock = threading.RLock()
        self._log_handle = None

    def _resolve_lora_path(self, lora_file: str) -> Path | None:
        if not lora_file:
            return None
        raw = Path(lora_file).expanduser()
        if raw.is_absolute():
            return raw.resolve()

        bundled = (self.model_dir / raw).resolve()
        if bundled.exists():
            return bundled

        user_copy = (user_brain_model_dir() / raw.name).resolve()
        if user_copy.exists():
            return user_copy

        # Mantém um caminho determinístico para diagnostics/require_lora.
        return bundled

    @property
    def lora_active(self) -> bool:
        return bool(self.lora_path and self.lora_path.exists())

    @property
    def name(self) -> str:
        if self.lora_active:
            return "AGCN Presenter v0.1 / Qwen3-4B / llama.cpp"
        return "AGCN Local Brain / Qwen3-4B base / llama.cpp"

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def assets_status(self) -> tuple[bool, str]:
        missing = []
        if not self.engine_path.exists():
            missing.append(str(self.engine_path))
        if not self.model_path.exists():
            missing.append(str(self.model_path))
        if self.require_lora and not self.lora_active:
            missing.append(str(self.lora_path or DEFAULT_LORA_FILE))
        if missing:
            return (
                False,
                "Pacote do Brain local incompleto: " + ", ".join(missing),
            )
        if self.lora_active:
            return (
                True,
                "AGCN Presenter v0.1 pronto: "
                f"{self.model_path.name} + {self.lora_path.name} + llama.cpp.",
            )
        return (
            True,
            "Brain local pronto com Qwen3 base. "
            "O adapter AGCN Presenter v0.1 ainda não está instalado; "
            f"coloque {DEFAULT_LORA_FILE} em "
            f"{user_brain_model_dir()} para ativá-lo.",
        )

    def _server_ready(self) -> bool:
        try:
            response = self.session.get(
                f"{self.base_url}/v1/models",
                timeout=1.5,
            )
            return response.status_code == 200
        except Exception:
            return False

    def _command(self) -> list[str]:
        command = [
            str(self.engine_path),
            "-m",
            str(self.model_path),
            "--alias",
            self.model_alias,
            "--host",
            self.host,
            "--port",
            str(self.port),
            "-c",
            str(self.context_size),
            "-t",
            str(self.threads),
            "--jinja",
            "--reasoning",
            "off",
        ]
        if self.lora_active:
            command.extend(["--lora", str(self.lora_path)])
        return command

    def _start_server(self) -> None:
        if self._server_ready():
            return

        ok, detail = self.assets_status()
        if not ok:
            raise RuntimeError(detail)

        with self._lock:
            if self._server_ready():
                return

            if self.process is not None and self.process.poll() is None:
                return self._wait_until_ready()

            log_path = _log_dir() / "agcn-local-brain.log"
            self._log_handle = open(log_path, "a", encoding="utf-8")

            creationflags = 0
            if os.name == "nt":
                creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

            self.process = subprocess.Popen(
                self._command(),
                cwd=str(self.bin_dir),
                stdout=self._log_handle,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                creationflags=creationflags,
            )
            self._started_by_us = True
            self._wait_until_ready()

    def _wait_until_ready(self) -> None:
        deadline = time.monotonic() + self.startup_timeout_seconds
        while time.monotonic() < deadline:
            if self._server_ready():
                return
            if self.process is not None and self.process.poll() is not None:
                raise RuntimeError(
                    "O AGCN Local Brain encerrou durante a inicialização. "
                    "Consulte agcn-local-brain.log."
                )
            time.sleep(0.35)
        raise TimeoutError(
            "O AGCN Local Brain demorou demais para carregar o Qwen3."
        )

    def healthcheck(self) -> tuple[bool, str]:
        ok, detail = self.assets_status()
        if not ok:
            return False, detail
        try:
            self._start_server()
            response = self.session.get(
                f"{self.base_url}/v1/models",
                timeout=min(self.timeout_seconds, 8.0),
            )
            _raise_for_status(response, provider="AGCN Local Brain")
            # Preserve o diagnóstico real: Presenter quando o LoRA está
            # ativo; Qwen base quando o adapter ainda não foi instalado.
            return True, detail
        except Exception as exc:
            return False, f"AGCN Local Brain indisponível: {exc}"

    def complete(self, *, system_instruction: str, user_payload: str) -> str:
        self._start_server()

        body: dict[str, Any] = {
            "model": self.model_alias,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_payload},
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_output_tokens,
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
                f"{self.base_url}/v1/chat/completions",
                json=body,
                timeout=self.timeout_seconds,
            )
        except requests.RequestException as exc:
            raise TransportError(
                f"falha ao chamar AGCN Local Brain: {exc}"
            ) from exc

        _raise_for_status(response, provider="AGCN Local Brain")

        try:
            payload = response.json()
            content = payload["choices"][0]["message"]["content"]
        except Exception as exc:
            raise TransportError(
                "AGCN Local Brain retornou formato inesperado"
            ) from exc

        content = str(content or "").strip()
        if not content:
            raise TransportError("AGCN Local Brain retornou resposta vazia")
        return content

    def close(self) -> None:
        with self._lock:
            if self._started_by_us and self.process is not None:
                try:
                    if self.process.poll() is None:
                        self.process.terminate()
                        try:
                            self.process.wait(timeout=5)
                        except Exception:
                            self.process.kill()
                except Exception:
                    pass
            self.process = None
            self._started_by_us = False
            if self._log_handle is not None:
                try:
                    self._log_handle.close()
                except Exception:
                    pass
                self._log_handle = None

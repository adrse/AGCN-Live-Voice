import json

from core.local_llama_brain import LlamaCppLocalTransport


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code
        self.text = ""

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeSession:
    def __init__(self):
        self.get_calls = []
        self.post_calls = []

    def get(self, url, **kwargs):
        self.get_calls.append((url, kwargs))
        return FakeResponse({"data": [{"id": "agcn-qwen3-4b"}]})

    def post(self, url, **kwargs):
        self.post_calls.append((url, kwargs))
        return FakeResponse({
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "speech": "Fala local.",
                        "topic": "benefits",
                        "used_facts": [],
                        "needs_fact": False,
                        "next_sales_thread": "usage",
                    })
                }
            }]
        })


def test_local_brain_assets_are_self_contained(tmp_path):
    pack = tmp_path / "brain_local"
    (pack / "bin").mkdir(parents=True)
    (pack / "models").mkdir(parents=True)
    transport = LlamaCppLocalTransport(pack_dir=pack)
    transport.engine_path.write_bytes(b"engine")
    transport.model_path.write_bytes(b"model")
    ok, detail = transport.assets_status()

    assert ok is True
    assert "Qwen3-4B-Q4_K_M.gguf" in detail


def test_local_brain_uses_openai_compatible_schema(tmp_path, monkeypatch):
    pack = tmp_path / "brain_local"
    (pack / "bin").mkdir(parents=True)
    (pack / "models").mkdir(parents=True)
    session = FakeSession()
    transport = LlamaCppLocalTransport(
        pack_dir=pack,
        session=session,
    )
    transport.engine_path.write_bytes(b"engine")
    transport.model_path.write_bytes(b"model")
    monkeypatch.setattr(transport, "_start_server", lambda: None)

    output = transport.complete(
        system_instruction="SYSTEM AGCN",
        user_payload="TURN",
    )

    assert json.loads(output)["speech"] == "Fala local."
    url, kwargs = session.post_calls[0]
    assert url.endswith("/v1/chat/completions")
    body = kwargs["json"]
    assert body["model"] == "agcn-presenter-v0.1"
    assert body["messages"][0]["content"] == "SYSTEM AGCN"
    assert body["response_format"]["type"] == "json_schema"

def test_local_brain_applies_presenter_lora_when_installed(tmp_path):
    pack = tmp_path / "brain_local"
    (pack / "bin").mkdir(parents=True)
    (pack / "models").mkdir(parents=True)

    transport = LlamaCppLocalTransport(pack_dir=pack)
    transport.engine_path.write_bytes(b"engine")
    transport.model_path.write_bytes(b"model")
    lora = pack / "models" / "AGCN-Presenter-v0.1-F16.gguf"
    lora.write_bytes(b"lora")

    # Recria depois que o arquivo existe para resolver o caminho default.
    transport = LlamaCppLocalTransport(pack_dir=pack)
    command = transport._command()

    assert transport.lora_active is True
    assert "--lora" in command
    assert str(lora.resolve()) in command
    assert "Presenter v0.1" in transport.name


def test_local_brain_can_require_presenter_lora(tmp_path):
    pack = tmp_path / "brain_local"
    (pack / "bin").mkdir(parents=True)
    (pack / "models").mkdir(parents=True)

    transport = LlamaCppLocalTransport(
        pack_dir=pack,
        require_lora=True,
    )
    transport.engine_path.write_bytes(b"engine")
    transport.model_path.write_bytes(b"model")

    ok, detail = transport.assets_status()

    assert ok is False
    assert "AGCN-Presenter-v0.1-F16.gguf" in detail


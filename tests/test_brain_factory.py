import pytest

from core.brain_factory import FallbackBrainProvider, build_brain_provider
from core.integration_contracts import BrainContext, BrainResult


class FakeBrain:
    def __init__(self, name, result=None, error=None):
        self._name = name
        self.result = result
        self.error = error

    @property
    def name(self):
        return self._name

    def healthcheck(self):
        return True, "ok"

    def generate(self, context):
        if self.error:
            raise self.error
        return self.result


def test_factory_builds_bundled_local_qwen():
    provider = build_brain_provider({
        "brain": {
            "provider": "qwen_local",
            "local_brain": {
                "pack_dir": "brain_local",
                "model_file": "Qwen3-4B-Q4_K_M.gguf",
            },
        }
    })
    assert "Qwen3-4B" in provider.name
    assert "llama.cpp" in provider.name


def test_openai_requires_key_when_no_fallback(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValueError):
        build_brain_provider({
            "brain": {
                "provider": "openai",
                "fallback_local": False,
                "api": {"model": "gpt-test"},
            }
        })


def test_fallback_uses_local_when_primary_fails():
    fallback_result = BrainResult(speech="fallback")
    provider = FallbackBrainProvider(
        FakeBrain("api", error=RuntimeError("down")),
        FakeBrain("local", result=fallback_result),
    )
    result = provider.generate(BrainContext(mode="proactive"))
    assert result.speech == "fallback"
    assert provider.last_provider == "local"
    assert result.raw["_agcn_fallback"]["from"] == "api"

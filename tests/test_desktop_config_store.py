import json

from desktop.config_store import ConfigStore


def test_config_store_merges_defaults_and_strips_secrets(tmp_path):
    defaults = tmp_path / "defaults.json"
    user = tmp_path / "config.json"

    defaults.write_text(
        json.dumps({
            "brain": {
                "provider": "qwen_local",
                "ollama": {"model": "qwen3:4b"},
            },
            "audio": {"volume": 1.0},
        }),
        encoding="utf-8",
    )

    store = ConfigStore(path=user, defaults_path=defaults)
    saved = store.save({
        "brain": {
            "provider": "openai",
            "api_key": "NAO_PODE_SALVAR",
            "api": {
                "api_key_env": "OPENAI_API_KEY",
                "token": "SEGREDO",
            },
        },
        "audio": {"output_device": "CABLE Input"},
    })

    assert "api_key" not in saved["brain"]
    assert "token" not in saved["brain"]["api"]

    loaded = store.load()
    assert loaded["brain"]["provider"] == "openai"
    assert loaded["brain"]["ollama"]["model"] == "qwen3:4b"
    assert loaded["brain"]["api"]["api_key_env"] == "OPENAI_API_KEY"
    assert loaded["audio"]["volume"] == 1.0
    assert loaded["audio"]["output_device"] == "CABLE Input"


def test_builtin_defaults_use_local_voice_without_api(tmp_path):
    missing_defaults = tmp_path / "does-not-exist.json"
    store = ConfigStore(
        path=tmp_path / "config.json",
        defaults_path=missing_defaults,
    )
    loaded = store.load()
    assert loaded["brain"]["provider"] == "qwen_local"
    assert loaded["tts"]["provider"] == "qwen3_hq_auto"
    assert loaded["tts"]["profile"] == "female_fast"
    assert loaded["tts"]["speed"] == 1.28
    assert loaded["tts"]["qwen3_hq"]["expressive"] is True
    assert loaded["tts"]["qwen3_hq"]["expression_strength"] == 1.0
    assert loaded["tts"]["qwen3_hq"]["voice_style"] == "auto"
    assert loaded["tts"]["voice_style"] == "auto"
    assert loaded["tts"]["expression_strength"] == 1.0
    assert (
        loaded["tts"]["gemini"]["model"]
        == "gemini-3.8-flash-lite-tts"
    )
    assert loaded["tts"]["gemini"]["api_key_env"] == "GEMINI_API_KEY"

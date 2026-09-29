import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from desktop.main_window import MainWindow, VoiceAudioPage


class FakeController:
    def __init__(self):
        self.config = {
            "brain": {
                "provider": "qwen_local",
                "fallback_local": True,
                "ollama": {
                    "base_url": "http://127.0.0.1:11434",
                    "model": "qwen3:4b",
                },
                "api": {
                    "base_url": "https://api.openai.com/v1",
                    "model": "gpt-6-luna",
                },
            },
            "tts": {
                "provider": "qwen3_hq_auto",
                "profile": "female_fast",
                "speed": 1.28,
                "expression_strength": 1.0,
                "voice_style": "auto",
                "qwen3_hq": {
                    "expression_strength": 1.0,
                    "voice_style": "auto",
                },
                "gemini": {
                    "model": "gemini-3.8-flash-lite-tts",
                },
                "openai_live": {
                    "model": "gpt-live-1",
                    "mode": "strict_speech",
                },
            },
            "audio": {
                "output_device": "",
            },
        }
        self.closed = False

    def products(self):
        return []

    def snapshot(self):
        return {
            "monitoring": False,
            "status": "parado",
            "viewers": None,
            "likes": None,
            "active_product": {},
            "brain_provider": "Qwen local",
            "voice": {
                "active_provider": "Qwen3-TTS HQ / Vivian",
                "style_selection": "auto",
                "current_style": "sales_energy",
            },
            "presenter_mode": "interativo",
            "comments_paused_seconds": 0,
            "current_speech": None,
            "queue": [],
            "comments": [],
        }

    def api_key_saved(self):
        return False

    def gemini_key_saved(self):
        return False

    def close(self):
        self.closed = True


def _app():
    return QApplication.instance() or QApplication([])


def test_voice_audio_has_own_sidebar_page_and_dashboard_shortcut():
    _app()
    controller = FakeController()
    window = MainWindow(controller)

    assert [
        window.nav.item(index).text()
        for index in range(window.nav.count())
    ] == [
        "Dashboard",
        "Produto",
        "Voz e áudio",
        "Configurações",
    ]
    assert isinstance(window.pages.widget(2), VoiceAudioPage)

    window.dashboard.voice_advanced_btn.click()
    assert window.nav.currentRow() == 2
    assert window.pages.currentWidget() is window.voice_audio_page

    window.close()


def test_dashboard_voice_card_is_summary_of_saved_voice_configuration():
    _app()
    controller = FakeController()
    window = MainWindow(controller)

    window.dashboard.refresh(controller.snapshot())

    assert "Qwen3-TTS" in window.dashboard.voice_summary_engine.text()
    assert "Vivian" in window.dashboard.voice_summary_profile.text()
    assert window.dashboard.voice_summary_speed.text() == "1.28x"
    assert window.dashboard.voice_summary_expression.text() == "100%"
    assert "Automático" in window.dashboard.voice_summary_style.text()

    window.close()


def test_brain_settings_no_longer_own_voice_controls():
    _app()
    controller = FakeController()
    window = MainWindow(controller)

    assert not hasattr(window.settings_page, "voice_engine")
    assert hasattr(window.voice_audio_page, "voice_engine")
    assert hasattr(window.voice_audio_page, "expression_slider")
    assert hasattr(window.voice_audio_page, "voice_style_combo")
    assert hasattr(window.voice_audio_page, "voice_test_text")

    window.close()

import ast
from pathlib import Path


SOURCE_PATH = Path(__file__).resolve().parents[1] / "desktop" / "main_window.py"


def _source() -> str:
    return SOURCE_PATH.read_text(encoding="utf-8")


def _class_source(name: str) -> str:
    source = _source()
    tree = ast.parse(source)
    lines = source.splitlines()
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == name:
            return "\n".join(lines[node.lineno - 1:node.end_lineno])
    raise AssertionError(f"class {name} not found")


def test_desktop_source_is_valid_python():
    ast.parse(_source())


def test_voice_audio_has_own_sidebar_page():
    source = _source()
    main = _class_source("MainWindow")

    assert '"Dashboard",' in main
    assert '"Produto",' in main
    assert '"Voz e áudio",' in main
    assert '"Configurações",' in main
    assert "self.voice_audio_page = VoiceAudioPage(self.controller)" in main
    assert "self.pages.addWidget(self.voice_audio_page)" in main
    assert "self.voice_audio_page.load()" in main


def test_dashboard_has_compact_voice_summary_and_advanced_shortcut():
    dashboard = _class_source("DashboardPage")
    main = _class_source("MainWindow")

    assert (
        'group("Voz e áudio")' in dashboard
        or 'card("Voz e áudio"' in dashboard
    )
    assert "self.voice_summary_engine" in dashboard
    assert "self.voice_summary_profile" in dashboard
    assert "self.voice_summary_speed" in dashboard
    assert "self.voice_summary_expression" in dashboard
    assert "self.voice_summary_style" in dashboard
    assert 'QPushButton("Ajustes avançados →")' in dashboard
    assert "self.voice_advanced_btn.clicked.connect" in dashboard
    assert "open_voice_audio=lambda: self.nav.setCurrentRow(2)" in main


def test_voice_page_owns_complete_voice_controls():
    voice_page = _class_source("VoiceAudioPage")

    for expected in (
        "self.voice_engine",
        "self.gemini_model",
        "self.gemini_key",
        "self.openai_live_model",
        "self.openai_live_mode",
        "self.openai_key",
        "self.voice_profile",
        "self.speed_slider",
        "self.expression_slider",
        "self.voice_style_combo",
        "self.voice_test_text",
        "self.device",
        "self.test_voice_btn",
    ):
        assert expected in voice_page

    assert '"tts": {' in voice_page
    assert '"audio": {' in voice_page
    assert '"brain": {' not in voice_page


def test_general_settings_no_longer_own_voice_controls():
    settings = _class_source("SettingsPage")

    assert "self.brain_provider" in settings
    assert "self.test_brain_btn" in settings
    assert "self.doctor_btn" in settings
    assert "self.voice_engine" not in settings
    assert "self.expression_slider" not in settings
    assert "self.voice_style_combo" not in settings
    assert '"brain": {' in settings
    assert '"tts": {' not in settings
    assert '"audio": {' not in settings


def test_voice_patch_does_not_overwrite_hidden_engine_paths():
    voice_page = _class_source("VoiceAudioPage")

    # These settings are technical defaults already persisted by ConfigStore.
    # The page only patches what the user can actually edit.
    patch = voice_page[
        voice_page.index("    def _patch(self) -> dict:"):
        voice_page.index("    def _save(self) -> None:")
    ]
    assert '"pack_dir"' not in patch
    assert '"websocket_url"' not in patch
    assert '"models_base_url"' not in patch
    assert '"base_url"' not in patch
    assert '"timeout_seconds"' not in patch


def test_desktop_uses_polished_theme_and_maximized_startup():
    source = _source()
    main_path = SOURCE_PATH.parent / "main.py"
    main_source = main_path.read_text(encoding="utf-8")

    assert "APP_STYLESHEET" in source
    assert 'setObjectName("Sidebar")' in source
    assert 'setObjectName("SidebarNav")' in source
    assert 'setObjectName("PageRoot")' in source
    assert 'card("Status da LIVE"' in source
    assert 'card("Andamento da apresentação"' in source
    assert "showMaximized()" in main_source
    assert 'setStyle("Fusion")' in main_source

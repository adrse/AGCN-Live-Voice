from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.voice_profiles import list_voice_profiles
from desktop.app_controller import DesktopController


def heading(text: str, subtitle: str = "") -> tuple[QLabel, QLabel]:
    title = QLabel(text)
    title.setStyleSheet("font-size:26px;font-weight:700;color:#111827;")
    desc = QLabel(subtitle)
    desc.setWordWrap(True)
    desc.setStyleSheet("color:#6B7280;font-size:13px;")
    return title, desc


def group(title: str) -> QGroupBox:
    box = QGroupBox(title)
    box.setStyleSheet(
        "QGroupBox{font-weight:700;border:1px solid #E5E7EB;"
        "border-radius:10px;margin-top:12px;padding-top:12px;background:white;}"
        "QGroupBox::title{subcontrol-origin:margin;left:12px;padding:0 5px;}"
    )
    return box


class DashboardPage(QWidget):
    def __init__(self, controller: DesktopController) -> None:
        super().__init__()
        self.controller = controller

        layout = QVBoxLayout(self)
        title, desc = heading(
            "Dashboard",
            "Conecte a LIVE e acompanhe produto, Brain, comentários e fala atual.",
        )
        layout.addWidget(title)
        layout.addWidget(desc)

        connect_box = group("TikTok LIVE")
        row = QHBoxLayout(connect_box)
        self.username = QLineEdit()
        self.username.setPlaceholderText("@username")
        self.connect_btn = QPushButton("Conectar")
        self.stop_btn = QPushButton("Parar")
        self.stop_btn.setEnabled(False)
        row.addWidget(self.username, 1)
        row.addWidget(self.connect_btn)
        row.addWidget(self.stop_btn)
        layout.addWidget(connect_box)

        status_box = group("Status")
        grid = QGridLayout(status_box)
        self.status = QLabel("Parado")
        self.viewers = QLabel("—")
        self.likes = QLabel("—")
        self.product = QLabel("Nenhum")
        self.brain = QLabel("—")
        self.voice = QLabel("—")
        labels = [
            ("LIVE", self.status),
            ("Viewers", self.viewers),
            ("Curtidas", self.likes),
            ("Produto ativo", self.product),
            ("Brain", self.brain),
            ("Voz", self.voice),
        ]
        for index, (name, widget) in enumerate(labels):
            card = QLabel(name)
            card.setStyleSheet("color:#6B7280;font-size:12px;")
            grid.addWidget(card, index // 3 * 2, index % 3)
            widget.setStyleSheet("font-size:15px;font-weight:700;")
            grid.addWidget(widget, index // 3 * 2 + 1, index % 3)
        layout.addWidget(status_box)

        speech_box = group("Falando agora")
        speech_layout = QVBoxLayout(speech_box)
        self.speech = QTextEdit()
        self.speech.setReadOnly(True)
        self.speech.setFixedHeight(95)
        self.speech.setPlaceholderText("A fala atual aparecerá aqui.")
        speech_layout.addWidget(self.speech)
        layout.addWidget(speech_box)

        columns = QHBoxLayout()
        comments_box = group("Comentários recentes")
        comments_layout = QVBoxLayout(comments_box)
        self.comments = QListWidget()
        comments_layout.addWidget(self.comments)
        columns.addWidget(comments_box, 1)

        queue_box = group("Fila / decisão")
        queue_layout = QVBoxLayout(queue_box)
        self.queue = QListWidget()
        queue_layout.addWidget(self.queue)
        columns.addWidget(queue_box, 1)
        layout.addLayout(columns, 1)

        self.diagnostic = QLabel("")
        self.diagnostic.setWordWrap(True)
        self.diagnostic.setStyleSheet("color:#6B7280;font-size:12px;")
        layout.addWidget(self.diagnostic)

        self.connect_btn.clicked.connect(self._connect)
        self.stop_btn.clicked.connect(self._stop)

    def _connect(self) -> None:
        try:
            result = self.controller.start_live(
                self.username.text().strip()
            )
            if not result.get("ok", True):
                QMessageBox.warning(
                    self,
                    "Não foi possível iniciar",
                    result.get("message") or "Falha ao iniciar.",
                )
        except Exception as exc:
            QMessageBox.critical(self, "Erro", str(exc))

    def _stop(self) -> None:
        try:
            self.controller.stop_live()
        except Exception as exc:
            QMessageBox.critical(self, "Erro", str(exc))

    def refresh(self, data: dict) -> None:
        monitoring = bool(data.get("monitoring"))
        self.connect_btn.setEnabled(not monitoring)
        self.stop_btn.setEnabled(monitoring)

        self.status.setText(str(data.get("status") or "parado"))
        self.viewers.setText(
            str(data.get("viewers"))
            if data.get("viewers") is not None
            else "—"
        )
        self.likes.setText(
            str(data.get("likes"))
            if data.get("likes") is not None
            else "—"
        )

        active = data.get("active_product") or {}
        self.product.setText(active.get("name") or "Nenhum")
        self.brain.setText(str(data.get("brain_provider") or "—"))

        voice = data.get("voice") or {}
        self.voice.setText(
            str(voice.get("tts") or "Desativada")
        )

        current = data.get("current_speech") or {}
        self.speech.setPlainText(current.get("speech") or "")

        self.comments.clear()
        for item in reversed(data.get("comments") or []):
            user = item.get("user") or "—"
            text = item.get("text") or ""
            self.comments.addItem(f"{user}: {text}")

        self.queue.clear()
        for item in data.get("queue") or []:
            priority = item.get("priority", 0)
            text = item.get("speech") or item.get("comment") or ""
            self.queue.addItem(f"[{priority}] {text}")

        error = (
            data.get("presenter_worker_error")
            or voice.get("last_error")
            or data.get("error")
            or data.get("diagnostic")
            or ""
        )
        self.diagnostic.setText(str(error))


class ProductPage(QWidget):
    PERMANENT = [
        ("product_url", "Link do produto"),
        ("name", "Nome *"),
        ("brand", "Marca"),
        ("model", "Modelo"),
        ("category", "Categoria"),
        ("description", "Descrição"),
        ("key_benefits", "Benefícios"),
        ("problems_solved", "Problemas que resolve"),
        ("differentials", "Diferenciais"),
        ("included_items", "Itens inclusos"),
        ("compatibility", "Compatibilidade"),
        ("size_info", "Tamanho / medidas"),
        ("battery_info", "Bateria / autonomia"),
        ("usage_info", "Modo de uso"),
        ("warranty", "Garantia"),
        ("limitations", "Limitações"),
        ("additional_info", "Informações adicionais"),
        ("image_url", "URL da imagem"),
    ]
    LIVE = [
        ("regular_price", "Preço regular"),
        ("current_price", "Preço atual"),
        ("discount", "Desconto (%)"),
        ("stock", "Estoque"),
        ("shipping_info", "Frete / entrega"),
        ("coupon", "Cupom"),
        ("live_offer_text", "Texto da oferta"),
        ("promotion_note", "Observação promocional"),
    ]

    def __init__(self, controller: DesktopController) -> None:
        super().__init__()
        self.controller = controller
        self.current_id: str | None = None
        self.fields: dict[str, QLineEdit | QTextEdit] = {}

        root = QVBoxLayout(self)
        title, desc = heading(
            "Produto",
            "O produto ativo é a fonte da verdade para Qwen e API.",
        )
        root.addWidget(title)
        root.addWidget(desc)

        top = QHBoxLayout()
        self.product_combo = QComboBox()
        self.new_btn = QPushButton("Novo")
        self.activate_btn = QPushButton("Ativar")
        self.delete_btn = QPushButton("Excluir")
        top.addWidget(self.product_combo, 1)
        top.addWidget(self.new_btn)
        top.addWidget(self.activate_btn)
        top.addWidget(self.delete_btn)
        root.addLayout(top)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        stack = QVBoxLayout(container)

        permanent_box = group("Ficha do produto")
        permanent_form = QFormLayout(permanent_box)
        for field, label in self.PERMANENT:
            if field in {
                "description",
                "key_benefits",
                "problems_solved",
                "differentials",
                "included_items",
                "additional_info",
            }:
                widget = QTextEdit()
                widget.setFixedHeight(72)
            else:
                widget = QLineEdit()
            self.fields[field] = widget
            permanent_form.addRow(label, widget)
        stack.addWidget(permanent_box)

        live_box = group("Condições desta LIVE")
        live_form = QFormLayout(live_box)
        for field, label in self.LIVE:
            widget = QLineEdit()
            self.fields[field] = widget
            live_form.addRow(label, widget)
        self.live_offer = QCheckBox("Oferta ativa nesta LIVE")
        live_form.addRow("", self.live_offer)
        stack.addWidget(live_box)

        self.save_btn = QPushButton("Salvar e usar este produto")
        self.save_btn.setStyleSheet(
            "padding:12px;font-weight:700;background:#0061FF;color:white;"
            "border-radius:7px;"
        )
        stack.addWidget(self.save_btn)
        stack.addStretch(1)
        scroll.setWidget(container)
        root.addWidget(scroll, 1)

        self.product_combo.currentIndexChanged.connect(self._selected)
        self.new_btn.clicked.connect(self.clear_form)
        self.activate_btn.clicked.connect(self._activate)
        self.delete_btn.clicked.connect(self._delete)
        self.save_btn.clicked.connect(self._save)

        self.reload_products()

    @staticmethod
    def _get_text(widget) -> str:
        if isinstance(widget, QTextEdit):
            return widget.toPlainText().strip()
        return widget.text().strip()

    @staticmethod
    def _set_text(widget, value) -> None:
        text = "" if value is None else str(value)
        if isinstance(widget, QTextEdit):
            widget.setPlainText(text)
        else:
            widget.setText(text)

    def reload_products(self) -> None:
        products = self.controller.products()
        active_id = None
        self.product_combo.blockSignals(True)
        self.product_combo.clear()
        self.product_combo.addItem("Selecione um produto", None)
        for product in products:
            label = product.get("name") or "Sem nome"
            if product.get("active"):
                label += "  • ATIVO"
                active_id = product.get("id")
            self.product_combo.addItem(label, product.get("id"))
        self.product_combo.blockSignals(False)

        if active_id:
            index = self.product_combo.findData(active_id)
            if index >= 0:
                self.product_combo.setCurrentIndex(index)
                self.load_product(active_id)

    def clear_form(self) -> None:
        self.current_id = None
        self.product_combo.setCurrentIndex(0)
        for widget in self.fields.values():
            self._set_text(widget, "")
        self.live_offer.setChecked(False)

    def _selected(self, index: int) -> None:
        product_id = self.product_combo.itemData(index)
        if product_id:
            self.load_product(product_id)

    def load_product(self, product_id: str) -> None:
        product = next(
            (
                item
                for item in self.controller.products()
                if item.get("id") == product_id
            ),
            None,
        )
        if not product:
            return

        self.current_id = product_id
        live = product.get("live_conditions") or {}
        for field, _ in self.PERMANENT:
            self._set_text(self.fields[field], product.get(field))
        for field, _ in self.LIVE:
            self._set_text(self.fields[field], live.get(field))
        self.live_offer.setChecked(bool(live.get("live_offer")))

    def _payload(self) -> dict:
        payload = {
            field: self._get_text(widget)
            for field, widget in self.fields.items()
        }
        payload["live_offer"] = self.live_offer.isChecked()
        return payload

    def _save(self) -> None:
        try:
            product = self.controller.save_product(
                self._payload(),
                product_id=self.current_id,
                activate=True,
            )
            self.current_id = product.get("id")
            self.reload_products()
            QMessageBox.information(
                self,
                "Produto salvo",
                "Produto salvo e ativado para a apresentação.",
            )
        except Exception as exc:
            QMessageBox.critical(self, "Erro ao salvar", str(exc))

    def _activate(self) -> None:
        if not self.current_id:
            return
        try:
            self.controller.activate_product(self.current_id)
            self.reload_products()
        except Exception as exc:
            QMessageBox.critical(self, "Erro", str(exc))

    def _delete(self) -> None:
        if not self.current_id:
            return
        answer = QMessageBox.question(
            self,
            "Excluir produto",
            "Deseja excluir este produto?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.controller.delete_product(self.current_id)
            self.clear_form()
            self.reload_products()
        except Exception as exc:
            QMessageBox.critical(self, "Erro", str(exc))


class SettingsPage(QWidget):
    def __init__(self, controller: DesktopController) -> None:
        super().__init__()
        self.controller = controller

        root = QVBoxLayout(self)
        title, desc = heading(
            "Configurações",
            "Escolha Brain, voz e dispositivo. Secrets ficam fora do arquivo de configuração.",
        )
        root.addWidget(title)
        root.addWidget(desc)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        stack = QVBoxLayout(container)

        brain_box = group("Presenter Brain")
        brain_form = QFormLayout(brain_box)
        self.brain_provider = QComboBox()
        self.brain_provider.addItems(
            ["qwen_local", "openai", "openai_compatible"]
        )
        self.ollama_url = QLineEdit()
        self.ollama_model = QLineEdit()
        self.api_url = QLineEdit()
        self.api_model = QLineEdit()
        self.api_key = QLineEdit()
        self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key.setPlaceholderText(
            "Deixe vazio para manter a chave já salva"
        )
        self.fallback = QCheckBox("Usar Qwen local se API falhar")
        brain_form.addRow("Provider", self.brain_provider)
        brain_form.addRow("Ollama URL", self.ollama_url)
        brain_form.addRow("Modelo local", self.ollama_model)
        brain_form.addRow("API URL", self.api_url)
        brain_form.addRow("Modelo API", self.api_model)
        brain_form.addRow("Chave OpenAI", self.api_key)
        brain_form.addRow("", self.fallback)

        brain_actions = QHBoxLayout()
        self.test_brain_btn = QPushButton("Testar Brain")
        self.doctor_btn = QPushButton("Diagnóstico completo")
        self.key_status = QLabel("")
        brain_actions.addWidget(self.test_brain_btn)
        brain_actions.addWidget(self.doctor_btn)
        brain_actions.addWidget(self.key_status, 1)
        brain_form.addRow("", brain_actions)
        stack.addWidget(brain_box)

        voice_box = group("Voz e áudio")
        voice_form = QFormLayout(voice_box)

        self.voice_engine = QLabel(
            "AGCN Neural HQ — Qwen3-TTS 1.7B (offline, fallback Kokoro)"
        )
        self.voice_engine.setStyleSheet("font-weight:700;color:#111827;")

        self.voice_profile = QComboBox()
        for profile in list_voice_profiles():
            self.voice_profile.addItem(
                profile["label"],
                profile["id"],
            )

        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setMinimum(80)
        self.speed_slider.setMaximum(160)
        self.speed_slider.setSingleStep(1)
        self.speed_slider.setValue(128)
        self.speed_label = QLabel("1.28x")
        self.speed_slider.valueChanged.connect(
            lambda value: self.speed_label.setText(
                f"{value / 100:.2f}x"
            )
        )
        speed_row = QHBoxLayout()
        speed_row.addWidget(self.speed_slider, 1)
        speed_row.addWidget(self.speed_label)

        self.device = QComboBox()
        self.device.setEditable(True)
        self.refresh_devices_btn = QPushButton("Atualizar dispositivos")
        self.test_voice_btn = QPushButton("Testar voz")
        voice_form.addRow("Motor", self.voice_engine)
        voice_form.addRow("Perfil de voz", self.voice_profile)
        voice_form.addRow("Velocidade", speed_row)
        voice_form.addRow("Saída de áudio", self.device)

        voice_actions = QHBoxLayout()
        voice_actions.addWidget(self.refresh_devices_btn)
        voice_actions.addWidget(self.test_voice_btn)
        voice_form.addRow("", voice_actions)
        stack.addWidget(voice_box)

        self.save_btn = QPushButton("Salvar configurações")
        self.save_btn.setStyleSheet(
            "padding:12px;font-weight:700;background:#0061FF;color:white;"
            "border-radius:7px;"
        )
        stack.addWidget(self.save_btn)
        stack.addStretch(1)
        scroll.setWidget(container)
        root.addWidget(scroll, 1)

        self.save_btn.clicked.connect(self._save)
        self.refresh_devices_btn.clicked.connect(self._devices)
        self.test_brain_btn.clicked.connect(self._test_brain)
        self.doctor_btn.clicked.connect(self._doctor)
        self.test_voice_btn.clicked.connect(self._test_voice)

        self.load()

    def load(self) -> None:
        config = self.controller.config
        brain = config.get("brain") or {}
        ollama = brain.get("ollama") or {}
        api = brain.get("api") or {}
        tts = config.get("tts") or {}
        audio = config.get("audio") or {}

        self.brain_provider.setCurrentText(
            str(brain.get("provider") or "qwen_local")
        )
        self.ollama_url.setText(
            str(ollama.get("base_url") or "http://127.0.0.1:11434")
        )
        self.ollama_model.setText(
            str(ollama.get("model") or "qwen3:4b")
        )
        self.api_url.setText(
            str(api.get("base_url") or "https://api.openai.com/v1")
        )
        self.api_model.setText(str(api.get("model") or ""))
        self.fallback.setChecked(bool(brain.get("fallback_local", True)))

        profile_id = str(tts.get("profile") or "female_fast")
        profile_index = self.voice_profile.findData(profile_id)
        if profile_index >= 0:
            self.voice_profile.setCurrentIndex(profile_index)
        speed = float(tts.get("speed") or 1.28)
        self.speed_slider.setValue(
            max(80, min(160, int(round(speed * 100))))
        )
        self.device.setCurrentText(
            str(audio.get("output_device") or "")
        )
        self.key_status.setText(
            "API da inteligência salva"
            if self.controller.api_key_saved()
            else "API da inteligência opcional"
        )

    def _patch(self) -> dict:
        return {
            "brain": {
                "provider": self.brain_provider.currentText(),
                "fallback_local": self.fallback.isChecked(),
                "ollama": {
                    "base_url": self.ollama_url.text().strip(),
                    "model": self.ollama_model.text().strip(),
                },
                "api": {
                    "base_url": self.api_url.text().strip(),
                    "model": self.api_model.text().strip(),
                    "api_key_env": "OPENAI_API_KEY",
                },
            },
            "tts": {
                "provider": "qwen3_hq_auto",
                "profile": (
                    self.voice_profile.currentData()
                    or "female_fast"
                ),
                "speed": self.speed_slider.value() / 100.0,
                "voice_override": "",
                "qwen3_hq": {
                    "pack_dir": "",
                    "port": 18765,
                    "startup_timeout_seconds": 120,
                    "request_timeout_seconds": 60,
                },
                "kokoro": {
                    "model_dir": "",
                },
            },
            "audio": {
                "output_device": self.device.currentText().strip(),
            },
        }

    def _save(self) -> None:
        try:
            key = self.api_key.text()
            self.controller.save_settings(
                self._patch(),
                openai_key=key if key else None,
            )
            self.api_key.clear()
            self.load()
            QMessageBox.information(
                self,
                "Configurações",
                "Configurações salvas. O runtime foi recarregado.",
            )
        except Exception as exc:
            QMessageBox.critical(self, "Erro ao salvar", str(exc))

    def _devices(self) -> None:
        try:
            current = self.device.currentText()
            devices = self.controller.list_audio_devices()
            self.device.clear()
            self.device.addItem("")
            self.device.addItems(devices)
            if current:
                self.device.setCurrentText(current)
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Dispositivos de áudio",
                str(exc),
            )

    def _apply_settings_before_test(self) -> None:
        key = self.api_key.text()
        self.controller.save_settings(
            self._patch(),
            openai_key=key if key else None,
        )
        if key:
            self.api_key.clear()

    def _test_brain(self) -> None:
        try:
            self._apply_settings_before_test()
            ok, message = self.controller.brain_health()
            QMessageBox.information(
                self,
                "Teste do Brain",
                ("OK — " if ok else "Falhou — ") + message,
            )
        except Exception as exc:
            QMessageBox.critical(self, "Teste do Brain", str(exc))

    def _doctor(self) -> None:
        try:
            ok, message = self.controller.diagnostics()
            box = QMessageBox(self)
            box.setWindowTitle("Diagnóstico AGCN")
            box.setIcon(
                QMessageBox.Icon.Information
                if ok
                else QMessageBox.Icon.Warning
            )
            box.setText(
                "Pronto para teste de LIVE"
                if ok
                else "Há pendências no ambiente"
            )
            box.setDetailedText(message)
            box.setInformativeText(message)
            box.exec()
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Diagnóstico AGCN",
                str(exc),
            )

    def _test_voice(self) -> None:
        try:
            self._apply_settings_before_test()
            ok, message = self.controller.test_voice()
            QMessageBox.information(
                self,
                "Teste de voz",
                ("OK — " if ok else "Falhou — ") + message,
            )
        except Exception as exc:
            QMessageBox.critical(self, "Teste de voz", str(exc))


class MainWindow(QMainWindow):
    def __init__(
        self,
        controller: DesktopController | None = None,
    ) -> None:
        super().__init__()
        self.controller = controller or DesktopController()

        self.setWindowTitle(
            "AGCN Live Voice — Sua voz inteligente para vender ao vivo."
        )
        self.resize(1180, 780)

        root = QWidget()
        self.setCentralWidget(root)
        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)

        sidebar = QWidget()
        sidebar.setFixedWidth(210)
        sidebar.setStyleSheet("background:#0A0A0B;color:white;")
        side_layout = QVBoxLayout(sidebar)
        brand = QLabel("AGCN\nLive Voice")
        brand.setStyleSheet(
            "font-size:22px;font-weight:700;padding:12px;"
        )
        side_layout.addWidget(brand)

        self.nav = QListWidget()
        self.nav.setStyleSheet(
            "QListWidget{border:0;background:transparent;}"
            "QListWidget::item{padding:14px;}"
            "QListWidget::item:selected{background:#0061FF;}"
        )
        for name in ("Dashboard", "Produto", "Configurações"):
            self.nav.addItem(QListWidgetItem(name))
        side_layout.addWidget(self.nav, 1)

        self.pages = QStackedWidget()
        self.dashboard = DashboardPage(self.controller)
        self.product_page = ProductPage(self.controller)
        self.settings_page = SettingsPage(self.controller)
        self.pages.addWidget(self.dashboard)
        self.pages.addWidget(self.product_page)
        self.pages.addWidget(self.settings_page)

        self.nav.currentRowChanged.connect(self.pages.setCurrentIndex)
        self.nav.currentRowChanged.connect(self._page_changed)
        self.nav.setCurrentRow(0)

        outer.addWidget(sidebar)
        outer.addWidget(self.pages, 1)

        self.setStyleSheet(
            "QMainWindow{background:#F3F5F9;}"
            "QWidget{font-family:Segoe UI,Arial;font-size:13px;}"
            "QLineEdit,QTextEdit,QComboBox,QListWidget{"
            "border:1px solid #D1D5DB;border-radius:6px;padding:7px;background:white;}"
            "QPushButton{padding:8px 12px;border-radius:6px;"
            "border:1px solid #D1D5DB;background:white;}"
            "QPushButton:hover{background:#F3F4F6;}"
        )

        self.timer = QTimer(self)
        self.timer.setInterval(700)
        self.timer.timeout.connect(self.refresh)
        self.timer.start()
        self.refresh()

    def _page_changed(self, index: int) -> None:
        if index == 1:
            self.product_page.reload_products()
        elif index == 2:
            self.settings_page.load()

    def refresh(self) -> None:
        try:
            self.dashboard.refresh(self.controller.snapshot())
        except Exception as exc:
            self.dashboard.diagnostic.setText(str(exc))

    def closeEvent(self, event) -> None:
        try:
            self.controller.close()
        finally:
            event.accept()

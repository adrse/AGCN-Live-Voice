from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from desktop.output_window import OutputWindow


class PlaceholderPage(QWidget):
    def __init__(self, title: str, subtitle: str) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        heading = QLabel(title)
        heading.setStyleSheet("font-size: 26px; font-weight: 700;")
        desc = QLabel(subtitle)
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #6B7280; font-size: 14px;")
        layout.addWidget(heading)
        layout.addWidget(desc)
        layout.addStretch(1)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("AGCN Live Voice — Sua voz inteligente para vender ao vivo.")
        self.resize(1180, 760)
        self.output_window = OutputWindow()

        root = QWidget()
        self.setCentralWidget(root)
        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)

        sidebar = QWidget()
        sidebar.setFixedWidth(210)
        sidebar.setStyleSheet("background:#0A0A0B;color:white;")
        side_layout = QVBoxLayout(sidebar)
        brand = QLabel("AGCN\nLive Voice")
        brand.setStyleSheet("font-size:22px;font-weight:700;padding:12px;")
        side_layout.addWidget(brand)

        self.nav = QListWidget()
        self.nav.setStyleSheet("QListWidget{border:0;background:transparent;} QListWidget::item{padding:14px;} QListWidget::item:selected{background:#0061FF;}")
        for name in ("Dashboard", "Produto", "Configurações"):
            self.nav.addItem(QListWidgetItem(name))
        side_layout.addWidget(self.nav, 1)

        self.open_output = QPushButton("Abrir saída 9:16")
        self.open_output.clicked.connect(self.output_window.show)
        self.open_output.setStyleSheet("padding:12px;background:#0061FF;color:white;border:0;border-radius:8px;")
        side_layout.addWidget(self.open_output)

        self.pages = QStackedWidget()
        self.pages.addWidget(PlaceholderPage("Dashboard", "Conexão TikTok, produto ativo, presenter, comentários, fila e fala atual."))
        self.pages.addWidget(PlaceholderPage("Produto", "Cadastro manual do produto, condições da LIVE e playlist de vídeos."))
        self.pages.addWidget(PlaceholderPage("Configurações", "Qwen/API, voz, dispositivo de áudio, presenter e dados locais."))

        self.nav.currentRowChanged.connect(self.pages.setCurrentIndex)
        self.nav.setCurrentRow(0)

        outer.addWidget(sidebar)
        outer.addWidget(self.pages, 1)

        self.setStyleSheet("QMainWindow{background:#F3F5F9;} QWidget{font-family:Segoe UI, Arial;}")

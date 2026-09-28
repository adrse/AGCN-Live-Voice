from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class OutputWindow(QWidget):
    """Janela vertical limpa destinada à captura pelo TikTok LIVE Studio."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("AGCN Live Output")
        self.resize(540, 960)
        self.setMinimumSize(360, 640)
        self.setStyleSheet("background:#000000;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.video_placeholder = QLabel("AGCN Live Output\nVídeo do produto")
        self.video_placeholder.setAlignment(Qt.AlignCenter)
        self.video_placeholder.setStyleSheet("color:#6B7280;font-size:22px;")
        layout.addWidget(self.video_placeholder)

    def resizeEvent(self, event) -> None:  # noqa: N802
        # Mantém a intenção 9:16 sem forçar redimensionamento recursivo.
        return super().resizeEvent(event)

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() == Qt.Key_Escape and self.isFullScreen():
            self.showNormal()
            return
        super().keyPressEvent(event)

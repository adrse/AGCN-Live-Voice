from __future__ import annotations

import logging
import sys

from desktop.logging_setup import (
    install_exception_hook,
    setup_logging,
)


def main() -> int:
    setup_logging()
    install_exception_hook()

    try:
        from PySide6.QtWidgets import QApplication
        from desktop.main_window import MainWindow
    except Exception:
        logging.exception("Falha ao carregar interface desktop")
        return 1

    app = QApplication(sys.argv)
    app.setApplicationName("AGCN Live Voice")
    app.setOrganizationName("AGCN")
    app.setStyle("Fusion")

    window = MainWindow()
    window.showMaximized()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

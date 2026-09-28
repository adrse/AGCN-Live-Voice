from __future__ import annotations

import sys


def main() -> int:
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        print("PySide6 não instalado. Rode: pip install -r requirements-desktop.txt")
        return 1

    from desktop.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("AGCN Live Voice")
    app.setOrganizationName("AGCN")

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

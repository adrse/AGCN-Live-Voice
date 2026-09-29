from __future__ import annotations

import logging
import sys
import traceback
from datetime import datetime
from pathlib import Path

from desktop.config_store import app_data_dir


def log_dir() -> Path:
    path = app_data_dir() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def current_log_file() -> Path:
    return log_dir() / "agcn-live-voice.log"


def setup_logging() -> Path:
    path = current_log_file()
    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s | %(levelname)s | "
            "%(name)s | %(message)s"
        ),
        handlers=[
            logging.FileHandler(
                path,
                encoding="utf-8",
            )
        ],
        force=True,
    )
    logging.info(
        "AGCN Live Voice iniciado em %s",
        datetime.now().isoformat(timespec="seconds"),
    )
    return path


def install_exception_hook() -> None:
    def handle(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(
                exc_type,
                exc_value,
                exc_tb,
            )
            return

        text = "".join(
            traceback.format_exception(
                exc_type,
                exc_value,
                exc_tb,
            )
        )
        logging.critical(
            "Exceção não tratada:\n%s",
            text,
        )

        try:
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.critical(
                None,
                "Erro no AGCN Live Voice",
                (
                    "O programa encontrou um erro.\n\n"
                    f"Log salvo em:\n{current_log_file()}"
                ),
            )
        except Exception:
            pass

    sys.excepthook = handle

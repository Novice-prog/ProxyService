from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication

from proxy_access.ui.main_window import MainWindow


def run() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Proxy Access")
    app.setFont(QFont("Segoe UI", 10))
    app.setStyle("Fusion")

    styles = Path(__file__).parent / "ui" / "styles.qss"
    if styles.exists():
        app.setStyleSheet(styles.read_text(encoding="utf-8"))

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run())

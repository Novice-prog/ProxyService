from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)


class ActivateKeyDialog(QDialog):

    submitted = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Активация ключа")
        self.setModal(True)
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("Введите ключ активации")
        title.setObjectName("DialogTitle")
        layout.addWidget(title)

        hint = QLabel(
            "Ключ выдаётся после регистрации на сайте и приходит на email. "
            "Один ключ — одна активация."
        )
        hint.setObjectName("DialogHint")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.input = QLineEdit()
        self.input.setObjectName("KeyInput")
        self.input.setPlaceholderText("XXXX-XXXX-XXXX")
        self.input.setClearButtonEnabled(True)
        self.input.returnPressed.connect(self._on_submit)
        layout.addWidget(self.input)

        self.error_label = QLabel()
        self.error_label.setObjectName("DialogError")
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        layout.addWidget(self.error_label)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        self.progress.hide()
        layout.addWidget(self.progress)

        buttons = QHBoxLayout()
        buttons.setSpacing(10)

        self.paste_button = QPushButton("Вставить")
        self.paste_button.setObjectName("SecondaryButton")
        self.paste_button.clicked.connect(self._on_paste)

        self.cancel_button = QPushButton("Отмена")
        self.cancel_button.setObjectName("GhostButton")
        self.cancel_button.clicked.connect(self.reject)

        self.submit_button = QPushButton("Активировать")
        self.submit_button.setObjectName("PrimaryButton")
        self.submit_button.setDefault(True)
        self.submit_button.clicked.connect(self._on_submit)

        buttons.addWidget(self.paste_button)
        buttons.addStretch()
        buttons.addWidget(self.cancel_button)
        buttons.addWidget(self.submit_button)
        layout.addLayout(buttons)

    # ---------- API для родителя ----------

    def show_error(self, message: str) -> None:
        self.error_label.setText(message)
        self.error_label.show()

    def set_busy(self, busy: bool) -> None:
        self.progress.setVisible(busy)
        self.input.setEnabled(not busy)
        self.submit_button.setEnabled(not busy)
        self.paste_button.setEnabled(not busy)
        self.cancel_button.setEnabled(not busy)
        self.submit_button.setText("Активация…" if busy else "Активировать")

    def is_busy(self) -> bool:
        return self.progress.isVisible()

    # ---------- внутренние обработчики ----------

    def _on_paste(self) -> None:
        text = QGuiApplication.clipboard().text().strip()
        if text:
            self.input.setText(text)

    def _on_submit(self) -> None:
        if self.is_busy():
            return
        key = self.input.text().strip()
        if not key:
            self.show_error("Введите ключ активации.")
            return
        self.error_label.hide()
        self.submitted.emit(key)

    def keyPressEvent(self, event) -> None:  # noqa: N802
        # Esc закрывает только если не идёт запрос
        if event.key() == Qt.Key.Key_Escape and self.is_busy():
            return
        super().keyPressEvent(event)

    def closeEvent(self, event) -> None:  # noqa: N802
        # запрет закрытия крестиком во время запроса
        if self.is_busy():
            event.ignore()
            return
        super().closeEvent(event)

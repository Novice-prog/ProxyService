from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from proxy_access.config import ProxyInfo


STATUS_LABELS = {
    "connected": "ПОДКЛЮЧЁН",
    "disconnected": "НЕ ПОДКЛЮЧЁН",
    "no_free_vms": "НЕТ СВОБОДНЫХ",
    "error": "ОШИБКА",
    "loading": "ОЖИДАНИЕ…",
}

STATUS_HINTS = {
    "connected": "Прокси-сервер активен. Кликните, чтобы отключиться.",
    "disconnected": "Кликните, чтобы подключиться к свободному прокси.",
    "no_free_vms": "Все прокси заняты. Кликните, чтобы повторить попытку.",
    "error": "Соединение с сервером прервано",
    "loading": "Связываемся с сервером…",
}

CLICKABLE_STATES = {"connected", "disconnected", "no_free_vms"}


class ConnectionPanel(QFrame):
    toggle_requested = pyqtSignal(bool)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("ConnectionPanel")

        self._current_state: str = "disconnected"
        self._session_available: bool = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.status_button = QPushButton("On/Off")
        self.status_button.setObjectName("StatusOrb")
        self.status_button.setFixedSize(220, 220)
        self.status_button.setProperty("state", "disconnected")
        self.status_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.status_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.status_button.clicked.connect(self._on_clicked)

        layout.addWidget(self.status_button, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.status_label = QLabel(STATUS_LABELS["disconnected"])
        self.status_label.setObjectName("StatusLabel")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        self.hint_label = QLabel(STATUS_HINTS["disconnected"])
        self.hint_label.setObjectName("StatusHint")
        self.hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hint_label.setWordWrap(True)
        layout.addWidget(self.hint_label)

        layout.addSpacing(20)

        info = QFrame()
        info.setObjectName("ConnectionInfo")
        info_layout = QVBoxLayout(info)
        info_layout.setContentsMargins(16, 12, 16, 12)
        info_layout.setSpacing(4)
        info_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.vm_label = QLabel("—")
        self.vm_label.setObjectName("ConnectionVm")
        self.vm_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.endpoint_label = QLabel("—")
        self.endpoint_label.setObjectName("ConnectionEndpoint")
        self.endpoint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        info_layout.addWidget(self.vm_label)
        info_layout.addWidget(self.endpoint_label)
        layout.addWidget(info)

        layout.addStretch()

        self._refresh_clickability()

    def set_session_available(self, available: bool) -> None:
        self._session_available = available
        self._refresh_clickability()

    def set_status(
        self,
        *,
        status: str,
        vm_id: int | None = None,
        proxy: ProxyInfo | None = None,
        custom_message: str | None = None,
    ) -> None:
        state = status if status in STATUS_LABELS else "error"
        self._current_state = state

        self.status_button.setProperty("state", state)
        self.status_button.style().unpolish(self.status_button)
        self.status_button.style().polish(self.status_button)

        self.status_label.setText(STATUS_LABELS[state])
        self.hint_label.setText(custom_message or STATUS_HINTS[state])

        if proxy is not None:
            self.vm_label.setText(f"VM #{vm_id}" if vm_id else "—")
            self.endpoint_label.setText(f"{proxy.protocol.upper()} · {proxy.host}:{proxy.port}")
        elif state == "disconnected":
            self.vm_label.setText("—")
            self.endpoint_label.setText("—")

        self._refresh_clickability()

    def show_loading(self, message: str | None = None) -> None:
        self.set_status(status="loading", custom_message=message)

    def _refresh_clickability(self) -> None:
        clickable = (
            self._session_available
            and self._current_state in CLICKABLE_STATES
        )
        self.status_button.setEnabled(clickable)
        self.status_button.setCursor(
            Qt.CursorShape.PointingHandCursor
            if clickable
            else Qt.CursorShape.ArrowCursor
        )

    def _on_clicked(self) -> None:
        wants_connect = self._current_state != "connected"
        self.toggle_requested.emit(wants_connect)

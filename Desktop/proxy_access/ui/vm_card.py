from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

from proxy_access.config import ProxyInfo


class VmCard(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("VmCard")
        self.setProperty("selected", True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(14)

        self.dot = QLabel()
        self.dot.setObjectName("VmDot")
        self.dot.setFixedSize(10, 10)
        layout.addWidget(self.dot, alignment=Qt.AlignmentFlag.AlignVCenter)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)

        self.title = QLabel("Нет назначенной VM")
        self.title.setObjectName("VmTitle")

        self.subtitle = QLabel("Активируйте ключ через «+»")
        self.subtitle.setObjectName("VmSubtitle")

        text_col.addWidget(self.title)
        text_col.addWidget(self.subtitle)
        layout.addLayout(text_col, stretch=1)

        self.region = QLabel("—")
        self.region.setObjectName("VmRegion")
        layout.addWidget(self.region, alignment=Qt.AlignmentFlag.AlignVCenter)

    def set_vm(
        self,
        *,
        vm_id: int | None,
        proxy: ProxyInfo | None,
        is_connected: bool = False,
    ) -> None:
        if vm_id and proxy:
            self.title.setText(f"VM #{vm_id}")
            self.subtitle.setText(f"{proxy.protocol.upper()} · {proxy.host}:{proxy.port}")
            self.region.setText(proxy.protocol.upper())
            self.setProperty("state", "connected" if is_connected else "idle")
        else:
            self.title.setText("Нет назначенной VM")
            self.subtitle.setText("Активируйте ключ через «+»")
            self.region.setText("—")
            self.setProperty("state", "empty")

        self.style().unpolish(self)
        self.style().polish(self)
        self.dot.style().unpolish(self.dot)
        self.dot.style().polish(self.dot)

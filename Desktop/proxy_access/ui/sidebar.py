from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QFrame, QToolButton, QVBoxLayout


class SidebarButton(QToolButton):
    def __init__(self, glyph: str, tooltip: str) -> None:
        super().__init__()
        self.setObjectName("SidebarButton")
        self.setText(glyph)
        self.setToolTip(tooltip)
        self.setCheckable(False)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(56, 56)
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)


class Sidebar(QFrame):
    add_clicked = pyqtSignal()
    reset_clicked = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("Sidebar")
        self.setFixedWidth(72)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 16, 8, 16)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Действия сверху
        self.add_button = SidebarButton("+", "Активировать ключ")
        self.add_button.clicked.connect(self.add_clicked.emit)

        self.servers_button = SidebarButton("◉", "Серверы")
        self.servers_button.setProperty("active", True)

        layout.addWidget(self.add_button, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self.servers_button, alignment=Qt.AlignmentFlag.AlignHCenter)

        layout.addStretch()

        # Снизу — выход (сброс сессии)
        self.reset_button = SidebarButton("⎋", "Сбросить сессию")
        self.reset_button.clicked.connect(self.reset_clicked.emit)
        layout.addWidget(self.reset_button, alignment=Qt.AlignmentFlag.AlignHCenter)

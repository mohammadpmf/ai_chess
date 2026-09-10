"""Player information card widget."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)


class PlayerCard(QFrame):
    """A card displaying player name, side, and turn indicator."""

    def __init__(
        self,
        name: str,
        side_text: str,
        symbol: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("PlayerCard")
        self.setProperty("active", False)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(12)

        self.avatar = QLabel(symbol)
        self.avatar.setFixedSize(44, 44)
        self.avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.avatar.setStyleSheet(
            "background-color: #1a1a1a; border-radius: 22px; "
            "font-size: 26px; color: #e8e8e8;"
        )
        layout.addWidget(self.avatar)

        info = QVBoxLayout()
        info.setSpacing(2)
        self.name_label = QLabel(name)
        self.name_label.setObjectName("PlayerName")
        self.side_label = QLabel(side_text)
        self.side_label.setObjectName("PlayerSide")
        info.addWidget(self.name_label)
        info.addWidget(self.side_label)
        layout.addLayout(info, 1)

        self.turn_label = QLabel("")
        self.turn_label.setObjectName("TurnIndicator")
        self.turn_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        layout.addWidget(self.turn_label)

    def set_active(self, active: bool, text: str = "") -> None:
        self.setProperty("active", active)
        self.style().unpolish(self)
        self.style().polish(self)
        self.turn_label.setText(text if active else "")

    def set_thinking(self, thinking: bool) -> None:
        if thinking:
            self.turn_label.setText("● Thinking…")
        else:
            self.turn_label.setText("")

"""Move history list widget with scrollable SAN display."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)


class MoveHistoryWidget(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("SectionFrame")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 12)
        layout.setSpacing(8)

        title = QLabel("MOVE HISTORY")
        title.setObjectName("SectionTitle")
        layout.addWidget(title)

        self.list_widget = QListWidget()
        self.list_widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.list_widget.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        layout.addWidget(self.list_widget, 1)

    def update_from_history(self, history: list[tuple[object, object, str]]) -> None:
        self.list_widget.clear()
        i = 0
        move_num = 1
        while i < len(history):
            white_san = history[i][2]
            black_san = history[i + 1][2] if i + 1 < len(history) else ""
            text = f"{move_num:>3}.  {white_san:<9}{black_san}"
            item = QListWidgetItem(text)
            self.list_widget.addItem(item)
            i += 2
            move_num += 1
        if self.list_widget.count() > 0:
            self.list_widget.scrollToBottom()

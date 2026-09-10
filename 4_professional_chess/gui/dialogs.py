"""Custom dialogs: game mode picker, promotion picker, and game over."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from chess_engine import Color, PieceType
from gui.game_mode import GameMode
from gui.resources import get_piece_pixmap


# ======================================================================
# Game mode / side selection
# ======================================================================
class GameModeDialog(QDialog):
    """Modal dialog that asks the user which game mode and side to start.

    After exec(), read:
      - self.selected_mode: GameMode | None
      - self.selected_color: Color | None
        (only meaningful when selected_mode is COMPUTER; None for TWO_PLAYERS)
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("New Game")
        self.setModal(True)
        self.setFixedSize(560, 320)
        self.selected_mode: Optional[GameMode] = None
        self.selected_color: Optional[Color] = None
        self._chosen: Optional[tuple[GameMode, Optional[Color]]] = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(16)

        title = QLabel("SELECT GAME MODE")
        title.setObjectName("Title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("Choose how you want to play")
        subtitle.setObjectName("Subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        # Three option cards
        options_row = QHBoxLayout()
        options_row.setSpacing(10)

        self._white_card = self._make_option_card(
            "♔",
            "Play as White",
            "You move first",
            (GameMode.COMPUTER, Color.WHITE),
        )
        self._black_card = self._make_option_card(
            "♚",
            "Play as Black",
            "Computer moves first",
            (GameMode.COMPUTER, Color.BLACK),
        )
        self._two_player_card = self._make_option_card(
            "♟♟",
            "Two Players",
            "Human vs Human",
            (GameMode.TWO_PLAYERS, None),
        )
        options_row.addWidget(self._white_card, 1)
        options_row.addWidget(self._black_card, 1)
        options_row.addWidget(self._two_player_card, 1)
        layout.addLayout(options_row, 1)

        # Start / Cancel
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setMinimumHeight(38)
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)

        self.start_btn = QPushButton("Start Game")
        self.start_btn.setObjectName("PrimaryButton")
        self.start_btn.setMinimumHeight(38)
        self.start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_btn.setEnabled(False)
        self.start_btn.clicked.connect(self._on_start)

        btn_row.addWidget(cancel_btn, 1)
        btn_row.addWidget(self.start_btn, 2)
        layout.addLayout(btn_row)

        self._refresh_cards()

    def _make_option_card(
        self,
        icon: str,
        title: str,
        subtitle: str,
        choice: tuple[GameMode, Optional[Color]],
    ) -> QFrame:
        card = QFrame()
        card.setObjectName("PlayerCard")
        card.setProperty("active", False)
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        card.mousePressEvent = lambda _e, c=choice: self._pick(c)  # type: ignore[assignment]

        cl = QVBoxLayout(card)
        cl.setContentsMargins(10, 14, 10, 14)
        cl.setSpacing(6)

        icon_lbl = QLabel(icon)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet("font-size: 26px; color: #e8e8e8;")

        t = QLabel(title)
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t.setStyleSheet("color: #ffffff; font-size: 13px; font-weight: 700;")

        s = QLabel(subtitle)
        s.setAlignment(Qt.AlignmentFlag.AlignCenter)
        s.setWordWrap(True)
        s.setStyleSheet("color: #9a9a9a; font-size: 10px;")

        cl.addWidget(icon_lbl)
        cl.addWidget(t)
        cl.addWidget(s)
        return card

    def _pick(self, choice: tuple[GameMode, Optional[Color]]) -> None:
        self._chosen = choice
        self._refresh_cards()

    def _refresh_cards(self) -> None:
        for card, choice in (
            (self._white_card, (GameMode.COMPUTER, Color.WHITE)),
            (self._black_card, (GameMode.COMPUTER, Color.BLACK)),
            (self._two_player_card, (GameMode.TWO_PLAYERS, None)),
        ):
            active = self._chosen == choice
            card.setProperty("active", active)
            card.style().unpolish(card)
            card.style().polish(card)
        self.start_btn.setEnabled(self._chosen is not None)

    def _on_start(self) -> None:
        if self._chosen is None:
            return
        mode, color = self._chosen
        self.selected_mode = mode
        self.selected_color = color
        self.accept()

    def keyPressEvent(self, event):  # noqa: N802
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._on_start()
            return
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
            return
        super().keyPressEvent(event)


# ======================================================================
# Promotion
# ======================================================================
class PromotionDialog(QDialog):
    """Modal dialog for pawn promotion selection."""

    def __init__(self, color: Color, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Pawn Promotion")
        self.setModal(True)
        self.setFixedSize(380, 200)
        self.selected: Optional[PieceType] = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        title = QLabel("Choose a piece")
        title.setObjectName("Title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("Your pawn has reached the last rank")
        subtitle.setObjectName("Subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        row = QHBoxLayout()
        row.setSpacing(10)
        row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        for pt in (
            PieceType.QUEEN,
            PieceType.ROOK,
            PieceType.BISHOP,
            PieceType.KNIGHT,
        ):
            btn = self._make_piece_button(pt, color)
            row.addWidget(btn)

        layout.addLayout(row)

    def _make_piece_button(self, piece_type: PieceType, color: Color) -> QPushButton:
        btn = QPushButton()
        btn.setFixedSize(72, 72)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #2a2a2a;
                border: 1px solid #3d3d3d;
                border-radius: 10px;
            }
            QPushButton:hover {
                background-color: #3a3a3a;
                border-color: #4a90d9;
            }
            QPushButton:pressed {
                background-color: #4a90d9;
            }
            """)
        pixmap = get_piece_pixmap(piece_type, color, 56)
        btn.setIcon(pixmap)
        btn.setIconSize(pixmap.size())
        btn.clicked.connect(lambda: self._choose(piece_type))
        return btn

    def _choose(self, pt: PieceType) -> None:
        self.selected = pt
        self.accept()


# ======================================================================
# Game over
# ======================================================================
class GameOverDialog(QDialog):
    """Modal dialog shown when the game ends."""

    new_game_requested = Signal()
    exit_requested = Signal()

    def __init__(
        self,
        title: str,
        message: str,
        is_win: bool,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Game Over")
        self.setModal(True)
        self.setFixedSize(420, 240)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(12)

        header = QLabel(title)
        header.setObjectName("Title")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet(
            f"color: {'#4caf50' if is_win else '#e57373'}; "
            "font-size: 26px; font-weight: 800; letter-spacing: 2px;"
        )
        layout.addWidget(header)

        msg = QLabel(message)
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg.setWordWrap(True)
        msg.setStyleSheet("color: #b0b0b0; font-size: 14px;")
        layout.addWidget(msg, 1)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        new_btn = QPushButton("New Game")
        new_btn.setObjectName("PrimaryButton")
        new_btn.setMinimumHeight(40)
        new_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        new_btn.clicked.connect(self._on_new_game)

        exit_btn = QPushButton("Exit")
        exit_btn.setMinimumHeight(40)
        exit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        exit_btn.clicked.connect(self._on_exit)

        btn_row.addWidget(new_btn, 1)
        btn_row.addWidget(exit_btn, 1)
        layout.addLayout(btn_row)

    def _on_new_game(self) -> None:
        self.new_game_requested.emit()
        self.accept()

    def _on_exit(self) -> None:
        self.exit_requested.emit()
        self.accept()

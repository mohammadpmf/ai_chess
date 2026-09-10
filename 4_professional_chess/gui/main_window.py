"""Main application window - chess dashboard.

Supports three start choices:
  - COMPUTER + WHITE human: human plays White, AI plays Black (board flipped)
  - COMPUTER + BLACK human: human plays Black, AI plays White (default view)
  - TWO_PLAYERS:            both sides are human (default view)
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from chess_engine import ChessGame, Color, GameStatus, Move
from chess_ai import ChessAI
from gui.ai_process import AIProcessController
from gui.chess_board import ChessBoardWidget
from gui.dialogs import GameModeDialog, GameOverDialog, PromotionDialog
from gui.game_mode import GameMode
from gui.move_history import MoveHistoryWidget
from gui.player_panel import PlayerCard


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Chess")
        self.resize(1180, 800)
        self.setMinimumSize(940, 640)

        self.game = ChessGame()
        self.ai = ChessAI("medium")
        self.game_over = False

        # Game configuration — set by the mode dialog before each game.
        self.game_mode: GameMode = GameMode.COMPUTER
        self.human_color: Color = Color.BLACK  # only used in COMPUTER mode

        # AI process controller (only used in COMPUTER mode).
        self._ai = AIProcessController()
        self._ai_timer = QTimer(self)
        self._ai_timer.setInterval(50)
        self._ai_timer.timeout.connect(self._poll_ai)
        self._thinking_started: float = 0.0
        self._last_ai_info: str = ""

        self._build_ui()
        self._apply_stylesheet()
        self._sync_board()
        self._update_sidebar()

        QTimer.singleShot(0, self._prompt_new_game)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        central = QWidget()
        central.setObjectName("CentralWidget")

        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ---------- Board area ----------
        board_container = QFrame()
        board_container.setStyleSheet("background-color: #1a1a1a;")
        board_layout = QVBoxLayout(board_container)
        board_layout.setContentsMargins(24, 24, 24, 24)

        self.board = ChessBoardWidget(self.game)
        self.board.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.board.move_requested.connect(self._on_user_move)
        self.board.promotion_requested.connect(self._on_promotion_request)
        board_layout.addWidget(self.board, 1)

        root.addWidget(board_container, 1)

        # ---------- Sidebar ----------
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(340)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(18, 20, 18, 20)
        side_layout.setSpacing(14)

        title = QLabel("CHESS")
        title.setObjectName("Title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        side_layout.addWidget(title)

        self.mode_subtitle = QLabel("Select a game mode to start")
        self.mode_subtitle.setObjectName("Subtitle")
        self.mode_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        side_layout.addWidget(self.mode_subtitle)

        # Player cards (top = White side, bottom = Black side, always).
        self.top_card = PlayerCard("Computer", "White", "♔")
        side_layout.addWidget(self.top_card)

        vs = QLabel("VS")
        vs.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vs.setStyleSheet("color: #5a5a5a; font-size: 11px; font-weight: 700;")
        side_layout.addWidget(vs)

        self.bottom_card = PlayerCard("You", "Black", "♚")
        side_layout.addWidget(self.bottom_card)

        # Difficulty selector (hidden in two-players mode)
        self.diff_frame = QFrame()
        self.diff_frame.setObjectName("SectionFrame")
        diff_layout = QVBoxLayout(self.diff_frame)
        diff_layout.setContentsMargins(12, 10, 12, 12)
        diff_layout.setSpacing(8)

        diff_title = QLabel("DIFFICULTY")
        diff_title.setObjectName("SectionTitle")
        diff_layout.addWidget(diff_title)

        self.diff_combo = QComboBox()
        self.diff_combo.addItems(["Easy", "Medium", "Hard"])
        self.diff_combo.setCurrentText("Medium")
        self.diff_combo.currentTextChanged.connect(self._on_difficulty_change)
        diff_layout.addWidget(self.diff_combo)

        side_layout.addWidget(self.diff_frame)

        # Move history
        self.move_history = MoveHistoryWidget()
        side_layout.addWidget(self.move_history, 1)

        # Buttons
        btn_grid = QVBoxLayout()
        btn_grid.setSpacing(8)

        row1 = QHBoxLayout()
        row1.setSpacing(8)

        self.new_btn = QPushButton("New Game")
        self.new_btn.setObjectName("PrimaryButton")
        self.new_btn.setMinimumHeight(38)
        self.new_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.new_btn.clicked.connect(self._on_new_game)

        self.undo_btn = QPushButton("Undo")
        self.undo_btn.setObjectName("SuccessButton")
        self.undo_btn.setMinimumHeight(38)
        self.undo_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.undo_btn.clicked.connect(self._on_undo)

        row1.addWidget(self.new_btn, 1)
        row1.addWidget(self.undo_btn, 1)
        btn_grid.addLayout(row1)

        row2 = QHBoxLayout()
        row2.setSpacing(8)

        self.resign_btn = QPushButton("Resign")
        self.resign_btn.setObjectName("DangerButton")
        self.resign_btn.setMinimumHeight(38)
        self.resign_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.resign_btn.clicked.connect(self._on_resign)

        self.exit_btn = QPushButton("Exit")
        self.exit_btn.setMinimumHeight(38)
        self.exit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.exit_btn.clicked.connect(self.close)

        row2.addWidget(self.resign_btn, 1)
        row2.addWidget(self.exit_btn, 1)
        btn_grid.addLayout(row2)

        side_layout.addLayout(btn_grid)

        root.addWidget(sidebar)

        # ---------- Status bar ----------
        status = QFrame()
        status.setObjectName("StatusBar")
        status.setFixedHeight(52)
        status_layout = QHBoxLayout(status)
        status_layout.setContentsMargins(24, 8, 24, 8)

        self.status_text = QLabel("Welcome")
        self.status_text.setObjectName("StatusText")

        self.status_sub = QLabel("")
        self.status_sub.setObjectName("StatusSub")
        self.status_sub.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )

        status_layout.addWidget(self.status_text, 1)
        status_layout.addWidget(self.status_sub)

        wrapper = QWidget()
        wrapper.setObjectName("CentralWidget")
        wl = QVBoxLayout(wrapper)
        wl.setContentsMargins(0, 0, 0, 0)
        wl.setSpacing(0)
        wl.addWidget(central, 1)
        wl.addWidget(status)
        self.setCentralWidget(wrapper)

    def _apply_stylesheet(self) -> None:
        qss_path = Path(__file__).resolve().parent.parent / "styles" / "dark_theme.qss"
        if qss_path.exists():
            self.setStyleSheet(qss_path.read_text(encoding="utf-8"))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _ai_color(self) -> Optional[Color]:
        """The color played by AI, or None in two-players mode."""
        if self.game_mode.is_two_players:
            return None
        return self.human_color.opposite

    def _is_human_turn(self) -> bool:
        side = self.game.state.side_to_move
        if self.game_mode.is_two_players:
            return True
        return side is self.human_color

    def _cancel_ai(self) -> None:
        self._ai.cancel()
        self._ai_timer.stop()
        self._last_ai_info = ""

    def _apply_board_orientation(self) -> None:
        """Flip the board so White sits at the bottom of the screen.

        Two-players mode: White at bottom.
        Computer mode:    Human's color at bottom.
        """
        if self.game_mode.is_two_players:
            self.board.set_flipped(True)
        else:
            self.board.set_flipped(self.human_color is Color.WHITE)

    # ------------------------------------------------------------------
    # State sync
    # ------------------------------------------------------------------
    def _sync_board(self) -> None:
        self.board.set_last_move(
            self.game.history[-1][1] if self.game.history else None
        )
        interactive = (
            not self.game_over and self._is_human_turn() and not self._ai.is_busy()
        )
        self.board.set_interactive(interactive)
        self.board.update()

    def _update_sidebar(self) -> None:
        st = self.game.status
        side = self.game.state.side_to_move
        busy = self._ai.is_busy()

        # Subtitle reflects current mode
        if self.game_mode.is_computer:
            human_side = "White" if self.human_color is Color.WHITE else "Black"
            self.mode_subtitle.setText(
                f"Computer ({self.diff_combo.currentText()}) vs You ({human_side})"
            )
        else:
            self.mode_subtitle.setText("Two Players — Human vs Human")

        # Show/hide difficulty
        self.diff_frame.setVisible(self.game_mode.is_computer)

        # Player cards
        if self.game_over:
            self.top_card.set_active(False)
            self.bottom_card.set_active(False)
        else:
            if self.game_mode.is_two_players:
                self.top_card.set_active(side is Color.WHITE, "● To move")
                self.bottom_card.set_active(side is Color.BLACK, "● To move")
            else:
                white_is_ai = self.human_color is Color.BLACK
                if white_is_ai:
                    self.top_card.set_active(
                        side is Color.WHITE,
                        "● Thinking…" if busy else "● To move",
                    )
                    self.bottom_card.set_active(side is Color.BLACK, "● Your turn")
                else:
                    self.top_card.set_active(side is Color.WHITE, "● Your turn")
                    self.bottom_card.set_active(
                        side is Color.BLACK,
                        "● Thinking…" if busy else "● To move",
                    )

        # Status text
        if self.game_over:
            self.status_text.setText("Game Over")
            self.status_sub.setText(self.game.result_text())
        elif busy:
            self.status_text.setText("Computer is thinking…")
            self.status_sub.setText(self._last_ai_info or "Please wait")
        else:
            if side is Color.WHITE:
                self.status_text.setText("White's turn")
            else:
                self.status_text.setText("Black's turn")
            if st is GameStatus.CHECK:
                self.status_sub.setText("Check!")
            else:
                self.status_sub.setText("")

        # Move history
        self.move_history.update_from_history(self.game.history)

        # Undo availability
        if self.game_mode.is_two_players:
            self.undo_btn.setEnabled(not self.game_over and len(self.game.history) >= 1)
        else:
            human_side = self.human_color
            can_undo_single = (
                not self.game_over
                and side is human_side.opposite
                and len(self.game.history) >= 1
            )
            can_undo_pair = (
                not self.game_over
                and side is human_side
                and len(self.game.history) >= 2
            )
            self.undo_btn.setEnabled(can_undo_single or can_undo_pair)

        self.resign_btn.setEnabled(not self.game_over)
        self.new_btn.setEnabled(True)

    # ------------------------------------------------------------------
    # Player card labels (mode-dependent)
    # ------------------------------------------------------------------
    def _apply_mode_labels(self) -> None:
        # Sidebar semantics:
        #   top_card = the side whose home rank is at the top of the board
        #   bottom_card = the side whose home rank is at the bottom.
        # This follows the board orientation, so labels stay consistent with
        # what the user actually sees on screen.
        bottom_color = (
            Color.WHITE
            if self.board.is_flipped() or self.game_mode.is_two_players and False
            else Color.BLACK
        )
        # Two-players keeps Black at bottom; COMPUTER flips when human is White.
        if self.game_mode.is_two_players:
            bottom_color = Color.BLACK
        else:
            bottom_color = self.human_color

        top_color = bottom_color.opposite

        def describe(color: Color) -> tuple[str, str]:
            if self.game_mode.is_two_players:
                if color is Color.WHITE:
                    return ("White Player", "White")
                return ("Black Player", "Black")
            if color is self.human_color:
                return ("You", "White" if color is Color.WHITE else "Black")
            return ("Computer", "White" if color is Color.WHITE else "Black")

        top_name, top_side = describe(top_color)
        bot_name, bot_side = describe(bottom_color)

        self.top_card.name_label.setText(top_name)
        self.top_card.side_label.setText(top_side)
        self.bottom_card.name_label.setText(bot_name)
        self.bottom_card.side_label.setText(bot_side)

    # ------------------------------------------------------------------
    # AI scheduling (only in COMPUTER mode)
    # ------------------------------------------------------------------
    def _schedule_ai_move(self, delay_ms: int = 100) -> None:
        if self.game_mode.is_two_players:
            return
        if self.game_over:
            return
        if self.game.state.side_to_move is not self._ai_color():
            return
        QTimer.singleShot(delay_ms, self._start_ai_move)

    def _start_ai_move(self) -> None:
        if self.game_mode.is_two_players:
            return
        if self.game_over or self.game.state.side_to_move is not self._ai_color():
            return
        if self._ai.is_busy():
            return

        self._thinking_started = time.perf_counter()
        self._last_ai_info = ""
        difficulty = self.diff_combo.currentText().lower()
        self._ai.start(self.game, difficulty)
        self._ai_timer.start()
        self._sync_board()
        self._update_sidebar()

    def _poll_ai(self) -> None:
        if self.game_mode.is_two_players:
            self._cancel_ai()
            self._sync_board()
            self._update_sidebar()
            return

        result = self._ai.try_fetch()

        if result is None:
            if not self._ai.is_busy():
                self._ai_timer.stop()
                self._sync_board()
                self._update_sidebar()
            else:
                elapsed = time.perf_counter() - self._thinking_started
                self._last_ai_info = f"Elapsed {elapsed:.1f}s"
                self._update_sidebar()
            return

        self._ai_timer.stop()

        if result.move is None:
            self._check_game_end()
            return

        if self.game_over or self.game.state.side_to_move is not self._ai_color():
            self._sync_board()
            self._update_sidebar()
            return

        if not self.game.make_move(result.move):
            self._sync_board()
            self._update_sidebar()
            return

        self._last_ai_info = f"Depth {result.depth} · {result.elapsed_seconds:.2f}s"
        self.board.animate_move(result.move, callback=self._after_move)

    # ------------------------------------------------------------------
    # Move handling (shared between both modes)
    # ------------------------------------------------------------------
    def _on_user_move(self, move: Move) -> None:
        if self.game_over:
            return
        if not self._is_human_turn():
            return
        if self._ai.is_busy():
            return
        if not self.game.make_move(move):
            return

        self.board.set_selected(None, [])
        self.board.animate_move(move, callback=self._after_move)

    def _after_move(self) -> None:
        self._sync_board()
        self._update_sidebar()
        self._check_game_end()
        if not self.game_over:
            self._schedule_ai_move(120)

    def _on_promotion_request(self, candidates: list[Move]) -> None:
        color = self.game.state.side_to_move
        dlg = PromotionDialog(color, self)
        dlg.exec()
        if dlg.selected is None:
            self.board.set_selected(None, [])
            return
        chosen = next((m for m in candidates if m.promotion == dlg.selected), None)
        if chosen is None:
            return
        self._on_user_move(chosen)

    # ------------------------------------------------------------------
    # New game flow
    # ------------------------------------------------------------------
    def _prompt_new_game(self) -> None:
        dlg = GameModeDialog(self)
        dlg.exec()
        if dlg.selected_mode is None:
            if not self.game.history:
                self.close()
            return
        color = dlg.selected_color
        self._start_new_game(dlg.selected_mode, color)

    def _on_new_game(self) -> None:
        if not self.game_over and self.game.history:
            ans = QMessageBox.question(
                self,
                "New Game",
                "Start a new game?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if ans != QMessageBox.StandardButton.Yes:
                return
        self._prompt_new_game()

    def _start_new_game(self, mode: GameMode, color: Optional[Color]) -> None:
        # 1. Stop any AI computation from the previous game.
        self._cancel_ai()

        # 2. Reset engine state.
        self.game.reset()
        self.ai.set_difficulty(self.diff_combo.currentText().lower())
        self.game_over = False
        self.game_mode = mode

        # 3. Store human color (only meaningful in COMPUTER mode).
        if mode.is_computer and color is not None:
            self.human_color = color

        # 4. Apply board orientation BEFORE resetting visuals.
        self._apply_board_orientation()

        # 5. Reset board visuals.
        self.board.set_selected(None, [])
        self.board.set_last_move(None)

        # 6. Update labels & sidebar for the new mode.
        self._apply_mode_labels()
        self._sync_board()
        self._update_sidebar()

        # 7. In COMPUTER mode, if AI plays White, it moves first.
        if mode.is_computer:
            self._schedule_ai_move(400)

    # ------------------------------------------------------------------
    # Undo
    # ------------------------------------------------------------------
    def _on_undo(self) -> None:
        had_ai = self._ai.is_busy()
        if had_ai:
            self._cancel_ai()

        history_len = len(self.game.history)
        side = self.game.state.side_to_move

        if self.game_mode.is_two_players:
            if history_len >= 1:
                self.game.undo()
                self.game_over = False
                self.board.set_selected(None, [])
                self.board.set_last_move(
                    self.game.history[-1][1] if self.game.history else None
                )
            self._sync_board()
            self._update_sidebar()
            return

        human_side = self.human_color
        ai_side = human_side.opposite

        if had_ai or (side is ai_side and history_len >= 1):
            self.game.undo()
            self.game_over = False
            self.board.set_selected(None, [])
            self.board.set_last_move(
                self.game.history[-1][1] if self.game.history else None
            )
            self._sync_board()
            self._update_sidebar()
            return

        if side is human_side and history_len >= 2:
            self.game.undo()
            self.game.undo()
            self.game_over = False
            self.board.set_selected(None, [])
            self.board.set_last_move(
                self.game.history[-1][1] if self.game.history else None
            )
            self._sync_board()
            self._update_sidebar()
            return

        self._sync_board()
        self._update_sidebar()

    # ------------------------------------------------------------------
    # Resign
    # ------------------------------------------------------------------
    def _on_resign(self) -> None:
        if self.game_over:
            return

        if self.game_mode.is_two_players:
            ans = QMessageBox.question(
                self,
                "Resign",
                "Which side resigns?\nYes = White, No = Black, Cancel = keep playing",
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No
                | QMessageBox.StandardButton.Cancel,
            )
            if ans == QMessageBox.StandardButton.Cancel:
                return
            loser = (
                Color.WHITE if ans == QMessageBox.StandardButton.Yes else Color.BLACK
            )
        else:
            ans = QMessageBox.question(
                self,
                "Resign",
                "Resign the game?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if ans != QMessageBox.StandardButton.Yes:
                return
            loser = self.human_color

        self._cancel_ai()
        self.game.resign(loser)
        self.game_over = True
        self._sync_board()
        self._update_sidebar()
        self._show_game_over_dialog()

    def _on_difficulty_change(self, text: str) -> None:
        self.ai.set_difficulty(text.lower())
        if self.game_mode.is_computer and self._ai.is_busy():
            self._cancel_ai()
            if not self.game_over and self.game.state.side_to_move is self._ai_color():
                self._schedule_ai_move(80)

    # ------------------------------------------------------------------
    # Game end
    # ------------------------------------------------------------------
    def _check_game_end(self) -> None:
        st = self.game.status
        if st in (
            GameStatus.CHECKMATE,
            GameStatus.STALEMATE,
            GameStatus.DRAW_FIFTY,
            GameStatus.DRAW_REPETITION,
            GameStatus.DRAW_MATERIAL,
            GameStatus.RESIGNED,
        ):
            self.game_over = True
            self._cancel_ai()
            self._sync_board()
            self._update_sidebar()
            self._show_game_over_dialog()

    def _show_game_over_dialog(self) -> None:
        st = self.game.status
        result = self.game.result_text()
        winner = self.game.winner()

        if st is GameStatus.CHECKMATE:
            if self.game_mode.is_two_players:
                if winner is Color.WHITE:
                    title, msg, is_win = "WHITE WINS", "Checkmate! White wins.", True
                else:
                    title, msg, is_win = "BLACK WINS", "Checkmate! Black wins.", True
            else:
                if winner is self.human_color:
                    title, msg, is_win = (
                        "YOU WIN",
                        "Congratulations! Checkmate!",
                        True,
                    )
                else:
                    title, msg, is_win = (
                        "CHECKMATE",
                        "Computer wins. Better luck next time!",
                        False,
                    )
        elif st is GameStatus.RESIGNED:
            if self.game_mode.is_two_players:
                if winner is Color.WHITE:
                    title, msg, is_win = "WHITE WINS", "Black resigned.", True
                else:
                    title, msg, is_win = "BLACK WINS", "White resigned.", True
            else:
                title, msg, is_win = "YOU RESIGNED", "Computer wins.", False
        elif st is GameStatus.STALEMATE:
            title, msg, is_win = "STALEMATE", "The game is a draw.", False
        else:
            title, msg, is_win = "DRAW", result, False

        dlg = GameOverDialog(title, msg or result, is_win, self)
        dlg.new_game_requested.connect(self._prompt_new_game)
        dlg.exit_requested.connect(self.close)
        dlg.exec()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        self._ai_timer.stop()
        self._ai.shutdown()
        super().closeEvent(event)

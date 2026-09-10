"""Custom chess board widget with animations and highlighting.

Supports optional 180° rotation so the human player can view the board
from their own side (White at bottom when playing White).
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import (
    QEasingCurve,
    QPointF,
    QPropertyAnimation,
    Property,
    QRectF,
    Qt,
    Signal,
)
from PySide6.QtGui import (
    QColor,
    QFont,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QPen,
)
from PySide6.QtWidgets import QWidget

from chess_engine import ChessGame, Color, Move, PieceType, GameStatus
from gui.resources import get_piece_pixmap


class ChessBoardWidget(QWidget):
    """Interactive board widget. Renders board, pieces, highlights, animations.

    By default Black is at the bottom (display_row = 7 - engine_row).
    If `set_flipped(True)` is called, White is at the bottom instead.
    """

    move_requested = Signal(Move)
    promotion_requested = Signal(list)

    # Colors
    LIGHT = QColor("#eedfcc")
    DARK = QColor("#b58863")
    HIGHLIGHT_SELECTED = QColor(255, 235, 100, 180)
    HIGHLIGHT_MOVE = QColor(255, 220, 80, 130)
    HIGHLIGHT_LAST = QColor(210, 200, 120, 120)
    HIGHLIGHT_CHECK = QColor(220, 80, 80, 200)
    DOT_COLOR = QColor(76, 175, 80, 200)
    CAPTURE_RING = QColor(214, 72, 72, 220)
    COORD_LIGHT = QColor(120, 90, 60)
    COORD_DARK = QColor(240, 230, 215)

    def __init__(self, game: ChessGame, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.game = game
        self.selected: Optional[tuple[int, int]] = None
        self.legal_destinations: list[Move] = []
        self.last_move: Optional[Move] = None
        self.interactive = True
        self._flipped = False  # False → Black at bottom; True → White at bottom
        self._square_size = 80
        self._anim_progress = 1.0
        self._anim_from: Optional[QPointF] = None
        self._anim_to: Optional[QPointF] = None
        self._anim_piece = None

        self._anim = QPropertyAnimation(self, b"animProgress")
        self._anim.setDuration(180)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.setMinimumSize(400, 400)
        self.setMouseTracking(True)

    # ------------------------------------------------------------------
    # Qt property for animation
    # ------------------------------------------------------------------
    def _get_anim_progress(self) -> float:
        return self._anim_progress

    def _set_anim_progress(self, v: float) -> None:
        self._anim_progress = v
        self.update()

    animProgress = Property(float, _get_anim_progress, _set_anim_progress)

    # ------------------------------------------------------------------
    # Geometry helpers (flip-aware)
    # ------------------------------------------------------------------
    def _square_size_px(self) -> int:
        return min(self.width(), self.height()) // 8

    def _board_origin(self) -> tuple[int, int]:
        size = self._square_size_px() * 8
        ox = (self.width() - size) // 2
        oy = (self.height() - size) // 2
        return ox, oy

    def _internal_to_display(self, row: int, col: int) -> tuple[int, int]:
        if self._flipped:
            return (row, col)
        return (7 - row, 7 - col)

    def _display_to_internal(self, drow: int, dcol: int) -> tuple[int, int]:
        if self._flipped:
            return (drow, dcol)
        return (7 - drow, 7 - dcol)

    def _square_rect(self, drow: int, dcol: int) -> QRectF:
        s = self._square_size_px()
        ox, oy = self._board_origin()
        return QRectF(ox + dcol * s, oy + drow * s, s, s)

    def _square_center(self, drow: int, dcol: int) -> QPointF:
        r = self._square_rect(drow, dcol)
        return r.center()

    def _event_to_internal(self, x: float, y: float) -> Optional[tuple[int, int]]:
        s = self._square_size_px()
        ox, oy = self._board_origin()
        if x < ox or y < oy or x >= ox + 8 * s or y >= oy + 8 * s:
            return None
        dcol = int((x - ox) // s)
        drow = int((y - oy) // s)
        return self._display_to_internal(drow, dcol)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def set_interactive(self, enabled: bool) -> None:
        self.interactive = enabled
        if not enabled:
            self.selected = None
            self.legal_destinations = []
            self.update()

    def set_last_move(self, move: Optional[Move]) -> None:
        self.last_move = move
        self.update()

    def set_selected(self, sq: Optional[tuple[int, int]], dests: list[Move]) -> None:
        self.selected = sq
        self.legal_destinations = dests
        self.update()

    def set_flipped(self, flipped: bool) -> None:
        """Rotate the board 180° so the given color sits at the bottom."""
        if self._flipped == flipped:
            return
        self._flipped = flipped
        # Selection is expressed in engine coords, so it stays valid.
        self.update()

    def is_flipped(self) -> bool:
        return self._flipped

    def animate_move(self, move: Move, callback=None) -> None:
        piece = move.piece
        if piece is None:
            self.update()
            if callback:
                callback()
            return

        d_from = self._internal_to_display(*move.from_sq)
        d_to = self._internal_to_display(*move.to_sq)
        self._anim_from = self._square_center(*d_from)
        self._anim_to = self._square_center(*d_to)
        self._anim_piece = piece
        self._anim_progress = 0.0

        try:
            self._anim.finished.disconnect()
        except (RuntimeError, TypeError):
            pass
        if callback:
            self._anim.finished.connect(callback)

        self._anim.stop()
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.start()

    # ------------------------------------------------------------------
    # Painting
    # ------------------------------------------------------------------
    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        painter.fillRect(self.rect(), QColor("#1a1a1a"))

        self._draw_squares(painter)
        self._draw_highlights(painter)
        self._draw_pieces(painter)
        self._draw_destination_markers(painter)
        self._draw_coordinates(painter)

        painter.end()

    def _draw_squares(self, painter: QPainter) -> None:
        for drow in range(8):
            for dcol in range(8):
                ir, ic = self._display_to_internal(drow, dcol)
                is_light = (ir + ic) % 2 == 0
                color = self.LIGHT if is_light else self.DARK
                rect = self._square_rect(drow, dcol)
                painter.fillRect(rect, color)

    def _draw_highlights(self, painter: QPainter) -> None:
        if self.last_move is not None:
            for sq in (self.last_move.from_sq, self.last_move.to_sq):
                d = self._internal_to_display(*sq)
                painter.fillRect(self._square_rect(*d), self.HIGHLIGHT_LAST)

        status = self.game.status
        if status in (GameStatus.CHECK, GameStatus.CHECKMATE):
            king_sq = self.game.state.board.find_king(self.game.state.side_to_move)
            if king_sq:
                d = self._internal_to_display(*king_sq)
                rect = self._square_rect(*d)
                painter.fillRect(rect, self.HIGHLIGHT_CHECK)

        if self.selected is not None:
            d = self._internal_to_display(*self.selected)
            painter.fillRect(self._square_rect(*d), self.HIGHLIGHT_SELECTED)

    def _draw_pieces(self, painter: QPainter) -> None:
        s = self._square_size_px()
        piece_size = int(s * 0.92)
        board = self.game.state.board

        for row in range(8):
            for col in range(8):
                p = board.grid[row][col]
                if p is None:
                    continue

                drow, dcol = self._internal_to_display(row, col)

                if (
                    self._anim_piece is not None
                    and self._anim_progress < 1.0
                    and self._anim_from is not None
                    and self._anim_to is not None
                    and p is self._anim_piece
                ):
                    t = self._anim_progress
                    pos = QPointF(
                        self._anim_from.x()
                        + (self._anim_to.x() - self._anim_from.x()) * t,
                        self._anim_from.y()
                        + (self._anim_to.y() - self._anim_from.y()) * t,
                    )
                    pixmap = get_piece_pixmap(p.piece_type, p.color, piece_size)
                    painter.drawPixmap(
                        int(pos.x() - piece_size / 2),
                        int(pos.y() - piece_size / 2),
                        pixmap,
                    )
                    continue

                pixmap = get_piece_pixmap(p.piece_type, p.color, piece_size)
                center = self._square_center(drow, dcol)
                painter.drawPixmap(
                    int(center.x() - piece_size / 2),
                    int(center.y() - piece_size / 2),
                    pixmap,
                )

    def _draw_destination_markers(self, painter: QPainter) -> None:
        s = self._square_size_px()
        for mv in self.legal_destinations:
            d = self._internal_to_display(*mv.to_sq)
            center = self._square_center(*d)

            if mv.captured is not None:
                radius = s / 2 - 6
                pen = QPen(self.CAPTURE_RING, 4)
                painter.setPen(pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawEllipse(center, radius, radius)
            else:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(self.DOT_COLOR)
                painter.drawEllipse(center, 9, 9)
        painter.setBrush(Qt.BrushStyle.NoBrush)

    def _draw_coordinates(self, painter: QPainter) -> None:
        s = self._square_size_px()
        ox, oy = self._board_origin()
        font = QFont("Segoe UI", max(8, s // 9), QFont.Weight.Bold)
        painter.setFont(font)

        # Files along the bottom edge. In normal view: h..a. In flipped view: a..h.
        for i in range(8):
            if self._flipped:
                label = chr(ord("a") + i)
            else:
                label = chr(ord("h") - i)
            x = ox + i * s + s - 6
            y = oy + 8 * s - 6
            # Determine underlying square color at this edge position
            ir, ic = self._display_to_internal(7, i)
            is_light = (ir + ic) % 2 == 0
            painter.setPen(self.COORD_LIGHT if not is_light else self.COORD_DARK)
            painter.drawText(x - 10, y - 10, label)

        # Ranks along the left edge. In normal view: 1..8 top-to-bottom.
        # In flipped view: 8..1 top-to-bottom.
        for i in range(8):
            if self._flipped:
                label = str(8 - i)
            else:
                label = str(i + 1)
            x = ox + 6
            y = oy + i * s + 18
            ir, ic = self._display_to_internal(i, 0)
            is_light = (ir + ic) % 2 == 0
            painter.setPen(
                QColor(240, 230, 215) if not is_light else QColor(120, 90, 60)
            )
            painter.drawText(x, y, label)

    # ------------------------------------------------------------------
    # Mouse
    # ------------------------------------------------------------------
    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if not self.interactive:
            return
        if event.button() != Qt.MouseButton.LeftButton:
            return

        sq = self._event_to_internal(event.position().x(), event.position().y())
        if sq is None:
            return

        row, col = sq
        board = self.game.state.board
        piece = board.grid[row][col]
        current = self.game.state.side_to_move

        if self.selected is not None:
            candidates = [m for m in self.legal_destinations if m.to_sq == (row, col)]
            if candidates:
                if any(m.promotion is not None for m in candidates):
                    self.promotion_requested.emit(candidates)
                else:
                    self.move_requested.emit(candidates[0])
                return
            if piece is not None and piece.color is current:
                self._select(row, col)
                return
            self.set_selected(None, [])
            return

        if piece is not None and piece.color is current:
            self._select(row, col)

    def _select(self, row: int, col: int) -> None:
        moves = self.game.legal_moves_from(row, col)
        self.set_selected((row, col), moves)

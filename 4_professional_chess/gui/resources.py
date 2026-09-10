"""SVG chess piece renderer - generates high quality vector pieces at runtime."""

from __future__ import annotations

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QPixmap, QPainter, QColor
from PySide6.QtSvg import QSvgRenderer

from chess_engine import Color, PieceType

# High-quality SVG chess pieces (Merida-style, simplified vector paths)
# White pieces use fill #f5f5f5 with dark outline; black use #2a2a2a with light outline.

_SVG_HEADER = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" '
    'width="100" height="100">'
)

_KING = """
<g>
  <path d="M50 8 L54 18 L64 18 L64 22 L54 22 L54 32 L46 32 L46 22 L36 22 L36 18 L46 18 L50 8 Z"
        fill="{fill}" stroke="{stroke}" stroke-width="2.2" stroke-linejoin="round"/>
  <path d="M30 38 Q50 30 70 38 L66 48 Q50 42 34 48 Z"
        fill="{fill}" stroke="{stroke}" stroke-width="2.2" stroke-linejoin="round"/>
  <path d="M34 48 Q28 60 30 72 L70 72 Q72 60 66 48 Z"
        fill="{fill}" stroke="{stroke}" stroke-width="2.2" stroke-linejoin="round"/>
  <rect x="28" y="72" width="44" height="8" rx="2"
        fill="{fill}" stroke="{stroke}" stroke-width="2.2"/>
  <rect x="24" y="80" width="52" height="10" rx="2"
        fill="{fill}" stroke="{stroke}" stroke-width="2.2"/>
</g>
"""

_QUEEN = """
<g>
  <circle cx="50" cy="14" r="4" fill="{fill}" stroke="{stroke}" stroke-width="2"/>
  <circle cx="32" cy="20" r="3.5" fill="{fill}" stroke="{stroke}" stroke-width="2"/>
  <circle cx="68" cy="20" r="3.5" fill="{fill}" stroke="{stroke}" stroke-width="2"/>
  <circle cx="22" cy="32" r="3.5" fill="{fill}" stroke="{stroke}" stroke-width="2"/>
  <circle cx="78" cy="32" r="3.5" fill="{fill}" stroke="{stroke}" stroke-width="2"/>
  <path d="M50 20 L32 44 L22 36 L28 56 L72 56 L78 36 L68 44 Z"
        fill="{fill}" stroke="{stroke}" stroke-width="2.2" stroke-linejoin="round"/>
  <path d="M28 56 Q50 50 72 56 L70 68 L30 68 Z"
        fill="{fill}" stroke="{stroke}" stroke-width="2.2" stroke-linejoin="round"/>
  <rect x="30" y="68" width="40" height="8" rx="2"
        fill="{fill}" stroke="{stroke}" stroke-width="2.2"/>
  <rect x="26" y="76" width="48" height="14" rx="2"
        fill="{fill}" stroke="{stroke}" stroke-width="2.2"/>
</g>
"""

_ROOK = """
<g>
  <path d="M26 22 L34 22 L34 30 L42 30 L42 22 L50 22 L50 30 L58 30 L58 22 L66 22 L66 30 L74 30 L74 22 L74 40 L26 40 Z"
        fill="{fill}" stroke="{stroke}" stroke-width="2.2" stroke-linejoin="round"/>
  <path d="M32 40 L68 40 L64 52 L36 52 Z"
        fill="{fill}" stroke="{stroke}" stroke-width="2.2" stroke-linejoin="round"/>
  <path d="M34 52 L66 52 L70 70 L30 70 Z"
        fill="{fill}" stroke="{stroke}" stroke-width="2.2" stroke-linejoin="round"/>
  <rect x="26" y="70" width="48" height="10" rx="2"
        fill="{fill}" stroke="{stroke}" stroke-width="2.2"/>
  <rect x="22" y="80" width="56" height="10" rx="2"
        fill="{fill}" stroke="{stroke}" stroke-width="2.2"/>
</g>
"""

_BISHOP = """
<g>
  <circle cx="50" cy="16" r="5" fill="{fill}" stroke="{stroke}" stroke-width="2"/>
  <path d="M50 22 Q36 34 34 50 Q34 58 50 58 Q66 58 66 50 Q64 34 50 22 Z"
        fill="{fill}" stroke="{stroke}" stroke-width="2.2" stroke-linejoin="round"/>
  <path d="M42 46 L58 46" stroke="{stroke}" stroke-width="2.5" stroke-linecap="round"/>
  <path d="M50 32 L50 42" stroke="{stroke}" stroke-width="2.5" stroke-linecap="round"/>
  <rect x="38" y="58" width="24" height="8" rx="2"
        fill="{fill}" stroke="{stroke}" stroke-width="2.2"/>
  <path d="M34 66 Q50 62 66 66 L70 78 L30 78 Z"
        fill="{fill}" stroke="{stroke}" stroke-width="2.2" stroke-linejoin="round"/>
  <rect x="26" y="78" width="48" height="12" rx="2"
        fill="{fill}" stroke="{stroke}" stroke-width="2.2"/>
</g>
"""

_KNIGHT = """
<g transform="translate(5,5) scale(2.1)">
  <path d="M 22,10 C 32.5,11 38.5,18 38,39 L 15,39 C 15,30 25,32.5 23,18"
        fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>
  <path d="M 24,18 C 24.38,20.91 18.45,25.37 16,27 C 13,29 13.18,31.34 11,31 C 9.958,30.06 12.41,27.96 11,28 C 10,28 11.19,29.23 10,30 C 9,30 5.997,31 6,26 C 6,24 12,14 12,14 C 12,14 13.89,12.1 14,10.5 C 13.27,9.506 13.5,8.5 13.5,7.5 C 14.5,6.5 16.5,10 16.5,10 L 18.5,10 C 18.5,10 19.28,8.008 21,7 C 22,7 22,10 22,10"
        fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>
  <path d="M 9.5 25.5 A 0.5 0.5 0 1 1 8.5,25.5 A 0.5 0.5 0 1 1 9.5 25.5 z"
        fill="{stroke}" stroke="{stroke}"/>
  <path d="M 15 15.5 A 0.5 1.5 0 1 1 14,15.5 A 0.5 1.5 0 1 1 15 15.5 z"
        transform="matrix(0.866,0.5,-0.5,0.866,9.693,-5.173)"
        fill="{stroke}" stroke="{stroke}"/>
</g>
"""

_PAWN = """
<g>
  <circle cx="50" cy="26" r="10" fill="{fill}" stroke="{stroke}" stroke-width="2.2"/>
  <path d="M42 36 Q38 44 38 54 L62 54 Q62 44 58 36 Z"
        fill="{fill}" stroke="{stroke}" stroke-width="2.2" stroke-linejoin="round"/>
  <rect x="40" y="54" width="20" height="8" rx="2"
        fill="{fill}" stroke="{stroke}" stroke-width="2.2"/>
  <rect x="32" y="62" width="36" height="10" rx="2"
        fill="{fill}" stroke="{stroke}" stroke-width="2.2"/>
  <rect x="26" y="72" width="48" height="12" rx="2"
        fill="{fill}" stroke="{stroke}" stroke-width="2.2"/>
</g>
"""

_SHAPES = {
    PieceType.KING: _KING,
    PieceType.QUEEN: _QUEEN,
    PieceType.ROOK: _ROOK,
    PieceType.BISHOP: _BISHOP,
    PieceType.KNIGHT: _KNIGHT,
    PieceType.PAWN: _PAWN,
}


def _render_svg(piece_type: PieceType, color: Color) -> bytes:
    shape = _SHAPES[piece_type]
    if color is Color.WHITE:
        fill = "#f8f8f8"
        stroke = "#1a1a1a"
    else:
        fill = "#2a2a2a"
        stroke = "#e0e0e0"
    body = shape.format(fill=fill, stroke=stroke)
    return (_SVG_HEADER + body + "</svg>").encode("utf-8")


_PIXMAP_CACHE: dict[tuple[PieceType, Color, int], QPixmap] = {}


def get_piece_pixmap(piece_type: PieceType, color: Color, size: int) -> QPixmap:
    """Return a cached, anti-aliased QPixmap for a piece at the given size."""
    key = (piece_type, color, size)
    if key in _PIXMAP_CACHE:
        return _PIXMAP_CACHE[key]

    svg_data = _render_svg(piece_type, color)
    renderer = QSvgRenderer(QByteArray(svg_data))

    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
    renderer.render(painter)
    painter.end()

    _PIXMAP_CACHE[key] = pixmap
    return pixmap

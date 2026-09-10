"""
Professional Pygame-based GUI for the chess game.
- Black (player) at the bottom, White (computer) at the top.
- Smooth animations, gradients, shadows, sound, and modern UI.
"""

from __future__ import annotations
import math
import threading
import time
from typing import Optional

import pygame

from chess_engine import ChessGame, Move, Piece, PieceType, Color, GameStatus
from chess_ai import ChessAI

# ------------------------------------------------------------------
# Dimensions & layout
# ------------------------------------------------------------------
SQ = 84
BOARD_PX = SQ * 8
MARGIN = 40
SIDEBAR_W = 340
WINDOW_W = BOARD_PX + MARGIN * 2 + SIDEBAR_W
WINDOW_H = BOARD_PX + MARGIN * 2 + 40
FPS = 60
MIN_THINK_TIME = 0.9
ANIM_DURATION = 0.45

# Colors
C_BOARD_EDGE = (58, 46, 36)
C_BOARD_EDGE2 = (86, 68, 52)
C_LIGHT = (238, 223, 204)
C_DARK = (181, 136, 99)
C_SELECTED = (241, 220, 100)
C_LAST_MOVE = (205, 191, 108)
C_CHECK = (229, 87, 87)
C_HINT_DOT = (76, 175, 80)
C_HINT_CAP = (214, 72, 72)
C_SIDEBAR = (30, 32, 38)
C_TEXT = (240, 240, 245)
C_TEXT_DIM = (150, 155, 165)
C_ACCENT = (74, 144, 217)
C_ACCENT_H = (96, 166, 240)
C_GREEN = (61, 139, 64)
C_GREEN_H = (74, 158, 76)
C_RED = (181, 69, 69)
C_RED_H = (201, 84, 84)
C_WHITE_PIECE = (250, 250, 250)
C_BLACK_PIECE = (28, 28, 32)

GLYPHS = {
    (Color.WHITE, PieceType.KING): "♔",
    (Color.WHITE, PieceType.QUEEN): "♕",
    (Color.WHITE, PieceType.ROOK): "♖",
    (Color.WHITE, PieceType.BISHOP): "♗",
    (Color.WHITE, PieceType.KNIGHT): "♘",
    (Color.WHITE, PieceType.PAWN): "♙",
    (Color.BLACK, PieceType.KING): "♚",
    (Color.BLACK, PieceType.QUEEN): "♛",
    (Color.BLACK, PieceType.ROOK): "♜",
    (Color.BLACK, PieceType.BISHOP): "♝",
    (Color.BLACK, PieceType.KNIGHT): "♞",
    (Color.BLACK, PieceType.PAWN): "♟",
}

FONT_CANDIDATES = [
    "segoeuisymbol",
    "dejavusans",
    "dejavusansmono",
    "notosanssymbols2",
    "freeserif",
    "arialunicodems",
]


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def ease_in_out_cubic(t: float) -> float:
    if t < 0.5:
        return 4 * t * t * t
    return 1 - pow(-2 * t + 2, 3) / 2


def draw_text(
    surface, text, font, color, pos, anchor="topleft", shadow=None, shadow_offset=(1, 2)
):
    if shadow is not None and len(shadow) not in (3, 4):
        shadow_offset = tuple(shadow)[:2]
        shadow = (0, 0, 0)
    img = font.render(text, True, color)
    rect = img.get_rect()
    setattr(rect, anchor, pos)
    if shadow is not None:
        sh = font.render(text, True, shadow)
        sh_rect = sh.get_rect()
        setattr(sh_rect, anchor, (pos[0] + shadow_offset[0], pos[1] + shadow_offset[1]))
        surface.blit(sh, sh_rect)
    surface.blit(img, rect)
    return rect


def vgradient(surface, rect, top_color, bottom_color):
    x, y, w, h = rect
    for i in range(h):
        t = i / max(1, h - 1)
        r = int(top_color[0] * (1 - t) + bottom_color[0] * t)
        g = int(top_color[1] * (1 - t) + bottom_color[1] * t)
        b = int(top_color[2] * (1 - t) + bottom_color[2] * t)
        pygame.draw.line(surface, (r, g, b), (x, y + i), (x + w, y + i))


def rounded_rect(surface, rect, color, radius=10, border=0, border_color=None):
    pygame.draw.rect(surface, color, rect, border_radius=radius)
    if border and border_color:
        pygame.draw.rect(surface, border_color, rect, border, border_radius=radius)


# ------------------------------------------------------------------
# Piece sprite cache
# ------------------------------------------------------------------
class PieceRenderer:
    def __init__(self, size: int, font_path: Optional[str] = None):
        self.size = size
        self.font = self._load_font(int(size * 0.78))
        self.cache: dict = {}
        self._build_cache()

    def _load_font(self, pt: int) -> pygame.font.Font:
        for name in FONT_CANDIDATES:
            path = pygame.font.match_font(name)
            if path:
                try:
                    return pygame.font.Font(path, pt)
                except Exception:
                    continue
        return pygame.font.SysFont(None, pt)

    def _build_cache(self) -> None:
        for (color, ptype), glyph in GLYPHS.items():
            surf = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
            for dx, dy, alpha in ((2, 3, 90), (1, 1, 60)):
                sh = self.font.render(glyph, True, (0, 0, 0))
                sh.set_alpha(alpha)
                r = sh.get_rect(center=(self.size // 2 + dx, self.size // 2 + dy))
                surf.blit(sh, r)
            body_color = C_WHITE_PIECE if color is Color.WHITE else C_BLACK_PIECE
            body = self.font.render(glyph, True, body_color)
            r = body.get_rect(center=(self.size // 2, self.size // 2))
            surf.blit(body, r)
            if color is Color.WHITE:
                outline = self.font.render(glyph, True, (60, 50, 45))
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    rr = outline.get_rect(
                        center=(self.size // 2 + dx, self.size // 2 + dy)
                    )
                    surf.blit(outline, rr, special_flags=pygame.BLEND_RGBA_MIN)
                surf.blit(body, r)
            self.cache[(color, ptype)] = surf

    def get(self, color: Color, ptype: PieceType) -> pygame.Surface:
        return self.cache[(color, ptype)]


# ------------------------------------------------------------------
# Sound manager (synthesized tones)
# ------------------------------------------------------------------
class SoundManager:
    def __init__(self):
        self.enabled = True
        try:
            pygame.mixer.pre_init(44100, -16, 1, 256)
            pygame.mixer.init()
        except Exception:
            self.enabled = False
            return
        self.move_snd = self._tone(420, 60, 0.35)
        self.capture_snd = self._tone(220, 90, 0.40)
        self.check_snd = self._tone(680, 130, 0.35)
        self.end_snd = self._chord([440, 550, 660], 500, 0.35)

    def _tone(self, freq, ms, vol):
        try:
            sr = 44100
            n = int(sr * ms / 1000)
            buf = bytearray()
            for i in range(n):
                env = 1.0 - (i / n)
                s = math.sin(2 * math.pi * freq * i / sr) * env * vol
                v = int(clamp(s, -1.0, 1.0) * 32767)
                buf += int(v).to_bytes(2, "little", signed=True)
            return pygame.mixer.Sound(buffer=bytes(buf))
        except Exception:
            return None

    def _chord(self, freqs, ms, vol):
        try:
            sr = 44100
            n = int(sr * ms / 1000)
            buf = bytearray()
            for i in range(n):
                env = 1.0 - (i / n)
                s = 0.0
                for f in freqs:
                    s += math.sin(2 * math.pi * f * i / sr)
                s = (s / len(freqs)) * env * vol
                v = int(clamp(s, -1.0, 1.0) * 32767)
                buf += int(v).to_bytes(2, "little", signed=True)
            return pygame.mixer.Sound(buffer=bytes(buf))
        except Exception:
            return None

    def play(self, snd):
        if not self.enabled or snd is None:
            return
        try:
            snd.play()
        except Exception:
            pass


# ------------------------------------------------------------------
# Promotion dialog
# ------------------------------------------------------------------
class PromotionDialog:
    def __init__(self, renderer, font_title, font_small, color):
        self.renderer = renderer
        self.font_title = font_title
        self.font_small = font_small
        self.color = color
        self.options = [
            PieceType.QUEEN,
            PieceType.ROOK,
            PieceType.BISHOP,
            PieceType.KNIGHT,
        ]
        self.rects: list[pygame.Rect] = []
        self.hovered: Optional[int] = None
        self.panel = pygame.Rect(0, 0, 0, 0)

    def update_layout(self, screen_w, screen_h):
        box_w = 4 * 110 + 40
        box_h = 200
        x = (screen_w - box_w) // 2
        y = (screen_h - box_h) // 2
        self.panel = pygame.Rect(x, y, box_w, box_h)
        self.rects = []
        pad = 20
        cw = (box_w - pad * 2 - 3 * 10) // 4
        ch = 110
        for i in range(4):
            rx = x + pad + i * (cw + 10)
            ry = y + 70
            self.rects.append(pygame.Rect(rx, ry, cw, ch))

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hovered = None
            for i, r in enumerate(self.rects):
                if r.collidepoint(event.pos):
                    self.hovered = i
                    break
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, r in enumerate(self.rects):
                if r.collidepoint(event.pos):
                    return self.options[i]
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return PieceType.QUEEN
        return None

    def draw(self, screen):
        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        screen.blit(overlay, (0, 0))

        shadow = self.panel.inflate(8, 8).move(0, 4)
        rounded_rect(screen, shadow, (0, 0, 0, 120), radius=16)
        rounded_rect(
            screen,
            self.panel,
            (40, 42, 50),
            radius=16,
            border=2,
            border_color=(90, 95, 110),
        )

        draw_text(
            screen,
            "Choose promotion piece",
            self.font_title,
            C_TEXT,
            (self.panel.centerx, self.panel.y + 26),
            anchor="midtop",
            shadow=(0, 0, 0),
            shadow_offset=(0, 2),
        )
        draw_text(
            screen,
            "Promote your pawn to:",
            self.font_small,
            C_TEXT_DIM,
            (self.panel.centerx, self.panel.y + 52),
            anchor="midtop",
        )

        for i, (rect, pt) in enumerate(zip(self.rects, self.options)):
            hovered = self.hovered == i
            bg = C_ACCENT_H if hovered else C_ACCENT
            rounded_rect(screen, rect, bg, radius=12)
            rounded_rect(
                screen,
                rect,
                (255, 255, 255, 30),
                radius=12,
                border=2,
                border_color=(255, 255, 255, 60),
            )
            sprite = self.renderer.get(self.color, pt)
            sx = rect.centerx - sprite.get_width() // 2
            sy = rect.centery - sprite.get_height() // 2 - 6
            screen.blit(sprite, (sx, sy))
            draw_text(
                screen,
                pt.name.capitalize(),
                self.font_small,
                (240, 240, 250),
                (rect.centerx, rect.bottom - 10),
                anchor="midbottom",
            )


# ------------------------------------------------------------------
# Main GUI
# ------------------------------------------------------------------
class ChessGUI:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Chess — You (Black) vs Computer (White)")
        self.screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
        self.clock = pygame.time.Clock()

        self.game = ChessGame()
        self.ai = ChessAI("medium")

        self.renderer = PieceRenderer(SQ - 8)
        self._load_fonts()

        self.sounds = SoundManager()

        self.selected: Optional[tuple[int, int]] = None
        self.hint_moves: list[Move] = []
        self.last_move: Optional[Move] = None
        self.ai_thinking = False
        self.game_over = False

        self.anim: Optional[dict] = None
        self.promotion_dialog: Optional[PromotionDialog] = None
        self._pending_promo_moves: list[Move] = []

        self.difficulty = "medium"
        self.diff_rects: list = []
        self.new_btn = pygame.Rect(0, 0, 0, 0)
        self.undo_btn = pygame.Rect(0, 0, 0, 0)
        self.resign_btn = pygame.Rect(0, 0, 0, 0)
        self._layout_sidebar()

        # AI threading state
        self.ai_started_at: Optional[float] = None
        self.ai_pending_delay: float = 0.0
        self.ai_thread: Optional[threading.Thread] = None
        self.ai_result: Optional[Move] = None
        self.ai_ready = False

        self._start_ai_turn(delay_ms=600)

    # ---------------------------------------------------------------
    def _load_fonts(self):
        def best(names, pt, bold=False, italic=False):
            for n in names:
                p = pygame.font.match_font(n, bold=bold, italic=italic)
                if p:
                    try:
                        return pygame.font.Font(p, pt)
                    except Exception:
                        continue
            return pygame.font.SysFont(None, pt, bold=bold, italic=italic)

        self.f_title = best(["segoeui", "dejavusans"], 24, bold=True)
        self.f_label = best(["segoeui", "dejavusans"], 15, bold=True)
        self.f_body = best(["segoeui", "dejavusans"], 14)
        self.f_small = best(["segoeui", "dejavusans"], 12)
        self.f_mono = pygame.font.SysFont("consolas,couriernew,monospace", 14)
        self.f_coords = best(["segoeui", "dejavusans"], 13, bold=True)
        self.f_big = best(["segoeui", "dejavusans"], 20, bold=True)

    # ---------------------------------------------------------------
    def _disp_to_internal(self, dr, dc):
        return (7 - dr, 7 - dc)

    def _internal_to_disp(self, r, c):
        return (7 - r, 7 - c)

    def _square_rect(self, r, c):
        dr, dc = self._internal_to_disp(r, c)
        return pygame.Rect(MARGIN + dc * SQ, MARGIN + dr * SQ, SQ, SQ)

    def _screen_to_square(self, pos):
        x, y = pos
        if not (MARGIN <= x < MARGIN + BOARD_PX and MARGIN <= y < MARGIN + BOARD_PX):
            return None
        dc = (x - MARGIN) // SQ
        dr = (y - MARGIN) // SQ
        return self._disp_to_internal(dr, dc)

    # ---------------------------------------------------------------
    def _layout_sidebar(self):
        sx = MARGIN + BOARD_PX + 20
        sy = MARGIN
        self.sidebar_rect = pygame.Rect(sx, sy, SIDEBAR_W - 40, WINDOW_H - MARGIN * 2)

        bx = self.sidebar_rect.x + 18
        bw_total = self.sidebar_rect.w - 36
        gap = 10

        btn_h = 44
        by = self.sidebar_rect.bottom - btn_h - 18
        bw = (bw_total - 2 * gap) // 3
        self.new_btn = pygame.Rect(bx, by, bw, btn_h)
        self.undo_btn = pygame.Rect(bx + bw + gap, by, bw, btn_h)
        self.resign_btn = pygame.Rect(bx + 2 * (bw + gap), by, bw, btn_h)

        diff_h = 36
        diff_label_h = 20
        dy = by - diff_h - diff_label_h - 6
        dw = (bw_total - 2 * gap) // 3
        self.diff_rects = [
            (pygame.Rect(bx, dy, dw, diff_h), "easy"),
            (pygame.Rect(bx + dw + gap, dy, dw, diff_h), "medium"),
            (pygame.Rect(bx + 2 * (dw + gap), dy, dw, diff_h), "hard"),
        ]

    # ---------------------------------------------------------------
    # AI orchestration
    # ---------------------------------------------------------------
    def _start_ai_turn(self, delay_ms=0):
        if self.game_over or self.game.state.side_to_move is not Color.WHITE:
            return
        self.ai_thinking = True
        self.ai_pending_delay = delay_ms / 1000.0
        self.ai_started_at = time.time()
        self.ai_ready = False
        self.ai_result = None
        self.ai_thread = None

    def _kick_ai_thread(self):
        self.ai_result = None
        self.ai_ready = False
        self.ai_started_at = time.time()

        # Take a snapshot of the live game so the worker thread can
        # never mutate the state that the GUI is rendering from.
        snapshot = self.game.clone()

        def worker():
            try:
                mv = self.ai.choose_move(snapshot)
            except Exception:
                mv = None
            self.ai_result = mv
            self.ai_ready = True

        self.ai_thread = threading.Thread(target=worker, daemon=True)
        self.ai_thread.start()

    def _poll_ai(self):
        if not self.ai_thinking:
            return

        # Phase 1: startup delay
        if self.ai_started_at is not None and self.ai_pending_delay > 0:
            if time.time() - self.ai_started_at < self.ai_pending_delay:
                return
            self.ai_pending_delay = 0.0
            self._kick_ai_thread()
            return

        # Phase 2: wait for AI thread + enforce MIN_THINK_TIME
        if self.ai_thread is None or not self.ai_ready:
            return
        elapsed = time.time() - (self.ai_started_at or time.time())
        if elapsed < MIN_THINK_TIME:
            return

        self.ai_thinking = False
        mv = self.ai_result
        self.ai_ready = False
        self.ai_result = None
        self.ai_thread = None
        self.ai_started_at = None
        if mv is not None:
            self._apply_ai_move(mv)

    def _apply_ai_move(self, mv):
        captured = mv.captured
        self.game.make_move(mv)
        self.last_move = mv
        self.anim = {
            "piece": self.game.state.board.grid[mv.to_sq[0]][mv.to_sq[1]],
            "from": mv.from_sq,
            "to": mv.to_sq,
            "start": time.time(),
            "dur": ANIM_DURATION,
            "captured": captured,
        }
        self._play_move_sound(captured, mv)
        self._post_move_checks()

    # ---------------------------------------------------------------
    # Player interaction
    # ---------------------------------------------------------------
    def _handle_click(self, pos):
        if self.new_btn.collidepoint(pos):
            self._new_game()
            return
        if self.undo_btn.collidepoint(pos):
            self._undo()
            return
        if self.resign_btn.collidepoint(pos):
            self._resign()
            return
        for rect, diff in self.diff_rects:
            if rect.collidepoint(pos):
                self.difficulty = diff
                self.ai.set_difficulty(diff)
                return

        if self.game_over or self.ai_thinking:
            return
        if self.game.state.side_to_move is not Color.BLACK:
            return

        sq = self._screen_to_square(pos)
        if sq is None:
            return
        r, c = sq
        piece = self.game.state.board.grid[r][c]

        if self.selected is not None:
            matches = [m for m in self.hint_moves if m.to_sq == (r, c)]
            if matches:
                if any(m.promotion for m in matches):
                    self.promotion_dialog = PromotionDialog(
                        self.renderer, self.f_big, self.f_body, Color.BLACK
                    )
                    self.promotion_dialog.update_layout(WINDOW_W, WINDOW_H)
                    self._pending_promo_moves = matches
                    return
                self._play_player_move(matches[0])
                return
            if piece is not None and piece.color is Color.BLACK:
                self._select(r, c)
                return
            self.selected = None
            self.hint_moves = []
            return

        if piece is not None and piece.color is Color.BLACK:
            self._select(r, c)

    def _select(self, r, c):
        self.selected = (r, c)
        self.hint_moves = self.game.legal_moves_from(r, c)

    def _play_player_move(self, mv):
        captured = mv.captured
        if not self.game.make_move(mv):
            return
        self.selected = None
        self.hint_moves = []
        self.last_move = mv
        self.anim = {
            "piece": self.game.state.board.grid[mv.to_sq[0]][mv.to_sq[1]],
            "from": mv.from_sq,
            "to": mv.to_sq,
            "start": time.time(),
            "dur": ANIM_DURATION,
            "captured": captured,
        }
        self._play_move_sound(captured, mv)
        self._post_move_checks()
        if not self.game_over:
            self._start_ai_turn(delay_ms=250)

    def _play_move_sound(self, captured, mv):
        if self.game.status is GameStatus.CHECKMATE or self.game_over:
            self.sounds.play(self.sounds.end_snd)
        elif self.game.status is GameStatus.CHECK:
            self.sounds.play(self.sounds.check_snd)
        elif captured is not None:
            self.sounds.play(self.sounds.capture_snd)
        else:
            self.sounds.play(self.sounds.move_snd)

    def _post_move_checks(self):
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
            self.ai_thinking = False

    # ---------------------------------------------------------------
    # Buttons
    # ---------------------------------------------------------------
    def _new_game(self):
        self.game.reset()
        self.ai.set_difficulty(self.difficulty)
        self.selected = None
        self.hint_moves = []
        self.last_move = None
        self.anim = None
        self.game_over = False
        self.ai_thinking = False
        self.promotion_dialog = None
        self._pending_promo_moves = []
        self.ai_thread = None
        self.ai_ready = False
        self.ai_result = None
        self._start_ai_turn(delay_ms=500)

    def _undo(self):
        if self.ai_thinking:
            return
        if not self.game.history:
            return
        if len(self.game.history) >= 2:
            self.game.undo()
            self.game.undo()
        else:
            self.game.undo()
        self.last_move = self.game.history[-1][1] if self.game.history else None
        self.selected = None
        self.hint_moves = []
        self.game_over = False
        self.anim = None
        if self.game.state.side_to_move is Color.WHITE:
            self._start_ai_turn(delay_ms=300)

    def _resign(self):
        if self.game_over:
            return
        self.game.resign(Color.BLACK)
        self.game_over = True
        self.sounds.play(self.sounds.end_snd)

    # ---------------------------------------------------------------
    # Main loop
    # ---------------------------------------------------------------
    def run(self):
        running = True
        while running:
            self.clock.tick(FPS)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif self.promotion_dialog is not None:
                    chosen = self.promotion_dialog.handle_event(event)
                    if chosen is not None:
                        mv = next(
                            m
                            for m in self._pending_promo_moves
                            if m.promotion is chosen
                        )
                        self.promotion_dialog = None
                        self._pending_promo_moves = []
                        self._play_player_move(mv)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self._handle_click(event.pos)
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_n and (event.mod & pygame.KMOD_CTRL):
                        self._new_game()
                    elif event.key == pygame.K_u and (event.mod & pygame.KMOD_CTRL):
                        self._undo()
                    elif event.key == pygame.K_r and (event.mod & pygame.KMOD_CTRL):
                        self._resign()

            self._poll_ai()
            self._render()

        pygame.quit()

    # ---------------------------------------------------------------
    # Rendering
    # ---------------------------------------------------------------
    def _render(self):
        vgradient(self.screen, (0, 0, WINDOW_W, WINDOW_H), (32, 34, 40), (18, 19, 24))
        frame = pygame.Rect(MARGIN - 14, MARGIN - 14, BOARD_PX + 28, BOARD_PX + 28)
        shadow = frame.inflate(20, 20).move(0, 8)
        rounded_rect(self.screen, shadow, (0, 0, 0, 110), radius=14)
        rounded_rect(self.screen, frame, C_BOARD_EDGE, radius=10)
        rounded_rect(self.screen, frame.inflate(-4, -4), C_BOARD_EDGE2, radius=8)

        self._draw_squares()
        self._draw_highlights()
        self._draw_pieces()
        self._draw_coordinates()
        self._draw_sidebar()

        if self.promotion_dialog is not None:
            self.promotion_dialog.draw(self.screen)

        pygame.display.flip()

    def _draw_squares(self):
        for dr in range(8):
            for dc in range(8):
                ir, ic = self._disp_to_internal(dr, dc)
                light = (ir + ic) % 2 == 0
                color = C_LIGHT if light else C_DARK
                x = MARGIN + dc * SQ
                y = MARGIN + dr * SQ
                pygame.draw.rect(self.screen, color, (x, y, SQ, SQ))
        pygame.draw.rect(
            self.screen, (25, 20, 16), (MARGIN, MARGIN, BOARD_PX, BOARD_PX), 1
        )

    def _draw_highlights(self):
        if self.last_move is not None:
            overlay = pygame.Surface((SQ, SQ), pygame.SRCALPHA)
            overlay.fill((*C_LAST_MOVE, 90))
            for sq in (self.last_move.from_sq, self.last_move.to_sq):
                rect = self._square_rect(*sq)
                self.screen.blit(overlay, rect.topleft)

        if self.game.status in (GameStatus.CHECK, GameStatus.CHECKMATE):
            king_color = self.game.state.side_to_move
            king_sq = self.game.state.board.find_king(king_color)
            if king_sq:
                rect = self._square_rect(*king_sq).inflate(-4, -4)
                pulse = 0.5 + 0.5 * math.sin(time.time() * 6)
                alpha = int(90 + 130 * pulse)
                overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
                pygame.draw.rect(
                    overlay, (*C_CHECK, alpha), overlay.get_rect(), border_radius=8
                )
                pygame.draw.rect(
                    overlay,
                    (*C_CHECK, 230),
                    overlay.get_rect(),
                    width=3,
                    border_radius=8,
                )
                self.screen.blit(overlay, rect.topleft)

        if self.selected is not None:
            rect = self._square_rect(*self.selected).inflate(-2, -2)
            overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
            pygame.draw.rect(
                overlay, (*C_SELECTED, 130), overlay.get_rect(), border_radius=8
            )
            pygame.draw.rect(
                overlay,
                (*C_SELECTED, 220),
                overlay.get_rect(),
                width=3,
                border_radius=8,
            )
            self.screen.blit(overlay, rect.topleft)

        for mv in self.hint_moves:
            rect = self._square_rect(*mv.to_sq)
            cx, cy = rect.center
            if mv.captured is not None:
                r = SQ // 2 - 6
                pygame.draw.circle(self.screen, C_HINT_CAP, (cx, cy), r, width=5)
            else:
                pygame.draw.circle(self.screen, C_HINT_DOT, (cx, cy), 10)

    def _draw_pieces(self):
        animating = None
        if self.anim is not None:
            t = (time.time() - self.anim["start"]) / self.anim["dur"]
            if t >= 1.0:
                self.anim = None
            else:
                animating = (self.anim, ease_in_out_cubic(t))

        for r in range(8):
            for c in range(8):
                p = self.game.state.board.grid[r][c]
                if p is None:
                    continue
                if animating is not None and (r, c) == animating[0]["to"]:
                    continue
                self._draw_piece_at(p, r, c)

        if animating is not None:
            anim, t = animating
            fr, fc = anim["from"]
            tr, tc = anim["to"]
            dr1, dc1 = self._internal_to_disp(fr, fc)
            dr2, dc2 = self._internal_to_disp(tr, tc)
            sx = MARGIN + dc1 * SQ + (dc2 - dc1) * SQ * t
            sy = MARGIN + dr1 * SQ + (dr2 - dr1) * SQ * t
            sprite = self.renderer.get(anim["piece"].color, anim["piece"].piece_type)
            self.screen.blit(sprite, (sx + 4, sy + 4))

    def _draw_piece_at(self, piece, r, c):
        rect = self._square_rect(r, c)
        sprite = self.renderer.get(piece.color, piece.piece_type)
        self.screen.blit(sprite, (rect.x + 4, rect.y + 4))

    def _draw_coordinates(self):
        for dc in range(8):
            file_label = chr(ord("h") - dc)
            x = MARGIN + dc * SQ + SQ // 2
            y = MARGIN + BOARD_PX + 12
            draw_text(
                self.screen,
                file_label,
                self.f_coords,
                (200, 200, 205),
                (x, y),
                anchor="midtop",
            )
        for dr in range(8):
            rank_label = str(dr + 1)
            x = MARGIN - 18
            y = MARGIN + dr * SQ + SQ // 2
            draw_text(
                self.screen,
                rank_label,
                self.f_coords,
                (200, 200, 205),
                (x, y),
                anchor="midright",
            )

    # ---------------------------------------------------------------
    def _draw_sidebar(self):
        r = self.sidebar_rect
        rounded_rect(self.screen, r, C_SIDEBAR, radius=14)
        rounded_rect(
            self.screen, r, (60, 64, 72), radius=14, border=1, border_color=(60, 64, 72)
        )

        x = r.x + 18
        y = r.y + 16

        draw_text(
            self.screen,
            "CHESS",
            self.f_title,
            C_ACCENT,
            (r.centerx, y),
            anchor="midtop",
            shadow=(0, 0, 0),
        )
        y += 44

        draw_text(
            self.screen, "● Computer — White", self.f_label, (220, 220, 225), (x, y)
        )
        y += 22
        draw_text(self.screen, "● You — Black", self.f_label, (220, 220, 225), (x, y))
        y += 28

        pygame.draw.line(self.screen, (60, 64, 72), (x, y), (r.right - 18, y))
        y += 14

        st = self.game.status
        if self.game_over:
            if st is GameStatus.CHECKMATE:
                w = self.game.winner()
                turn_text = (
                    f"Checkmate — {'White' if w is Color.WHITE else 'Black'} wins"
                )
                turn_color = C_ACCENT
            elif st is GameStatus.RESIGNED:
                turn_text = "You resigned — White wins"
                turn_color = C_RED_H
            else:
                turn_text = "Game over — Draw"
                turn_color = C_TEXT_DIM
        else:
            side = self.game.state.side_to_move
            if side is Color.WHITE:
                turn_text = (
                    "Computer is thinking..." if self.ai_thinking else "White to move"
                )
                turn_color = C_TEXT_DIM
            else:
                turn_text = "Your turn (Black)"
                turn_color = C_ACCENT_H

        draw_text(self.screen, turn_text, self.f_label, turn_color, (x, y))
        y += 24

        if st is GameStatus.CHECK and not self.game_over:
            draw_text(self.screen, "Check!", self.f_big, (255, 120, 120), (x, y))
        elif self.game_over:
            draw_text(
                self.screen,
                self.game.result_text(),
                self.f_body,
                (255, 200, 120),
                (x, y),
            )
        y += 26

        last_text = "Last move: —"
        if self.last_move is not None and self.game.history:
            san = self.game.history[-1][2]
            last_text = f"Last: {san}"
        draw_text(self.screen, last_text, self.f_body, C_TEXT_DIM, (x, y))
        y += 20
        draw_text(
            self.screen,
            f"Move: {self.game.state.fullmove_number}",
            self.f_body,
            C_TEXT_DIM,
            (x, y),
        )
        y += 26

        draw_text(self.screen, "Move history", self.f_label, C_TEXT, (x, y))
        y += 22

        list_rect = pygame.Rect(x, y, r.w - 36, r.bottom - y - 220)
        rounded_rect(self.screen, list_rect, (18, 20, 24), radius=10)
        rounded_rect(
            self.screen,
            list_rect,
            (60, 64, 72),
            radius=10,
            border=1,
            border_color=(60, 64, 72),
        )
        self._draw_history(list_rect)

        if self.diff_rects:
            dy = self.diff_rects[0][0].y - 20
            draw_text(self.screen, "Difficulty", self.f_body, C_TEXT_DIM, (x, dy))

        for rect, diff in self.diff_rects:
            active = diff == self.difficulty
            base = C_ACCENT if active else (55, 58, 66)
            hover = C_ACCENT_H if active else (72, 76, 86)
            mouse = pygame.mouse.get_pos()
            color = hover if rect.collidepoint(mouse) else base
            rounded_rect(self.screen, rect, color, radius=8)
            draw_text(
                self.screen,
                diff.capitalize(),
                self.f_body,
                (255, 255, 255) if active else C_TEXT,
                rect.center,
                anchor="center",
            )

        self._draw_button(self.new_btn, "New Game", C_GREEN, C_GREEN_H)
        self._draw_button(self.undo_btn, "Undo", (74, 84, 100), (94, 104, 122))
        self._draw_button(self.resign_btn, "Resign", C_RED, C_RED_H)

    def _draw_button(self, rect, label, base, hover):
        mouse = pygame.mouse.get_pos()
        color = hover if rect.collidepoint(mouse) else base
        shadow = rect.move(0, 3)
        rounded_rect(self.screen, shadow, (0, 0, 0, 90), radius=8)
        rounded_rect(self.screen, rect, color, radius=8)
        pygame.draw.rect(
            self.screen, (255, 255, 255, 40), rect, width=1, border_radius=8
        )
        draw_text(
            self.screen,
            label,
            self.f_label,
            (255, 255, 255),
            rect.center,
            anchor="center",
        )

    def _draw_history(self, rect):
        pad = 8
        line_h = 18
        max_lines = (rect.h - pad * 2) // line_h
        h = self.game.history
        lines = []
        i = 0
        n = 1
        while i < len(h):
            wsan = h[i][2]
            bsan = h[i + 1][2] if i + 1 < len(h) else ""
            lines.append(f"{n:>3}.  {wsan:<8} {bsan}")
            i += 2
            n += 1
        start = max(0, len(lines) - max_lines)
        for idx, line in enumerate(lines[start:]):
            draw_text(
                self.screen,
                line,
                self.f_mono,
                (215, 215, 220),
                (rect.x + pad, rect.y + pad + idx * line_h),
            )


# ------------------------------------------------------------------
def run() -> None:
    ChessGUI().run()


if __name__ == "__main__":
    run()

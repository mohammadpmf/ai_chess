import copy
import math
import tkinter as tk
import customtkinter as ctk

from dataclasses import dataclass
from typing import Optional, List, Tuple


# ============================================================
# Configuration
# ============================================================

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

WHITE = "white"
BLACK = "black"

FILES = "abcdefgh"

PIECE_VALUES = {
    "P": 100,
    "N": 320,
    "B": 330,
    "R": 500,
    "Q": 900,
    "K": 20000,
}

UNICODE_PIECES = {
    WHITE: {
        "K": "♔",
        "Q": "♕",
        "R": "♖",
        "B": "♗",
        "N": "♘",
        "P": "♙",
    },
    BLACK: {
        "K": "♚",
        "Q": "♛",
        "R": "♜",
        "B": "♝",
        "N": "♞",
        "P": "♟",
    },
}


# ============================================================
# Piece
# ============================================================

@dataclass
class Piece:
    color: str
    kind: str

    def symbol(self) -> str:
        return UNICODE_PIECES[self.color][self.kind]

    def value(self) -> int:
        return PIECE_VALUES[self.kind]


# ============================================================
# Move
# ============================================================

@dataclass
class Move:
    start: Tuple[int, int]
    end: Tuple[int, int]

    promotion: Optional[str] = None
    is_castling: bool = False
    is_en_passant: bool = False

    captured: Optional[Piece] = None

    def notation(self) -> str:
        sr, sc = self.start
        er, ec = self.end

        result = (
            f"{FILES[sc]}{8 - sr}"
            f"-"
            f"{FILES[ec]}{8 - er}"
        )

        if self.promotion:
            result += f"={self.promotion}"

        return result


# ============================================================
# Board - Chess Logic
# ============================================================

class Board:

    def __init__(self):
        self.reset()

    def reset(self):
        self.board = [
            [None for _ in range(8)]
            for _ in range(8)
        ]

        back_rank = [
            "R", "N", "B", "Q",
            "K", "B", "N", "R"
        ]

        for col, kind in enumerate(back_rank):
            self.board[0][col] = Piece(BLACK, kind)
            self.board[1][col] = Piece(BLACK, "P")

            self.board[6][col] = Piece(WHITE, "P")
            self.board[7][col] = Piece(WHITE, kind)

        self.turn = WHITE

        self.white_king_moved = False
        self.black_king_moved = False

        self.white_rook_a_moved = False
        self.white_rook_h_moved = False

        self.black_rook_a_moved = False
        self.black_rook_h_moved = False

        self.en_passant_target = None
        self.last_move = None

        self.captured_white = []
        self.captured_black = []

        self.move_history = []

    @staticmethod
    def inside(row, col):
        return 0 <= row < 8 and 0 <= col < 8

    @staticmethod
    def opponent(color):
        return BLACK if color == WHITE else WHITE

    def clone(self):
        return copy.deepcopy(self)

    # --------------------------------------------------------
    # King and attack detection
    # --------------------------------------------------------

    def find_king(self, color):
        for row in range(8):
            for col in range(8):
                piece = self.board[row][col]

                if (
                    piece
                    and piece.color == color
                    and piece.kind == "K"
                ):
                    return row, col

        return None

    def is_square_attacked(self, row, col, by_color):

        # Pawn
        pawn_source_row = (
            row + 1 if by_color == WHITE
            else row - 1
        )

        for dc in (-1, 1):
            pc = col + dc

            if self.inside(pawn_source_row, pc):
                piece = self.board[pawn_source_row][pc]

                if (
                    piece
                    and piece.color == by_color
                    and piece.kind == "P"
                ):
                    return True

        # Knight
        knight_offsets = [
            (-2, -1), (-2, 1),
            (-1, -2), (-1, 2),
            (1, -2), (1, 2),
            (2, -1), (2, 1),
        ]

        for dr, dc in knight_offsets:
            r = row + dr
            c = col + dc

            if self.inside(r, c):
                piece = self.board[r][c]

                if (
                    piece
                    and piece.color == by_color
                    and piece.kind == "N"
                ):
                    return True

        # King
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue

                r = row + dr
                c = col + dc

                if self.inside(r, c):
                    piece = self.board[r][c]

                    if (
                        piece
                        and piece.color == by_color
                        and piece.kind == "K"
                    ):
                        return True

        # Rook / Queen
        for dr, dc in [
            (-1, 0), (1, 0),
            (0, -1), (0, 1)
        ]:
            r = row + dr
            c = col + dc

            while self.inside(r, c):
                piece = self.board[r][c]

                if piece:
                    if (
                        piece.color == by_color
                        and piece.kind in ("R", "Q")
                    ):
                        return True

                    break

                r += dr
                c += dc

        # Bishop / Queen
        for dr, dc in [
            (-1, -1), (-1, 1),
            (1, -1), (1, 1)
        ]:
            r = row + dr
            c = col + dc

            while self.inside(r, c):
                piece = self.board[r][c]

                if piece:
                    if (
                        piece.color == by_color
                        and piece.kind in ("B", "Q")
                    ):
                        return True

                    break

                r += dr
                c += dc

        return False

    def is_in_check(self, color):
        king = self.find_king(color)

        if king is None:
            return True

        return self.is_square_attacked(
            king[0],
            king[1],
            self.opponent(color)
        )

    # --------------------------------------------------------
    # Move generation
    # --------------------------------------------------------

    def pseudo_legal_moves_for_piece(self, row, col):

        piece = self.board[row][col]

        if piece is None:
            return []

        if piece.kind == "P":
            return self._pawn_moves(row, col, piece)

        if piece.kind == "N":
            return self._knight_moves(row, col, piece)

        if piece.kind == "B":
            return self._sliding_moves(
                row, col, piece,
                [
                    (-1, -1), (-1, 1),
                    (1, -1), (1, 1),
                ]
            )

        if piece.kind == "R":
            return self._sliding_moves(
                row, col, piece,
                [
                    (-1, 0), (1, 0),
                    (0, -1), (0, 1),
                ]
            )

        if piece.kind == "Q":
            return self._sliding_moves(
                row, col, piece,
                [
                    (-1, -1), (-1, 1),
                    (1, -1), (1, 1),
                    (-1, 0), (1, 0),
                    (0, -1), (0, 1),
                ]
            )

        if piece.kind == "K":
            return self._king_moves(row, col, piece)

        return []

    def _pawn_moves(self, row, col, piece):

        moves = []

        direction = -1 if piece.color == WHITE else 1
        start_row = 6 if piece.color == WHITE else 1
        promotion_row = 0 if piece.color == WHITE else 7

        # One square
        nr = row + direction

        if self.inside(nr, col) and self.board[nr][col] is None:

            if nr == promotion_row:
                for promotion in ("Q", "R", "B", "N"):
                    moves.append(
                        Move(
                            (row, col),
                            (nr, col),
                            promotion=promotion
                        )
                    )
            else:
                moves.append(
                    Move((row, col), (nr, col))
                )

            # Two squares
            if row == start_row:
                nr2 = row + 2 * direction

                if self.board[nr2][col] is None:
                    moves.append(
                        Move((row, col), (nr2, col))
                    )

        # Capture
        for dc in (-1, 1):
            nc = col + dc

            if not self.inside(nr, nc):
                continue

            target = self.board[nr][nc]

            if target and target.color != piece.color:

                if nr == promotion_row:
                    for promotion in ("Q", "R", "B", "N"):
                        moves.append(
                            Move(
                                (row, col),
                                (nr, nc),
                                promotion=promotion,
                                captured=target
                            )
                        )
                else:
                    moves.append(
                        Move(
                            (row, col),
                            (nr, nc),
                            captured=target
                        )
                    )

            # En passant
            if self.en_passant_target == (nr, nc):

                adjacent = self.board[row][nc]

                if (
                    adjacent
                    and adjacent.kind == "P"
                    and adjacent.color != piece.color
                ):
                    moves.append(
                        Move(
                            (row, col),
                            (nr, nc),
                            is_en_passant=True,
                            captured=adjacent
                        )
                    )

        return moves

    def _knight_moves(self, row, col, piece):

        moves = []

        offsets = [
            (-2, -1), (-2, 1),
            (-1, -2), (-1, 2),
            (1, -2), (1, 2),
            (2, -1), (2, 1),
        ]

        for dr, dc in offsets:
            r = row + dr
            c = col + dc

            if not self.inside(r, c):
                continue

            target = self.board[r][c]

            if target is None:
                moves.append(
                    Move((row, col), (r, c))
                )

            elif target.color != piece.color:
                moves.append(
                    Move(
                        (row, col),
                        (r, c),
                        captured=target
                    )
                )

        return moves

    def _sliding_moves(
        self,
        row,
        col,
        piece,
        directions
    ):

        moves = []

        for dr, dc in directions:
            r = row + dr
            c = col + dc

            while self.inside(r, c):

                target = self.board[r][c]

                if target is None:
                    moves.append(
                        Move((row, col), (r, c))
                    )
                else:
                    if target.color != piece.color:
                        moves.append(
                            Move(
                                (row, col),
                                (r, c),
                                captured=target
                            )
                        )

                    break

                r += dr
                c += dc

        return moves

    def _king_moves(self, row, col, piece):

        moves = []

        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):

                if dr == 0 and dc == 0:
                    continue

                r = row + dr
                c = col + dc

                if not self.inside(r, c):
                    continue

                target = self.board[r][c]

                if target is None:
                    moves.append(
                        Move((row, col), (r, c))
                    )

                elif target.color != piece.color:
                    moves.append(
                        Move(
                            (row, col),
                            (r, c),
                            captured=target
                        )
                    )

        moves.extend(
            self._castling_moves(piece.color)
        )

        return moves

    def _castling_moves(self, color):

        moves = []

        if self.is_in_check(color):
            return moves

        enemy = self.opponent(color)

        row = 7 if color == WHITE else 0

        king = self.board[row][4]

        if not (
            king
            and king.kind == "K"
            and king.color == color
        ):
            return moves

        king_moved = (
            self.white_king_moved
            if color == WHITE
            else self.black_king_moved
        )

        if king_moved:
            return moves

        # King side
        rook_h_moved = (
            self.white_rook_h_moved
            if color == WHITE
            else self.black_rook_h_moved
        )

        rook_h = self.board[row][7]

        if (
            not rook_h_moved
            and rook_h
            and rook_h.color == color
            and rook_h.kind == "R"
            and self.board[row][5] is None
            and self.board[row][6] is None
            and not self.is_square_attacked(row, 5, enemy)
            and not self.is_square_attacked(row, 6, enemy)
        ):
            moves.append(
                Move(
                    (row, 4),
                    (row, 6),
                    is_castling=True
                )
            )

        # Queen side
        rook_a_moved = (
            self.white_rook_a_moved
            if color == WHITE
            else self.black_rook_a_moved
        )

        rook_a = self.board[row][0]

        if (
            not rook_a_moved
            and rook_a
            and rook_a.color == color
            and rook_a.kind == "R"
            and self.board[row][1] is None
            and self.board[row][2] is None
            and self.board[row][3] is None
            and not self.is_square_attacked(row, 3, enemy)
            and not self.is_square_attacked(row, 2, enemy)
        ):
            moves.append(
                Move(
                    (row, 4),
                    (row, 2),
                    is_castling=True
                )
            )

        return moves

    # --------------------------------------------------------
    # Legal move filtering
    # --------------------------------------------------------

    def legal_moves_for_piece(self, row, col):

        piece = self.board[row][col]

        if piece is None:
            return []

        pseudo_moves = self.pseudo_legal_moves_for_piece(
            row, col
        )

        legal_moves = []

        for move in pseudo_moves:
            test_board = self.clone()

            test_board.apply_move(
                move,
                record_history=False,
                switch_turn=False
            )

            if not test_board.is_in_check(piece.color):
                legal_moves.append(move)

        return legal_moves

    def all_legal_moves(self, color=None):

        if color is None:
            color = self.turn

        moves = []

        for row in range(8):
            for col in range(8):

                piece = self.board[row][col]

                if piece and piece.color == color:
                    moves.extend(
                        self.legal_moves_for_piece(row, col)
                    )

        return moves

    # --------------------------------------------------------
    # Apply move
    # --------------------------------------------------------

    def apply_move(
        self,
        move,
        record_history=True,
        switch_turn=True
    ):

        sr, sc = move.start
        er, ec = move.end

        piece = self.board[sr][sc]

        if piece is None:
            return

        captured_piece = None

        # Normal capture
        if not move.is_en_passant:
            captured_piece = self.board[er][ec]

        # En passant
        else:
            captured_piece = self.board[sr][ec]
            self.board[sr][ec] = None

        if captured_piece:
            if captured_piece.color == WHITE:
                self.captured_white.append(captured_piece)
            else:
                self.captured_black.append(captured_piece)

        # Move
        self.board[sr][sc] = None
        self.board[er][ec] = piece

        # Promotion
        if piece.kind == "P" and er in (0, 7):
            promotion = move.promotion or "Q"

            self.board[er][ec] = Piece(
                piece.color,
                promotion
            )

        # Castling rook
        if move.is_castling:

            if ec == 6:
                rook = self.board[er][7]
                self.board[er][7] = None
                self.board[er][5] = rook

            elif ec == 2:
                rook = self.board[er][0]
                self.board[er][0] = None
                self.board[er][3] = rook

        # Update castling rights for moved king
        if piece.kind == "K":

            if piece.color == WHITE:
                self.white_king_moved = True
            else:
                self.black_king_moved = True

        # Update castling rights for moved rook
        if piece.kind == "R":

            if piece.color == WHITE:

                if (sr, sc) == (7, 0):
                    self.white_rook_a_moved = True

                elif (sr, sc) == (7, 7):
                    self.white_rook_h_moved = True

            else:

                if (sr, sc) == (0, 0):
                    self.black_rook_a_moved = True

                elif (sr, sc) == (0, 7):
                    self.black_rook_h_moved = True

        # Update rights if rook was captured on original square
        if (
            captured_piece
            and captured_piece.kind == "R"
        ):

            if captured_piece.color == WHITE:

                if (er, ec) == (7, 0):
                    self.white_rook_a_moved = True

                elif (er, ec) == (7, 7):
                    self.white_rook_h_moved = True

            else:

                if (er, ec) == (0, 0):
                    self.black_rook_a_moved = True

                elif (er, ec) == (0, 7):
                    self.black_rook_h_moved = True

        # En passant target
        self.en_passant_target = None

        if (
            piece.kind == "P"
            and abs(er - sr) == 2
        ):
            self.en_passant_target = (
                (sr + er) // 2,
                sc
            )

        if record_history:
            self.last_move = copy.deepcopy(move)
            self.move_history.append(move.notation())

        if switch_turn:
            self.turn = self.opponent(self.turn)

    # --------------------------------------------------------
    # Game state
    # --------------------------------------------------------

    def game_state(self, color=None):

        if color is None:
            color = self.turn

        legal_moves = self.all_legal_moves(color)
        in_check = self.is_in_check(color)

        if not legal_moves:
            if in_check:
                return "checkmate"

            return "stalemate"

        if in_check:
            return "check"

        return "playing"


# ============================================================
# Chess AI
# ============================================================

class ChessAI:

    PAWN_TABLE = [
        [0, 0, 0, 0, 0, 0, 0, 0],
        [50, 50, 50, 50, 50, 50, 50, 50],
        [10, 10, 20, 30, 30, 20, 10, 10],
        [5, 5, 10, 25, 25, 10, 5, 5],
        [0, 0, 0, 20, 20, 0, 0, 0],
        [5, -5, -10, 0, 0, -10, -5, 5],
        [5, 10, 10, -20, -20, 10, 10, 5],
        [0, 0, 0, 0, 0, 0, 0, 0],
    ]

    KNIGHT_TABLE = [
        [-50, -40, -30, -30, -30, -30, -40, -50],
        [-40, -20, 0, 5, 5, 0, -20, -40],
        [-30, 5, 10, 15, 15, 10, 5, -30],
        [-30, 0, 15, 20, 20, 15, 0, -30],
        [-30, 5, 15, 20, 20, 15, 5, -30],
        [-30, 0, 10, 15, 15, 10, 0, -30],
        [-40, -20, 0, 0, 0, 0, -20, -40],
        [-50, -40, -30, -30, -30, -30, -40, -50],
    ]

    BISHOP_TABLE = [
        [-20, -10, -10, -10, -10, -10, -10, -20],
        [-10, 5, 0, 0, 0, 0, 5, -10],
        [-10, 10, 10, 10, 10, 10, 10, -10],
        [-10, 0, 10, 10, 10, 10, 0, -10],
        [-10, 5, 5, 10, 10, 5, 5, -10],
        [-10, 0, 5, 10, 10, 5, 0, -10],
        [-10, 0, 0, 0, 0, 0, 0, -10],
        [-20, -10, -10, -10, -10, -10, -10, -20],
    ]

    def __init__(self, depth=3):
        self.depth = depth

    def choose_move(self, board):

        moves = board.all_legal_moves(WHITE)

        if not moves:
            return None

        moves.sort(
            key=self.move_order_score,
            reverse=True
        )

        best_score = -math.inf
        best_move = moves[0]

        for move in moves:

            child = board.clone()

            child.turn = WHITE

            child.apply_move(
                move,
                switch_turn=True
            )

            score = self.minimax(
                child,
                self.depth - 1,
                -math.inf,
                math.inf,
                maximizing=False
            )

            if score > best_score:
                best_score = score
                best_move = move

        return best_move

    def minimax(
        self,
        board,
        depth,
        alpha,
        beta,
        maximizing
    ):

        state = board.game_state(board.turn)

        if state == "checkmate":
            return (
                -1000000 - depth
                if board.turn == WHITE
                else 1000000 + depth
            )

        if state == "stalemate":
            return 0

        if depth == 0:
            return self.evaluate(board)

        color = board.turn
        moves = board.all_legal_moves(color)

        moves.sort(
            key=self.move_order_score,
            reverse=maximizing
        )

        if maximizing:

            best = -math.inf

            for move in moves:
                child = board.clone()

                child.apply_move(move)

                best = max(
                    best,
                    self.minimax(
                        child,
                        depth - 1,
                        alpha,
                        beta,
                        False
                    )
                )

                alpha = max(alpha, best)

                if beta <= alpha:
                    break

            return best

        best = math.inf

        for move in moves:
            child = board.clone()

            child.apply_move(move)

            best = min(
                best,
                self.minimax(
                    child,
                    depth - 1,
                    alpha,
                    beta,
                    True
                )
            )

            beta = min(beta, best)

            if beta <= alpha:
                break

        return best

    def evaluate(self, board):

        score = 0

        for row in range(8):
            for col in range(8):

                piece = board.board[row][col]

                if not piece:
                    continue

                value = piece.value()
                positional = self.position_value(
                    piece,
                    row,
                    col
                )

                if piece.color == WHITE:
                    score += value + positional
                else:
                    score -= value + positional

        # Small center bonus
        for row, col in [
            (3, 3), (3, 4),
            (4, 3), (4, 4),
        ]:
            piece = board.board[row][col]

            if piece:
                score += (
                    10
                    if piece.color == WHITE
                    else -10
                )

        if board.is_in_check(BLACK):
            score += 30

        if board.is_in_check(WHITE):
            score -= 30

        return score

    def position_value(self, piece, row, col):

        tables = {
            "P": self.PAWN_TABLE,
            "N": self.KNIGHT_TABLE,
            "B": self.BISHOP_TABLE,
        }

        table = tables.get(piece.kind)

        if table is None:
            return 0

        actual_row = (
            row
            if piece.color == WHITE
            else 7 - row
        )

        return table[actual_row][col]

    @staticmethod
    def move_order_score(move):

        score = 0

        if move.captured:
            score += move.captured.value() * 10

        if move.promotion:
            score += PIECE_VALUES[move.promotion]

        if move.is_castling:
            score += 50

        return score


# ============================================================
# Modern GUI
# ============================================================

class ChessGame(ctk.CTk):

    LIGHT = "#E9D8B4"
    DARK = "#9A6747"

    SELECTED = "#E7C65B"
    LAST_MOVE = "#769EC8"
    LEGAL = "#55B879"
    CHECK = "#D85A5A"

    BACKGROUND = "#151A21"
    PANEL = "#202832"
    PANEL_2 = "#28323E"

    def __init__(self):

        super().__init__()

        self.title("Professional Chess")
        self.geometry("1050x780")
        self.resizable(False, False)

        self.configure(fg_color=self.BACKGROUND)

        self.board = Board()
        self.ai = ChessAI(depth=3)

        self.square_size = 82

        self.selected_square = None
        self.selected_moves = []

        self.ai_thinking = False
        self.game_over = False

        self.create_layout()
        self.draw_board()

        # White / AI starts first
        self.after(500, self.start_ai_turn)

    # --------------------------------------------------------
    # Layout
    # --------------------------------------------------------

    def create_layout(self):

        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Board area
        board_container = ctk.CTkFrame(
            self,
            fg_color="#11161C",
            corner_radius=18
        )

        board_container.grid(
            row=0,
            column=0,
            padx=(24, 14),
            pady=24,
            sticky="nsew"
        )

        self.canvas = tk.Canvas(
            board_container,
            width=self.square_size * 8,
            height=self.square_size * 8,
            bg="#11161C",
            highlightthickness=0
        )

        self.canvas.pack(
            padx=14,
            pady=14
        )

        self.canvas.bind(
            "<Button-1>",
            self.on_board_click
        )

        # Side panel
        sidebar = ctk.CTkFrame(
            self,
            width=320,
            fg_color=self.PANEL,
            corner_radius=18
        )

        sidebar.grid(
            row=0,
            column=1,
            padx=(14, 24),
            pady=24,
            sticky="nsew"
        )

        sidebar.grid_propagate(False)

        title = ctk.CTkLabel(
            sidebar,
            text="♔ CHESS ♚",
            font=ctk.CTkFont(
                size=30,
                weight="bold"
            )
        )

        title.pack(
            pady=(28, 8)
        )

        subtitle = ctk.CTkLabel(
            sidebar,
            text="YOU PLAY BLACK",
            text_color="#A9B7C6",
            font=ctk.CTkFont(
                size=12,
                weight="bold"
            )
        )

        subtitle.pack(
            pady=(0, 24)
        )

        # Turn card
        self.turn_card = ctk.CTkFrame(
            sidebar,
            fg_color=self.PANEL_2,
            corner_radius=12
        )

        self.turn_card.pack(
            fill="x",
            padx=20,
            pady=6
        )

        self.turn_label = ctk.CTkLabel(
            self.turn_card,
            text="",
            font=ctk.CTkFont(
                size=17,
                weight="bold"
            )
        )

        self.turn_label.pack(
            padx=16,
            pady=14
        )

        # Status
        self.status_label = ctk.CTkLabel(
            sidebar,
            text="",
            justify="left",
            wraplength=260,
            font=ctk.CTkFont(size=14)
        )

        self.status_label.pack(
            fill="x",
            padx=24,
            pady=(20, 12)
        )

        # Captured
        captured_title = ctk.CTkLabel(
            sidebar,
            text="CAPTURED PIECES",
            anchor="w",
            font=ctk.CTkFont(
                size=12,
                weight="bold"
            ),
            text_color="#A9B7C6"
        )

        captured_title.pack(
            fill="x",
            padx=24,
            pady=(12, 4)
        )

        self.captured_label = ctk.CTkLabel(
            sidebar,
            text="No pieces captured",
            justify="left",
            anchor="w",
            wraplength=260,
            font=ctk.CTkFont(size=20)
        )

        self.captured_label.pack(
            fill="x",
            padx=24,
            pady=(0, 14)
        )

        # Last move
        last_move_title = ctk.CTkLabel(
            sidebar,
            text="LAST MOVE",
            anchor="w",
            font=ctk.CTkFont(
                size=12,
                weight="bold"
            ),
            text_color="#A9B7C6"
        )

        last_move_title.pack(
            fill="x",
            padx=24,
            pady=(6, 4)
        )

        self.last_move_label = ctk.CTkLabel(
            sidebar,
            text="-",
            anchor="w",
            font=ctk.CTkFont(
                size=16,
                weight="bold"
            )
        )

        self.last_move_label.pack(
            fill="x",
            padx=24,
            pady=(0, 20)
        )

        # Spacer
        spacer = ctk.CTkFrame(
            sidebar,
            fg_color="transparent"
        )

        spacer.pack(
            expand=True,
            fill="both"
        )

        # New Game button
        self.new_game_button = ctk.CTkButton(
            sidebar,
            text="↻  New Game",
            height=48,
            corner_radius=12,
            font=ctk.CTkFont(
                size=16,
                weight="bold"
            ),
            command=self.new_game
        )

        self.new_game_button.pack(
            fill="x",
            padx=22,
            pady=(10, 26)
        )

    # --------------------------------------------------------
    # Draw board
    # --------------------------------------------------------

    def draw_board(self):

        self.canvas.delete("all")

        check_king = None

        if self.board.is_in_check(self.board.turn):
            check_king = self.board.find_king(
                self.board.turn
            )

        for row in range(8):
            for col in range(8):

                x1 = col * self.square_size
                y1 = row * self.square_size

                x2 = x1 + self.square_size
                y2 = y1 + self.square_size

                color = (
                    self.LIGHT
                    if (row + col) % 2 == 0
                    else self.DARK
                )

                # Last move
                if self.board.last_move:
                    if (
                        (row, col)
                        in (
                            self.board.last_move.start,
                            self.board.last_move.end
                        )
                    ):
                        color = self.LAST_MOVE

                # Check
                if check_king == (row, col):
                    color = self.CHECK

                # Selected
                if self.selected_square == (row, col):
                    color = self.SELECTED

                self.canvas.create_rectangle(
                    x1, y1, x2, y2,
                    fill=color,
                    outline=color
                )

                # Rank coordinates
                if col == 0:
                    coord_color = (
                        self.DARK
                        if (row + col) % 2 == 0
                        else self.LIGHT
                    )

                    self.canvas.create_text(
                        x1 + 8,
                        y1 + 8,
                        text=str(8 - row),
                        anchor="nw",
                        fill=coord_color,
                        font=(
                            "Segoe UI",
                            10,
                            "bold"
                        )
                    )

                # File coordinates
                if row == 7:
                    coord_color = (
                        self.DARK
                        if (row + col) % 2 == 0
                        else self.LIGHT
                    )

                    self.canvas.create_text(
                        x2 - 8,
                        y2 - 8,
                        text=FILES[col],
                        anchor="se",
                        fill=coord_color,
                        font=(
                            "Segoe UI",
                            10,
                            "bold"
                        )
                    )

        # Legal move indicators
        for move in self.selected_moves:

            row, col = move.end

            cx = (
                col * self.square_size
                + self.square_size / 2
            )

            cy = (
                row * self.square_size
                + self.square_size / 2
            )

            target = self.board.board[row][col]

            if target is None:

                radius = 9

                self.canvas.create_oval(
                    cx - radius,
                    cy - radius,
                    cx + radius,
                    cy + radius,
                    fill=self.LEGAL,
                    outline=""
                )

            else:

                radius = (
                    self.square_size / 2 - 8
                )

                self.canvas.create_oval(
                    cx - radius,
                    cy - radius,
                    cx + radius,
                    cy + radius,
                    outline=self.LEGAL,
                    width=5
                )

        # Pieces
        for row in range(8):
            for col in range(8):

                piece = self.board.board[row][col]

                if piece is None:
                    continue

                x = (
                    col * self.square_size
                    + self.square_size / 2
                )

                y = (
                    row * self.square_size
                    + self.square_size / 2
                )

                # Shadow
                self.canvas.create_text(
                    x + 2,
                    y + 3,
                    text=piece.symbol(),
                    font=(
                        "DejaVu Sans",
                        50
                    ),
                    fill="#000000"
                )

                # Piece
                fill = (
                    "#F7F4EC"
                    if piece.color == WHITE
                    else "#17191C"
                )

                self.canvas.create_text(
                    x,
                    y,
                    text=piece.symbol(),
                    font=(
                        "DejaVu Sans",
                        50
                    ),
                    fill=fill
                )

        self.update_status()

    # --------------------------------------------------------
    # Board click
    # --------------------------------------------------------

    def on_board_click(self, event):

        if (
            self.ai_thinking
            or self.game_over
            or self.board.turn != BLACK
        ):
            return

        col = event.x // self.square_size
        row = event.y // self.square_size

        if not self.board.inside(row, col):
            return

        clicked_piece = self.board.board[row][col]

        # First selection
        if self.selected_square is None:

            if (
                clicked_piece
                and clicked_piece.color == BLACK
            ):
                self.select_piece(row, col)

            return

        # Select another own piece
        if (
            clicked_piece
            and clicked_piece.color == BLACK
        ):
            self.select_piece(row, col)
            return

        possible_moves = [
            move
            for move in self.selected_moves
            if move.end == (row, col)
        ]

        if not possible_moves:
            self.selected_square = None
            self.selected_moves = []
            self.draw_board()
            return

        promotion_moves = [
            move
            for move in possible_moves
            if move.promotion
        ]

        if promotion_moves:
            self.show_promotion_dialog(
                promotion_moves
            )
        else:
            self.execute_user_move(
                possible_moves[0]
            )

    def select_piece(self, row, col):

        self.selected_square = (row, col)

        self.selected_moves = (
            self.board.legal_moves_for_piece(
                row, col
            )
        )

        self.draw_board()

    # --------------------------------------------------------
    # User move
    # --------------------------------------------------------

    def execute_user_move(self, move):

        self.board.apply_move(move)

        self.selected_square = None
        self.selected_moves = []

        self.draw_board()

        if self.check_game_over():
            return

        self.ai_thinking = True
        self.update_status()

        self.after(500, self.start_ai_turn)

    # --------------------------------------------------------
    # Promotion
    # --------------------------------------------------------

    def show_promotion_dialog(self, moves):

        dialog = ctk.CTkToplevel(self)

        dialog.title("Pawn Promotion")
        dialog.geometry("430x190")
        dialog.resizable(False, False)

        dialog.configure(
            fg_color=self.PANEL
        )

        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(
            dialog,
            text="Choose your promotion",
            font=ctk.CTkFont(
                size=20,
                weight="bold"
            )
        ).pack(
            pady=(24, 16)
        )

        choices = ctk.CTkFrame(
            dialog,
            fg_color="transparent"
        )

        choices.pack()

        names = {
            "Q": "Queen",
            "R": "Rook",
            "B": "Bishop",
            "N": "Knight",
        }

        for move in moves:

            button = ctk.CTkButton(
                choices,
                text=(
                    UNICODE_PIECES[BLACK][move.promotion]
                    + "\n"
                    + names[move.promotion]
                ),
                width=92,
                height=75,
                corner_radius=12,
                font=ctk.CTkFont(
                    size=15,
                    weight="bold"
                ),
                command=lambda m=move: self.finish_promotion(
                    dialog,
                    m
                )
            )

            button.pack(
                side="left",
                padx=4
            )

    def finish_promotion(self, dialog, move):

        dialog.destroy()
        self.execute_user_move(move)

    # --------------------------------------------------------
    # AI
    # --------------------------------------------------------

    def start_ai_turn(self):

        if self.game_over:
            self.ai_thinking = False
            return

        if self.board.turn != WHITE:
            self.ai_thinking = False
            return

        self.ai_thinking = True

        self.update_status()
        self.update_idletasks()

        move = self.ai.choose_move(self.board)

        if move is not None:
            self.board.apply_move(move)

        self.ai_thinking = False

        self.draw_board()

        self.check_game_over()

    # --------------------------------------------------------
    # New game
    # --------------------------------------------------------

    def new_game(self):

        self.board.reset()

        self.selected_square = None
        self.selected_moves = []

        self.ai_thinking = True
        self.game_over = False

        self.draw_board()

        self.after(500, self.start_ai_turn)

    # --------------------------------------------------------
    # Status
    # --------------------------------------------------------

    def update_status(self):

        if self.board.turn == WHITE:
            turn = "● WHITE — Computer"
        else:
            turn = "● BLACK — Your turn"

        self.turn_label.configure(text=turn)

        state = self.board.game_state(
            self.board.turn
        )

        if self.ai_thinking:
            status = "Computer is thinking..."

        elif state == "check":
            status = "⚠ CHECK! The king is under attack."

        elif state == "checkmate":
            if self.board.turn == WHITE:
                status = "CHECKMATE — You win!"
            else:
                status = "CHECKMATE — Computer wins."

        elif state == "stalemate":
            status = "STALEMATE — Draw."

        else:
            status = "Game in progress."

        self.status_label.configure(
            text=status
        )

        captured_lines = []

        if self.board.captured_black:
            captured_lines.append(
                "White: "
                + " ".join(
                    p.symbol()
                    for p in self.board.captured_black
                )
            )

        if self.board.captured_white:
            captured_lines.append(
                "Black: "
                + " ".join(
                    p.symbol()
                    for p in self.board.captured_white
                )
            )

        self.captured_label.configure(
            text=(
                "\n".join(captured_lines)
                if captured_lines
                else "No pieces captured"
            )
        )

        if self.board.last_move:
            self.last_move_label.configure(
                text=self.board.last_move.notation()
            )
        else:
            self.last_move_label.configure(text="-")

    # --------------------------------------------------------
    # End game
    # --------------------------------------------------------

    def check_game_over(self):

        state = self.board.game_state(
            self.board.turn
        )

        if state in ("playing", "check"):

            if (
                state == "check"
                and self.board.turn == BLACK
                and not self.ai_thinking
            ):
                self.after(
                    100,
                    lambda: self.show_message(
                        "Check!",
                        "Your king is in check."
                    )
                )

            return False

        self.game_over = True

        if state == "checkmate":

            if self.board.turn == WHITE:
                title = "Checkmate!"
                message = (
                    "Congratulations!\n"
                    "You defeated the computer."
                )
            else:
                title = "Checkmate!"
                message = (
                    "The computer wins this game."
                )

        else:
            title = "Stalemate"
            message = (
                "The game ended in a draw."
            )

        self.after(
            100,
            lambda: self.show_message(
                title,
                message
            )
        )

        return True

    # --------------------------------------------------------
    # Modern message dialog
    # --------------------------------------------------------

    def show_message(self, title, message):

        dialog = ctk.CTkToplevel(self)

        dialog.title(title)
        dialog.geometry("390x220")
        dialog.resizable(False, False)

        dialog.configure(
            fg_color=self.PANEL
        )

        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(
            dialog,
            text=title,
            font=ctk.CTkFont(
                size=24,
                weight="bold"
            )
        ).pack(
            pady=(35, 15)
        )

        ctk.CTkLabel(
            dialog,
            text=message,
            justify="center",
            font=ctk.CTkFont(size=15)
        ).pack(
            padx=30,
            pady=(0, 25)
        )

        ctk.CTkButton(
            dialog,
            text="OK",
            width=140,
            command=dialog.destroy
        ).pack()


# ============================================================
# Application Entry Point
# ============================================================

if __name__ == "__main__":

    app = ChessGame()
    app.mainloop()

import tkinter as tk
from tkinter import messagebox
from dataclasses import dataclass
from typing import Optional, List, Tuple
import copy
import math

# ============================================================
# Constants
# ============================================================

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
    "white": {
        "K": "♔",
        "Q": "♕",
        "R": "♖",
        "B": "♗",
        "N": "♘",
        "P": "♙",
    },
    "black": {
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
    """
    نماینده یک مهره شطرنج.

    kind:
        K = King
        Q = Queen
        R = Rook
        B = Bishop
        N = Knight
        P = Pawn
    """

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
    """
    یک حرکت شطرنج.

    promotion:
        در صورت ارتقای سرباز یکی از Q/R/B/N است.

    is_castling:
        حرکت روش کوتاه یا بلند.

    is_en_passant:
        حرکت آن پاسان.
    """

    start: Tuple[int, int]
    end: Tuple[int, int]

    promotion: Optional[str] = None
    is_castling: bool = False
    is_en_passant: bool = False

    captured: Optional[Piece] = None

    def notation(self) -> str:
        sf, sr = self.start
        ef, er = self.end

        text = FILES[sf] + str(8 - sr) + "-" + FILES[ef] + str(8 - er)

        if self.promotion:
            text += "=" + self.promotion

        return text


# ============================================================
# Board
# ============================================================


class Board:
    """
    منطق اصلی بازی شطرنج.

    این کلاس هیچ وابستگی به Tkinter ندارد.
    بنابراین منطق بازی کاملاً از رابط گرافیکی جدا است.
    """

    def __init__(self):
        self.reset()

    # --------------------------------------------------------
    # Initialization
    # --------------------------------------------------------

    def reset(self):
        self.board = [[None for _ in range(8)] for _ in range(8)]

        # ردیف اول سفید در پایین صفحه منطقی
        back_rank = ["R", "N", "B", "Q", "K", "B", "N", "R"]

        for col, kind in enumerate(back_rank):
            self.board[7][col] = Piece(WHITE, kind)
            self.board[6][col] = Piece(WHITE, "P")

            self.board[0][col] = Piece(BLACK, kind)
            self.board[1][col] = Piece(BLACK, "P")

        self.turn = WHITE

        # Castle rights
        self.white_king_moved = False
        self.black_king_moved = False

        self.white_rook_a_moved = False
        self.white_rook_h_moved = False

        self.black_rook_a_moved = False
        self.black_rook_h_moved = False

        # En passant target:
        # خانه‌ای که سرباز می‌تواند در حرکت بعدی آن پاسان شود.
        self.en_passant_target = None

        self.last_move: Optional[Move] = None

        self.captured_white: List[Piece] = []
        self.captured_black: List[Piece] = []

    # --------------------------------------------------------
    # Utilities
    # --------------------------------------------------------

    @staticmethod
    def inside(row: int, col: int) -> bool:
        return 0 <= row < 8 and 0 <= col < 8

    @staticmethod
    def opponent(color: str) -> str:
        return BLACK if color == WHITE else WHITE

    def clone(self):
        return copy.deepcopy(self)

    # --------------------------------------------------------
    # King
    # --------------------------------------------------------

    def find_king(self, color: str) -> Optional[Tuple[int, int]]:
        for row in range(8):
            for col in range(8):
                piece = self.board[row][col]

                if piece and piece.color == color and piece.kind == "K":
                    return row, col

        return None

    # --------------------------------------------------------
    # Attack detection
    # --------------------------------------------------------

    def is_square_attacked(self, row: int, col: int, by_color: str) -> bool:

        # ----------------------------------------------------
        # Pawn attacks
        # ----------------------------------------------------

        pawn_row = row + (1 if by_color == WHITE else -1)

        for dc in (-1, 1):
            pc = col + dc

            if self.inside(pawn_row, pc):
                piece = self.board[pawn_row][pc]

                if piece and piece.color == by_color and piece.kind == "P":
                    return True

        # ----------------------------------------------------
        # Knight attacks
        # ----------------------------------------------------

        knight_offsets = [
            (-2, -1),
            (-2, 1),
            (-1, -2),
            (-1, 2),
            (1, -2),
            (1, 2),
            (2, -1),
            (2, 1),
        ]

        for dr, dc in knight_offsets:
            r = row + dr
            c = col + dc

            if self.inside(r, c):
                piece = self.board[r][c]

                if piece and piece.color == by_color and piece.kind == "N":
                    return True

        # ----------------------------------------------------
        # King attacks
        # ----------------------------------------------------

        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):

                if dr == 0 and dc == 0:
                    continue

                r = row + dr
                c = col + dc

                if self.inside(r, c):
                    piece = self.board[r][c]

                    if piece and piece.color == by_color and piece.kind == "K":
                        return True

        # ----------------------------------------------------
        # Rook / Queen
        # ----------------------------------------------------

        rook_dirs = [
            (-1, 0),
            (1, 0),
            (0, -1),
            (0, 1),
        ]

        for dr, dc in rook_dirs:
            r = row + dr
            c = col + dc

            while self.inside(r, c):
                piece = self.board[r][c]

                if piece:
                    if piece.color == by_color and piece.kind in ("R", "Q"):
                        return True

                    break

                r += dr
                c += dc

        # ----------------------------------------------------
        # Bishop / Queen
        # ----------------------------------------------------

        bishop_dirs = [
            (-1, -1),
            (-1, 1),
            (1, -1),
            (1, 1),
        ]

        for dr, dc in bishop_dirs:
            r = row + dr
            c = col + dc

            while self.inside(r, c):
                piece = self.board[r][c]

                if piece:
                    if piece.color == by_color and piece.kind in ("B", "Q"):
                        return True

                    break

                r += dr
                c += dc

        return False

    def is_in_check(self, color: str) -> bool:
        king = self.find_king(color)

        if king is None:
            return True

        return self.is_square_attacked(king[0], king[1], self.opponent(color))

    # --------------------------------------------------------
    # Pseudo legal moves
    # --------------------------------------------------------

    def pseudo_legal_moves_for_piece(self, row: int, col: int) -> List[Move]:

        piece = self.board[row][col]

        if piece is None:
            return []

        moves = []

        if piece.kind == "P":
            moves.extend(self._pawn_moves(row, col, piece))

        elif piece.kind == "N":
            moves.extend(self._knight_moves(row, col, piece))

        elif piece.kind == "B":
            moves.extend(
                self._sliding_moves(
                    row,
                    col,
                    piece,
                    [
                        (-1, -1),
                        (-1, 1),
                        (1, -1),
                        (1, 1),
                    ],
                )
            )

        elif piece.kind == "R":
            moves.extend(
                self._sliding_moves(
                    row,
                    col,
                    piece,
                    [
                        (-1, 0),
                        (1, 0),
                        (0, -1),
                        (0, 1),
                    ],
                )
            )

        elif piece.kind == "Q":
            moves.extend(
                self._sliding_moves(
                    row,
                    col,
                    piece,
                    [
                        (-1, -1),
                        (-1, 1),
                        (1, -1),
                        (1, 1),
                        (-1, 0),
                        (1, 0),
                        (0, -1),
                        (0, 1),
                    ],
                )
            )

        elif piece.kind == "K":
            moves.extend(self._king_moves(row, col, piece))

        return moves

    # --------------------------------------------------------
    # Pawn
    # --------------------------------------------------------

    def _pawn_moves(self, row: int, col: int, piece: Piece) -> List[Move]:

        moves = []

        direction = -1 if piece.color == WHITE else 1
        start_row = 6 if piece.color == WHITE else 1
        promotion_row = 0 if piece.color == WHITE else 7

        # ----------------------------------------------------
        # One square forward
        # ----------------------------------------------------

        new_row = row + direction

        if self.inside(new_row, col):
            if self.board[new_row][col] is None:

                if new_row == promotion_row:
                    for promotion in ("Q", "R", "B", "N"):
                        moves.append(
                            Move((row, col), (new_row, col), promotion=promotion)
                        )
                else:
                    moves.append(Move((row, col), (new_row, col)))

                # Two squares forward
                if row == start_row:
                    two_row = row + 2 * direction

                    if self.board[two_row][col] is None:
                        moves.append(Move((row, col), (two_row, col)))

        # ----------------------------------------------------
        # Captures
        # ----------------------------------------------------

        for dc in (-1, 1):

            new_col = col + dc

            if not self.inside(new_row, new_col):
                continue

            target = self.board[new_row][new_col]

            if target and target.color != piece.color:

                if new_row == promotion_row:
                    for promotion in ("Q", "R", "B", "N"):
                        moves.append(
                            Move(
                                (row, col),
                                (new_row, new_col),
                                promotion=promotion,
                                captured=target,
                            )
                        )
                else:
                    moves.append(Move((row, col), (new_row, new_col), captured=target))

            # ------------------------------------------------
            # En passant
            # ------------------------------------------------

            if self.en_passant_target == (new_row, new_col):
                adjacent = self.board[row][new_col]

                if adjacent and adjacent.color != piece.color and adjacent.kind == "P":
                    moves.append(
                        Move(
                            (row, col),
                            (new_row, new_col),
                            is_en_passant=True,
                            captured=adjacent,
                        )
                    )

        return moves

    # --------------------------------------------------------
    # Knight
    # --------------------------------------------------------

    def _knight_moves(self, row: int, col: int, piece: Piece) -> List[Move]:

        moves = []

        offsets = [
            (-2, -1),
            (-2, 1),
            (-1, -2),
            (-1, 2),
            (1, -2),
            (1, 2),
            (2, -1),
            (2, 1),
        ]

        for dr, dc in offsets:
            r = row + dr
            c = col + dc

            if not self.inside(r, c):
                continue

            target = self.board[r][c]

            if target is None:
                moves.append(Move((row, col), (r, c)))

            elif target.color != piece.color:
                moves.append(Move((row, col), (r, c), captured=target))

        return moves

    # --------------------------------------------------------
    # Sliding pieces
    # --------------------------------------------------------

    def _sliding_moves(
        self, row: int, col: int, piece: Piece, directions
    ) -> List[Move]:

        moves = []

        for dr, dc in directions:

            r = row + dr
            c = col + dc

            while self.inside(r, c):

                target = self.board[r][c]

                if target is None:
                    moves.append(Move((row, col), (r, c)))

                else:

                    if target.color != piece.color:
                        moves.append(Move((row, col), (r, c), captured=target))

                    break

                r += dr
                c += dc

        return moves

    # --------------------------------------------------------
    # King
    # --------------------------------------------------------

    def _king_moves(self, row: int, col: int, piece: Piece) -> List[Move]:

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
                    moves.append(Move((row, col), (r, c)))

                elif target.color != piece.color:
                    moves.append(Move((row, col), (r, c), captured=target))

        # Castling
        moves.extend(self._castling_moves(piece.color))

        return moves

    # --------------------------------------------------------
    # Castling
    # --------------------------------------------------------

    def _castling_moves(self, color: str) -> List[Move]:

        moves = []

        if self.is_in_check(color):
            return moves

        enemy = self.opponent(color)

        if color == WHITE:
            king_row = 7

            # ----------------------------------------------
            # King side
            # ----------------------------------------------

            king = self.board[7][4]
            rook = self.board[7][7]

            if (
                not self.white_king_moved
                and not self.white_rook_h_moved
                and king
                and king.kind == "K"
                and king.color == WHITE
                and rook
                and rook.kind == "R"
                and rook.color == WHITE
                and self.board[7][5] is None
                and self.board[7][6] is None
                and not self.is_square_attacked(7, 5, enemy)
                and not self.is_square_attacked(7, 6, enemy)
            ):
                moves.append(Move((7, 4), (7, 6), is_castling=True))

            # ----------------------------------------------
            # Queen side
            # ----------------------------------------------

            rook = self.board[7][0]

            if (
                not self.white_king_moved
                and not self.white_rook_a_moved
                and king
                and king.kind == "K"
                and king.color == WHITE
                and rook
                and rook.kind == "R"
                and rook.color == WHITE
                and self.board[7][1] is None
                and self.board[7][2] is None
                and self.board[7][3] is None
                and not self.is_square_attacked(7, 3, enemy)
                and not self.is_square_attacked(7, 2, enemy)
            ):
                moves.append(Move((7, 4), (7, 2), is_castling=True))

        else:
            king_row = 0

            # ----------------------------------------------
            # King side
            # ----------------------------------------------

            king = self.board[0][4]
            rook = self.board[0][7]

            if (
                not self.black_king_moved
                and not self.black_rook_h_moved
                and king
                and king.kind == "K"
                and king.color == BLACK
                and rook
                and rook.kind == "R"
                and rook.color == BLACK
                and self.board[0][5] is None
                and self.board[0][6] is None
                and not self.is_square_attacked(0, 5, enemy)
                and not self.is_square_attacked(0, 6, enemy)
            ):
                moves.append(Move((0, 4), (0, 6), is_castling=True))

            # ----------------------------------------------
            # Queen side
            # ----------------------------------------------

            rook = self.board[0][0]

            if (
                not self.black_king_moved
                and not self.black_rook_a_moved
                and king
                and king.kind == "K"
                and king.color == BLACK
                and rook
                and rook.kind == "R"
                and rook.color == BLACK
                and self.board[0][1] is None
                and self.board[0][2] is None
                and self.board[0][3] is None
                and not self.is_square_attacked(0, 3, enemy)
                and not self.is_square_attacked(0, 2, enemy)
            ):
                moves.append(Move((0, 4), (0, 2), is_castling=True))

        return moves

    # --------------------------------------------------------
    # Legal moves
    # --------------------------------------------------------

    def legal_moves_for_piece(self, row: int, col: int) -> List[Move]:

        piece = self.board[row][col]

        if piece is None:
            return []

        pseudo = self.pseudo_legal_moves_for_piece(row, col)

        legal = []

        for move in pseudo:

            test_board = self.clone()

            # برای promotion در موتور، promotion از قبل مشخص است.
            test_board.apply_move(move, record_history=False)

            if not test_board.is_in_check(piece.color):
                legal.append(move)

        return legal

    def all_legal_moves(self, color: Optional[str] = None) -> List[Move]:

        if color is None:
            color = self.turn

        moves = []

        for row in range(8):
            for col in range(8):

                piece = self.board[row][col]

                if piece and piece.color == color:
                    moves.extend(self.legal_moves_for_piece(row, col))

        return moves

    # --------------------------------------------------------
    # Apply move
    # --------------------------------------------------------

    def apply_move(self, move: Move, record_history: bool = True):

        sr, sc = move.start
        er, ec = move.end

        piece = self.board[sr][sc]

        if piece is None:
            return

        captured_piece = move.captured

        # ----------------------------------------------------
        # Normal capture
        # ----------------------------------------------------

        if not move.is_en_passant:
            target = self.board[er][ec]

            if target:
                captured_piece = target

                if target.color == WHITE:
                    self.captured_white.append(target)
                else:
                    self.captured_black.append(target)

        # ----------------------------------------------------
        # En passant capture
        # ----------------------------------------------------

        if move.is_en_passant:

            captured_row = sr
            captured_col = ec

            captured_piece = self.board[captured_row][captured_col]

            if captured_piece:
                if captured_piece.color == WHITE:
                    self.captured_white.append(captured_piece)
                else:
                    self.captured_black.append(captured_piece)

                self.board[captured_row][captured_col] = None

        # ----------------------------------------------------
        # Move piece
        # ----------------------------------------------------

        self.board[sr][sc] = None
        self.board[er][ec] = piece

        # ----------------------------------------------------
        # Promotion
        # ----------------------------------------------------

        if piece.kind == "P" and er in (0, 7):
            # AI و حرکت‌های داخلی همیشه promotion مشخص دارند.
            promotion = move.promotion or "Q"

            self.board[er][ec] = Piece(piece.color, promotion)

        # ----------------------------------------------------
        # Castling
        # ----------------------------------------------------

        if move.is_castling:

            # King side
            if ec == 6:

                rook = self.board[er][7]

                self.board[er][7] = None
                self.board[er][5] = rook

            # Queen side
            elif ec == 2:

                rook = self.board[er][0]

                self.board[er][0] = None
                self.board[er][3] = rook

        # ----------------------------------------------------
        # Update castling rights
        # ----------------------------------------------------

        if piece.kind == "K":

            if piece.color == WHITE:
                self.white_king_moved = True
            else:
                self.black_king_moved = True

        if piece.kind == "R":

            if piece.color == WHITE:

                if sr == 7 and sc == 0:
                    self.white_rook_a_moved = True

                elif sr == 7 and sc == 7:
                    self.white_rook_h_moved = True

            else:

                if sr == 0 and sc == 0:
                    self.black_rook_a_moved = True

                elif sr == 0 and sc == 7:
                    self.black_rook_h_moved = True

        # اگر رخ روی خانه اولیه خودش گرفته شود،
        # حق روش همان سمت از بین می‌رود.
        if captured_piece and captured_piece.kind == "R":

            if captured_piece.color == WHITE:

                if er == 7 and ec == 0:
                    self.white_rook_a_moved = True

                elif er == 7 and ec == 7:
                    self.white_rook_h_moved = True

            else:

                if er == 0 and ec == 0:
                    self.black_rook_a_moved = True

                elif er == 0 and ec == 7:
                    self.black_rook_h_moved = True

        # ----------------------------------------------------
        # En passant target
        # ----------------------------------------------------

        self.en_passant_target = None

        if piece.kind == "P":

            if abs(er - sr) == 2:
                self.en_passant_target = ((er + sr) // 2, sc)

        if record_history:
            self.last_move = move

            self.turn = self.opponent(self.turn)

    # --------------------------------------------------------
    # Game state
    # --------------------------------------------------------

    def game_state(self, color: Optional[str] = None) -> str:

        if color is None:
            color = self.turn

        legal = self.all_legal_moves(color)
        check = self.is_in_check(color)

        if legal:
            return "check" if check else "playing"

        if check:
            return "checkmate"

        return "stalemate"

    # --------------------------------------------------------
    # Material
    # --------------------------------------------------------

    def material_score(self) -> int:

        score = 0

        for row in self.board:
            for piece in row:

                if piece:

                    value = piece.value()

                    if piece.color == WHITE:
                        score += value
                    else:
                        score -= value

        return score


# ============================================================
# AI
# ============================================================


class ChessAI:
    """
    موتور ساده ولی واقعی Minimax + Alpha-Beta.

    AI سفید است.
    """

    def __init__(self, depth: int = 3):
        self.depth = depth

    # --------------------------------------------------------
    # Piece-square tables
    # --------------------------------------------------------

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

    def choose_move(self, board: Board) -> Optional[Move]:

        legal = board.all_legal_moves(WHITE)

        if not legal:
            return None

        best_score = -math.inf
        best_move = legal[0]

        # ترتیب‌دهی برای Alpha-Beta بهتر
        legal.sort(key=self.move_order_score, reverse=True)

        for move in legal:

            test = board.clone()
            test.apply_move(move, record_history=True)

            score = self.minimax(test, self.depth - 1, -math.inf, math.inf, False)

            if score > best_score:
                best_score = score
                best_move = move

        return best_move

    # --------------------------------------------------------
    # Minimax
    # --------------------------------------------------------

    def minimax(
        self, board: Board, depth: int, alpha: float, beta: float, maximizing: bool
    ) -> float:

        state = board.game_state(board.turn)

        if state == "checkmate":

            # اگر نوبت سفید است یعنی سفید مات شده.
            if board.turn == WHITE:
                return -1000000 - depth

            return 1000000 + depth

        if state == "stalemate":
            return 0

        if depth <= 0:
            return self.evaluate(board)

        color = WHITE if maximizing else BLACK

        moves = board.all_legal_moves(color)

        moves.sort(key=self.move_order_score, reverse=True)

        if maximizing:

            value = -math.inf

            for move in moves:

                child = board.clone()

                child.turn = color

                child.apply_move(move, record_history=True)

                value = max(value, self.minimax(child, depth - 1, alpha, beta, False))

                alpha = max(alpha, value)

                if beta <= alpha:
                    break

            return value

        else:

            value = math.inf

            for move in moves:

                child = board.clone()

                child.turn = color

                child.apply_move(move, record_history=True)

                value = min(value, self.minimax(child, depth - 1, alpha, beta, True))

                beta = min(beta, value)

                if beta <= alpha:
                    break

            return value

    # --------------------------------------------------------
    # Evaluation
    # --------------------------------------------------------

    def evaluate(self, board: Board) -> float:

        score = 0.0

        for row in range(8):
            for col in range(8):

                piece = board.board[row][col]

                if piece is None:
                    continue

                value = piece.value()

                positional = self.position_value(piece, row, col)

                if piece.color == WHITE:
                    score += value + positional
                else:
                    score -= value + positional

        # کمی پاداش برای کنترل مرکز
        center = [
            (3, 3),
            (3, 4),
            (4, 3),
            (4, 4),
        ]

        for row, col in center:

            piece = board.board[row][col]

            if piece:

                if piece.color == WHITE:
                    score += 8
                else:
                    score -= 8

        # پاداش برای کیش دادن حریف
        if board.is_in_check(BLACK):
            score += 35

        if board.is_in_check(WHITE):
            score -= 35

        return score

    def position_value(self, piece: Piece, row: int, col: int) -> float:

        if piece.kind == "P":
            table = self.PAWN_TABLE

        elif piece.kind == "N":
            table = self.KNIGHT_TABLE

        elif piece.kind == "B":
            table = self.BISHOP_TABLE

        else:
            return 0

        # جدول برای سفید از پایین به بالا است.
        # برای سیاه برعکس می‌شود.
        actual_row = row if piece.color == WHITE else 7 - row

        return table[actual_row][col]

    # --------------------------------------------------------
    # Move ordering
    # --------------------------------------------------------

    @staticmethod
    def move_order_score(move: Move) -> int:

        score = 0

        if move.captured:
            score += 10 * move.captured.value()

        if move.promotion:
            score += PIECE_VALUES[move.promotion]

        if move.is_castling:
            score += 50

        if move.is_en_passant:
            score += 100

        return score


# ============================================================
# GUI
# ============================================================


class ChessGame:
    """
    رابط گرافیکی Tkinter.

    سفید = کامپیوتر
    سیاه = کاربر
    """

    LIGHT = "#F0D9B5"
    DARK = "#B58863"

    SELECTED = "#D9C44A"
    LAST_MOVE = "#86B8D8"
    LEGAL_MOVE = "#7FAF72"
    CHECK_COLOR = "#D95C5C"

    PANEL = "#20242A"
    TEXT = "#F2F2F2"

    def __init__(self, root):

        self.root = root
        self.root.title("Professional Chess - Python")

        self.root.configure(bg=self.PANEL)

        self.root.resizable(False, False)

        self.board = Board()

        # عمق 3 برای اجرای نسبتاً سریع.
        self.ai = ChessAI(depth=3)

        self.selected_square = None
        self.selected_moves: List[Move] = []

        self.ai_thinking = False
        self.game_over = False

        self.square_size = 78

        self.create_ui()

        self.draw_board()

        # سفید شروع می‌کند.
        self.root.after(500, self.ai_move)

    # --------------------------------------------------------
    # UI
    # --------------------------------------------------------

    def create_ui(self):

        main = tk.Frame(self.root, bg=self.PANEL)

        main.pack(padx=18, pady=18)

        # عنوان
        title = tk.Label(
            main,
            text="♔  CHESS  ♚",
            font=("Segoe UI", 20, "bold"),
            bg=self.PANEL,
            fg=self.TEXT,
        )

        title.pack(pady=(0, 12))

        content = tk.Frame(main, bg=self.PANEL)

        content.pack()

        # سمت چپ صفحه
        left = tk.Frame(content, bg=self.PANEL)

        left.grid(row=0, column=0)

        # Canvas
        canvas_width = self.square_size * 8

        self.canvas = tk.Canvas(
            left, width=canvas_width, height=canvas_width, highlightthickness=0, bd=0
        )

        self.canvas.pack()

        self.canvas.bind("<Button-1>", self.on_board_click)

        # سمت راست
        side = tk.Frame(content, bg=self.PANEL, width=230)

        side.grid(row=0, column=1, sticky="ns", padx=(18, 0))

        side.grid_propagate(False)

        self.turn_label = tk.Label(
            side,
            text="",
            font=("Segoe UI", 13, "bold"),
            bg=self.PANEL,
            fg=self.TEXT,
            anchor="w",
        )

        self.turn_label.pack(fill="x", pady=(5, 15))

        self.status_label = tk.Label(
            side,
            text="",
            font=("Segoe UI", 11),
            bg=self.PANEL,
            fg=self.TEXT,
            justify="left",
            anchor="nw",
            wraplength=220,
        )

        self.status_label.pack(fill="x")

        tk.Label(
            side,
            text="Captured",
            font=("Segoe UI", 12, "bold"),
            bg=self.PANEL,
            fg=self.TEXT,
            anchor="w",
        ).pack(fill="x", pady=(25, 5))

        self.captured_label = tk.Label(
            side,
            text="",
            font=("Segoe UI Symbol", 20),
            bg=self.PANEL,
            fg=self.TEXT,
            justify="left",
            anchor="nw",
            wraplength=210,
        )

        self.captured_label.pack(fill="x")

        # دکمه New Game
        self.new_game_button = tk.Button(
            side,
            text="New Game",
            font=("Segoe UI", 11, "bold"),
            command=self.new_game,
            bg="#3C4652",
            fg="white",
            activebackground="#566474",
            activeforeground="white",
            relief="flat",
            padx=18,
            pady=9,
            cursor="hand2",
        )

        self.new_game_button.pack(side="bottom", fill="x", pady=(10, 0))

        # وضعیت
        self.update_status()

    # --------------------------------------------------------
    # Drawing
    # --------------------------------------------------------

    def draw_board(self):

        self.canvas.delete("all")

        for row in range(8):
            for col in range(8):

                x1 = col * self.square_size
                y1 = row * self.square_size

                x2 = x1 + self.square_size
                y2 = y1 + self.square_size

                color = self.LIGHT if (row + col) % 2 == 0 else self.DARK

                # Last move
                if self.board.last_move:

                    if (row, col) == self.board.last_move.start or (
                        row,
                        col,
                    ) == self.board.last_move.end:
                        color = self.LAST_MOVE

                # Selection
                if self.selected_square == (row, col):
                    color = self.SELECTED

                # Check highlight
                king = self.board.find_king(self.board.turn)

                if (
                    king
                    and king == (row, col)
                    and self.board.is_in_check(self.board.turn)
                ):
                    color = self.CHECK_COLOR

                self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline=color)

                # مختصات افقی
                if row == 7:
                    self.canvas.create_text(
                        x2 - 7,
                        y2 - 7,
                        text=FILES[col],
                        anchor="se",
                        font=("Segoe UI", 9, "bold"),
                        fill=("#6A452C" if (row + col) % 2 == 0 else "#F4E4C2"),
                    )

                # مختصات عمودی
                if col == 0:
                    self.canvas.create_text(
                        x1 + 7,
                        y1 + 7,
                        text=str(8 - row),
                        anchor="nw",
                        font=("Segoe UI", 9, "bold"),
                        fill=("#6A452C" if (row + col) % 2 == 0 else "#F4E4C2"),
                    )

        # Legal move markers
        for move in self.selected_moves:

            row, col = move.end

            cx = col * self.square_size + self.square_size / 2

            cy = row * self.square_size + self.square_size / 2

            target = self.board.board[row][col]

            if target is None:

                radius = 8

                self.canvas.create_oval(
                    cx - radius,
                    cy - radius,
                    cx + radius,
                    cy + radius,
                    fill=self.LEGAL_MOVE,
                    outline="",
                )

            else:

                radius = self.square_size / 2 - 6

                self.canvas.create_oval(
                    cx - radius,
                    cy - radius,
                    cx + radius,
                    cy + radius,
                    outline=self.LEGAL_MOVE,
                    width=5,
                )

        # Pieces
        for row in range(8):
            for col in range(8):

                piece = self.board.board[row][col]

                if piece is None:
                    continue

                x = col * self.square_size + self.square_size / 2

                y = row * self.square_size + self.square_size / 2

                self.canvas.create_text(
                    x,
                    y,
                    text=piece.symbol(),
                    font=("DejaVu Sans", 48),
                    fill=("#FFFFFF" if piece.color == WHITE else "#111111"),
                    tags="piece",
                )

        self.update_status()

    # --------------------------------------------------------
    # User click
    # --------------------------------------------------------

    def on_board_click(self, event):

        if self.ai_thinking or self.game_over:
            return

        # فقط سیاه کاربر است.
        if self.board.turn != BLACK:
            return

        col = event.x // self.square_size
        row = event.y // self.square_size

        if not self.board.inside(row, col):
            return

        clicked_piece = self.board.board[row][col]

        # ----------------------------------------------------
        # انتخاب مهره
        # ----------------------------------------------------

        if self.selected_square is None:

            if clicked_piece and clicked_piece.color == BLACK:
                self.select_piece(row, col)

            return

        # ----------------------------------------------------
        # اگر روی مهره سیاه دیگری کلیک شد
        # ----------------------------------------------------

        if clicked_piece and clicked_piece.color == BLACK:

            self.select_piece(row, col)

            return

        # ----------------------------------------------------
        # انتخاب مقصد
        # ----------------------------------------------------

        possible = [move for move in self.selected_moves if move.end == (row, col)]

        if not possible:

            self.selected_square = None
            self.selected_moves = []

            self.draw_board()

            return

        # اگر Promotion است، پنجره انتخاب نمایش داده شود.
        promotion_moves = [move for move in possible if move.promotion]

        if promotion_moves:

            # مقصد یکی است و چهار promotion داریم.
            self.show_promotion_dialog(promotion_moves)

        else:

            self.execute_user_move(possible[0])

    # --------------------------------------------------------
    # Select piece
    # --------------------------------------------------------

    def select_piece(self, row: int, col: int):

        self.selected_square = (row, col)

        self.selected_moves = self.board.legal_moves_for_piece(row, col)

        self.draw_board()

    # --------------------------------------------------------
    # User move
    # --------------------------------------------------------

    def execute_user_move(self, move: Move):

        self.board.apply_move(move, record_history=True)

        self.selected_square = None
        self.selected_moves = []

        self.draw_board()

        if self.check_game_over():
            return

        # نوبت AI
        self.ai_thinking = True

        self.draw_board()

        self.root.after(500, self.ai_move)

    # --------------------------------------------------------
    # Promotion dialog
    # --------------------------------------------------------

    def show_promotion_dialog(self, moves: List[Move]):

        dialog = tk.Toplevel(self.root)

        dialog.title("Promotion")

        dialog.configure(bg=self.PANEL)

        dialog.resizable(False, False)

        dialog.transient(self.root)

        dialog.grab_set()

        tk.Label(
            dialog,
            text="Choose promotion",
            font=("Segoe UI", 13, "bold"),
            bg=self.PANEL,
            fg=self.TEXT,
        ).pack(padx=20, pady=(20, 10))

        frame = tk.Frame(dialog, bg=self.PANEL)

        frame.pack(padx=15, pady=(0, 20))

        names = {
            "Q": "Queen",
            "R": "Rook",
            "B": "Bishop",
            "N": "Knight",
        }

        for move in moves:

            piece_symbol = UNICODE_PIECES[BLACK][move.promotion]

            button = tk.Button(
                frame,
                text=(piece_symbol + "\n" + names[move.promotion]),
                font=("Segoe UI Symbol", 18),
                width=7,
                height=2,
                bg="#3C4652",
                fg="white",
                activebackground="#566474",
                activeforeground="white",
                relief="flat",
                cursor="hand2",
                command=lambda m=move: (dialog.destroy(), self.execute_user_move(m)),
            )

            button.pack(side="left", padx=4)

    # --------------------------------------------------------
    # AI
    # --------------------------------------------------------

    def ai_move(self):

        if self.game_over:
            self.ai_thinking = False
            return

        if self.board.turn != WHITE:
            self.ai_thinking = False
            return

        self.status_label.config(text="Computer is thinking...")

        self.root.update_idletasks()

        # اجرای AI در همین thread است تا فقط استاندارد Python
        # استفاده شود. عمق 3 برای جلوگیری از کندی شدید.
        move = self.ai.choose_move(self.board)

        if move is None:

            self.ai_thinking = False

            self.check_game_over()

            return

        self.board.apply_move(move, record_history=True)

        self.ai_thinking = False

        self.draw_board()

        self.check_game_over()

    # --------------------------------------------------------
    # New Game
    # --------------------------------------------------------

    def new_game(self):

        self.board.reset()

        self.selected_square = None
        self.selected_moves = []

        self.ai_thinking = False
        self.game_over = False

        self.draw_board()

        # سفید دوباره شروع می‌کند.
        self.ai_thinking = True

        self.root.after(500, self.ai_move)

    # --------------------------------------------------------
    # Status
    # --------------------------------------------------------

    def update_status(self):

        if self.board.turn == WHITE:
            turn_text = "Turn: WHITE (Computer)"
        else:
            turn_text = "Turn: BLACK (You)"

        self.turn_label.config(text=turn_text)

        state = self.board.game_state(self.board.turn)

        if state == "check":
            status = "⚠ CHECK!\n" "The king is under attack."

        elif state == "checkmate":
            if self.board.turn == WHITE:
                status = "CHECKMATE\n" "Black wins!"
            else:
                status = "CHECKMATE\n" "White wins!"

        elif state == "stalemate":
            status = "STALEMATE\n" "The game is a draw."

        else:

            if self.ai_thinking:
                status = "Computer is thinking..."
            else:
                status = "Game in progress."

        self.status_label.config(text=status)

        # ----------------------------------------------------
        # Captured pieces
        # ----------------------------------------------------

        captured = []

        if self.board.captured_black:
            captured.append(
                "White captured: "
                + "".join(p.symbol() for p in self.board.captured_black)
            )

        if self.board.captured_white:
            captured.append(
                "Black captured: "
                + "".join(p.symbol() for p in self.board.captured_white)
            )

        self.captured_label.config(text="\n".join(captured) if captured else "None")

    # --------------------------------------------------------
    # Game over
    # --------------------------------------------------------

    def check_game_over(self) -> bool:

        state = self.board.game_state(self.board.turn)

        if state == "playing":
            return False

        if state == "check":

            # بازی هنوز ادامه دارد.
            self.draw_board()

            # اگر کاربر در کیش است هشدار بده.
            if self.board.turn == BLACK and not self.ai_thinking:
                self.root.after(
                    50,
                    lambda: messagebox.showwarning("Check", "Your king is in check!"),
                )

            return False

        self.game_over = True

        self.draw_board()

        if state == "checkmate":

            if self.board.turn == WHITE:
                message = (
                    "Checkmate!\n\n" "Congratulations! You defeated " "the computer."
                )
            else:
                message = "Checkmate!\n\n" "The computer wins."

            messagebox.showinfo("Game Over", message)

        elif state == "stalemate":

            messagebox.showinfo("Draw", "Stalemate!\n\n" "The game ends in a draw.")

        return True


# ============================================================
# Main
# ============================================================


def main():

    root = tk.Tk()

    ChessGame(root)

    root.mainloop()


if __name__ == "__main__":
    main()

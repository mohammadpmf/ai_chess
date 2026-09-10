import math
import copy
from dataclasses import dataclass
from typing import Optional, List, Tuple

import tkinter as tk
import customtkinter as ctk

# ============================================================
# CONFIGURATION
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
# PIECE
# ============================================================


@dataclass
class Piece:
    """
    Chess piece.

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
# MOVE
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

        result = f"{FILES[sc]}{8 - sr}" f"-{FILES[ec]}{8 - er}"

        if self.promotion:
            result += f"={self.promotion}"

        return result


# ============================================================
# BOARD / GAME LOGIC
# ============================================================


class Board:

    def __init__(self):
        self.reset()

    # --------------------------------------------------------
    # INITIALIZATION
    # --------------------------------------------------------

    def reset(self):

        self.board = [[None for _ in range(8)] for _ in range(8)]

        order = ["R", "N", "B", "Q", "K", "B", "N", "R"]

        for col, kind in enumerate(order):

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
        self.move_history = []

        self.captured_white = []
        self.captured_black = []

    # --------------------------------------------------------
    # HELPERS
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
    # KING
    # --------------------------------------------------------

    def find_king(self, color: str) -> Optional[Tuple[int, int]]:

        for row in range(8):
            for col in range(8):

                piece = self.board[row][col]

                if piece is not None and piece.color == color and piece.kind == "K":
                    return row, col

        return None

    # --------------------------------------------------------
    # ATTACK DETECTION
    # --------------------------------------------------------

    def is_square_attacked(self, row: int, col: int, by_color: str) -> bool:

        # Pawn attacks
        pawn_row = row + (1 if by_color == WHITE else -1)

        for dc in (-1, 1):

            c = col + dc

            if self.inside(pawn_row, c):

                piece = self.board[pawn_row][c]

                if piece and piece.color == by_color and piece.kind == "P":
                    return True

        # Knight attacks
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

        # King attacks
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

        # Rook / Queen
        for dr, dc in [
            (-1, 0),
            (1, 0),
            (0, -1),
            (0, 1),
        ]:

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

        # Bishop / Queen
        for dr, dc in [
            (-1, -1),
            (-1, 1),
            (1, -1),
            (1, 1),
        ]:

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
    # PSEUDO LEGAL MOVES
    # --------------------------------------------------------

    def pseudo_legal_moves_for_piece(self, row: int, col: int) -> List[Move]:

        piece = self.board[row][col]

        if piece is None:
            return []

        if piece.kind == "P":
            return self._pawn_moves(row, col, piece)

        if piece.kind == "N":
            return self._knight_moves(row, col, piece)

        if piece.kind == "B":
            return self._sliding_moves(
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

        if piece.kind == "R":
            return self._sliding_moves(
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

        if piece.kind == "Q":
            return self._sliding_moves(
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

        if piece.kind == "K":
            return self._king_moves(row, col, piece)

        return []

    # --------------------------------------------------------
    # PAWN
    # --------------------------------------------------------

    def _pawn_moves(self, row: int, col: int, piece: Piece) -> List[Move]:

        moves = []

        direction = -1 if piece.color == WHITE else 1
        start_row = 6 if piece.color == WHITE else 1
        promotion_row = 0 if piece.color == WHITE else 7

        one_row = row + direction

        # Move forward
        if self.inside(one_row, col) and self.board[one_row][col] is None:

            if one_row == promotion_row:

                for promotion in ("Q", "R", "B", "N"):

                    moves.append(
                        Move(
                            (row, col),
                            (one_row, col),
                            promotion=promotion,
                        )
                    )

            else:

                moves.append(
                    Move(
                        (row, col),
                        (one_row, col),
                    )
                )

            # Double move
            two_row = row + 2 * direction

            if (
                row == start_row
                and self.inside(two_row, col)
                and self.board[two_row][col] is None
            ):

                moves.append(
                    Move(
                        (row, col),
                        (two_row, col),
                    )
                )

        # Captures
        for dc in (-1, 1):

            new_col = col + dc

            if not self.inside(one_row, new_col):
                continue

            target = self.board[one_row][new_col]

            # Kings are never captured.
            if target and target.color != piece.color and target.kind != "K":

                if one_row == promotion_row:

                    for promotion in ("Q", "R", "B", "N"):

                        moves.append(
                            Move(
                                (row, col),
                                (one_row, new_col),
                                promotion=promotion,
                                captured=target,
                            )
                        )

                else:

                    moves.append(
                        Move(
                            (row, col),
                            (one_row, new_col),
                            captured=target,
                        )
                    )

            # En Passant
            if self.en_passant_target == (one_row, new_col):

                adjacent = self.board[row][new_col]

                if adjacent and adjacent.color != piece.color and adjacent.kind == "P":

                    moves.append(
                        Move(
                            (row, col),
                            (one_row, new_col),
                            is_en_passant=True,
                            captured=adjacent,
                        )
                    )

        return moves

    # --------------------------------------------------------
    # KNIGHT
    # --------------------------------------------------------

    def _knight_moves(self, row: int, col: int, piece: Piece) -> List[Move]:

        moves = []

        for dr, dc in [
            (-2, -1),
            (-2, 1),
            (-1, -2),
            (-1, 2),
            (1, -2),
            (1, 2),
            (2, -1),
            (2, 1),
        ]:

            r = row + dr
            c = col + dc

            if not self.inside(r, c):
                continue

            target = self.board[r][c]

            if target is None:

                moves.append(Move((row, col), (r, c)))

            elif target.color != piece.color and target.kind != "K":

                moves.append(
                    Move(
                        (row, col),
                        (r, c),
                        captured=target,
                    )
                )

        return moves

    # --------------------------------------------------------
    # SLIDING PIECES
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

                    if target.color != piece.color and target.kind != "K":

                        moves.append(
                            Move(
                                (row, col),
                                (r, c),
                                captured=target,
                            )
                        )

                    break

                r += dr
                c += dc

        return moves

    # --------------------------------------------------------
    # KING
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

                    # King cannot be captured.
                    if target.kind != "K":

                        moves.append(
                            Move(
                                (row, col),
                                (r, c),
                                captured=target,
                            )
                        )

        moves.extend(self._castling_moves(piece.color))

        return moves

    # --------------------------------------------------------
    # CASTLING
    # --------------------------------------------------------

    def _castling_moves(self, color: str) -> List[Move]:

        moves = []

        if self.is_in_check(color):
            return moves

        enemy = self.opponent(color)

        if color == WHITE:

            king = self.board[7][4]

            # Kingside
            rook = self.board[7][7]

            if (
                not self.white_king_moved
                and not self.white_rook_h_moved
                and king
                and king.color == WHITE
                and king.kind == "K"
                and rook
                and rook.color == WHITE
                and rook.kind == "R"
                and self.board[7][5] is None
                and self.board[7][6] is None
                and not self.is_square_attacked(7, 5, enemy)
                and not self.is_square_attacked(7, 6, enemy)
            ):

                moves.append(
                    Move(
                        (7, 4),
                        (7, 6),
                        is_castling=True,
                    )
                )

            # Queenside
            rook = self.board[7][0]

            if (
                not self.white_king_moved
                and not self.white_rook_a_moved
                and king
                and king.color == WHITE
                and king.kind == "K"
                and rook
                and rook.color == WHITE
                and rook.kind == "R"
                and self.board[7][1] is None
                and self.board[7][2] is None
                and self.board[7][3] is None
                and not self.is_square_attacked(7, 3, enemy)
                and not self.is_square_attacked(7, 2, enemy)
            ):

                moves.append(
                    Move(
                        (7, 4),
                        (7, 2),
                        is_castling=True,
                    )
                )

        else:

            king = self.board[0][4]

            # Kingside
            rook = self.board[0][7]

            if (
                not self.black_king_moved
                and not self.black_rook_h_moved
                and king
                and king.color == BLACK
                and king.kind == "K"
                and rook
                and rook.color == BLACK
                and rook.kind == "R"
                and self.board[0][5] is None
                and self.board[0][6] is None
                and not self.is_square_attacked(0, 5, enemy)
                and not self.is_square_attacked(0, 6, enemy)
            ):

                moves.append(
                    Move(
                        (0, 4),
                        (0, 6),
                        is_castling=True,
                    )
                )

            # Queenside
            rook = self.board[0][0]

            if (
                not self.black_king_moved
                and not self.black_rook_a_moved
                and king
                and king.color == BLACK
                and king.kind == "K"
                and rook
                and rook.color == BLACK
                and rook.kind == "R"
                and self.board[0][1] is None
                and self.board[0][2] is None
                and self.board[0][3] is None
                and not self.is_square_attacked(0, 3, enemy)
                and not self.is_square_attacked(0, 2, enemy)
            ):

                moves.append(
                    Move(
                        (0, 4),
                        (0, 2),
                        is_castling=True,
                    )
                )

        return moves

    # --------------------------------------------------------
    # LEGAL MOVES
    # --------------------------------------------------------

    def legal_moves_for_piece(self, row: int, col: int) -> List[Move]:

        piece = self.board[row][col]

        if piece is None:
            return []

        pseudo_moves = self.pseudo_legal_moves_for_piece(
            row,
            col,
        )

        legal_moves = []

        for move in pseudo_moves:

            test_board = self.clone()

            test_board.apply_move(
                move,
                record_history=False,
                switch_turn=False,
            )

            if not test_board.is_in_check(piece.color):

                legal_moves.append(move)

        return legal_moves

    def all_legal_moves(self, color: Optional[str] = None) -> List[Move]:

        if color is None:
            color = self.turn

        moves = []

        for row in range(8):
            for col in range(8):

                piece = self.board[row][col]

                if piece and piece.color == color:

                    moves.extend(
                        self.legal_moves_for_piece(
                            row,
                            col,
                        )
                    )

        return moves

    # --------------------------------------------------------
    # APPLY MOVE
    # --------------------------------------------------------

    def apply_move(
        self,
        move: Move,
        record_history: bool = True,
        switch_turn: bool = True,
    ):

        sr, sc = move.start
        er, ec = move.end

        piece = self.board[sr][sc]

        if piece is None:
            return

        captured_piece = None

        # Normal capture
        if not move.is_en_passant:

            target = self.board[er][ec]

            if target:

                captured_piece = target

                if record_history:

                    if target.color == WHITE:
                        self.captured_white.append(target)
                    else:
                        self.captured_black.append(target)

        # En passant
        else:

            captured_row = sr
            captured_col = ec

            captured_piece = self.board[captured_row][captured_col]

            if captured_piece:

                if record_history:

                    if captured_piece.color == WHITE:
                        self.captured_white.append(captured_piece)
                    else:
                        self.captured_black.append(captured_piece)

                self.board[captured_row][captured_col] = None

        # Move
        self.board[sr][sc] = None
        self.board[er][ec] = piece

        # Promotion
        if piece.kind == "P" and er in (0, 7):

            promotion = move.promotion or "Q"

            self.board[er][ec] = Piece(
                piece.color,
                promotion,
            )

        # Castling rook move
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

                if (sr, sc) == (7, 7):
                    self.white_rook_h_moved = True

            else:

                if (sr, sc) == (0, 0):
                    self.black_rook_a_moved = True

                if (sr, sc) == (0, 7):
                    self.black_rook_h_moved = True

        # Update castling rights if original rook is captured
        if captured_piece and captured_piece.kind == "R":

            if (er, ec) == (7, 0):
                self.white_rook_a_moved = True

            elif (er, ec) == (7, 7):
                self.white_rook_h_moved = True

            elif (er, ec) == (0, 0):
                self.black_rook_a_moved = True

            elif (er, ec) == (0, 7):
                self.black_rook_h_moved = True

        # En passant
        self.en_passant_target = None

        if piece.kind == "P" and abs(er - sr) == 2:

            self.en_passant_target = (
                (er + sr) // 2,
                sc,
            )

        if record_history:

            self.last_move = move
            self.move_history.append(move.notation())

        if switch_turn:
            self.turn = self.opponent(self.turn)

    # --------------------------------------------------------
    # GAME STATE
    # --------------------------------------------------------

    def game_state(self, color: Optional[str] = None) -> str:

        if color is None:
            color = self.turn

        moves = self.all_legal_moves(color)
        check = self.is_in_check(color)

        if not moves:

            if check:
                return "checkmate"

            return "stalemate"

        if check:
            return "check"

        return "playing"


# ============================================================
# CHESS AI
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

    def choose_move(self, board: Board) -> Optional[Move]:

        moves = board.all_legal_moves(WHITE)

        if not moves:
            return None

        moves.sort(
            key=self.move_order_score,
            reverse=True,
        )

        best_score = -math.inf
        best_move = moves[0]

        for move in moves:

            child = board.clone()

            child.apply_move(
                move,
                record_history=False,
                switch_turn=True,
            )

            score = self.minimax(
                child,
                self.depth - 1,
                -math.inf,
                math.inf,
                maximizing=False,
            )

            if score > best_score:

                best_score = score
                best_move = move

        return best_move

    def minimax(
        self,
        board: Board,
        depth: int,
        alpha: float,
        beta: float,
        maximizing: bool,
    ) -> float:

        state = board.game_state(board.turn)

        if state == "checkmate":

            if board.turn == WHITE:
                return -1_000_000 - depth

            return 1_000_000 + depth

        if state == "stalemate":
            return 0

        if depth == 0:
            return self.evaluate(board)

        color = WHITE if maximizing else BLACK

        moves = board.all_legal_moves(color)

        moves.sort(
            key=self.move_order_score,
            reverse=True,
        )

        if maximizing:

            value = -math.inf

            for move in moves:

                child = board.clone()
                child.turn = WHITE

                child.apply_move(
                    move,
                    record_history=False,
                    switch_turn=True,
                )

                value = max(
                    value,
                    self.minimax(
                        child,
                        depth - 1,
                        alpha,
                        beta,
                        False,
                    ),
                )

                alpha = max(alpha, value)

                if alpha >= beta:
                    break

            return value

        else:

            value = math.inf

            for move in moves:

                child = board.clone()
                child.turn = BLACK

                child.apply_move(
                    move,
                    record_history=False,
                    switch_turn=True,
                )

                value = min(
                    value,
                    self.minimax(
                        child,
                        depth - 1,
                        alpha,
                        beta,
                        True,
                    ),
                )

                beta = min(beta, value)

                if alpha >= beta:
                    break

            return value

    def evaluate(self, board: Board) -> float:

        score = 0

        for row in range(8):
            for col in range(8):

                piece = board.board[row][col]

                if piece is None:
                    continue

                value = piece.value()
                positional = self.position_value(
                    piece,
                    row,
                    col,
                )

                if piece.color == WHITE:
                    score += value + positional
                else:
                    score -= value + positional

        # Center control bonus
        for row, col in [
            (3, 3),
            (3, 4),
            (4, 3),
            (4, 4),
        ]:

            piece = board.board[row][col]

            if piece:

                if piece.color == WHITE:
                    score += 8
                else:
                    score -= 8

        if board.is_in_check(BLACK):
            score += 30

        if board.is_in_check(WHITE):
            score -= 30

        return score

    def position_value(
        self,
        piece: Piece,
        row: int,
        col: int,
    ) -> int:

        table = None

        if piece.kind == "P":
            table = self.PAWN_TABLE

        elif piece.kind == "N":
            table = self.KNIGHT_TABLE

        elif piece.kind == "B":
            table = self.BISHOP_TABLE

        if table is None:
            return 0

        actual_row = row if piece.color == WHITE else 7 - row

        return table[actual_row][col]

    @staticmethod
    def move_order_score(move: Move):

        score = 0

        if move.captured:
            score += 10 * move.captured.value()

        if move.promotion:
            score += PIECE_VALUES[move.promotion]

        if move.is_castling:
            score += 50

        return score


# ============================================================
# MODERN GUI
# ============================================================


class ChessGame:

    BG = "#111827"
    PANEL = "#1F2937"
    PANEL_2 = "#273449"

    TEXT = "#F9FAFB"
    MUTED = "#9CA3AF"

    LIGHT = "#EAD8B5"
    DARK = "#9C6B4E"

    SELECTED = "#F6C945"
    LAST_MOVE = "#77A7D9"
    LEGAL_MOVE = "#65B891"
    CHECK = "#D9534F"

    WHITE_PIECE = "#F8F8F8"
    BLACK_PIECE = "#161616"

    def __init__(self, root):

        self.root = root

        self.root.title("Chess AI")

        self.root.configure(fg_color=self.BG)

        self.root.resizable(
            False,
            False,
        )

        self.board = Board()
        self.ai = ChessAI(depth=3)

        self.square_size = 78

        self.selected_square = None
        self.selected_moves = []

        self.ai_thinking = False
        self.game_over = False

        self.create_ui()
        self.draw_board()

        self.ai_thinking = True

        self.root.after(
            600,
            self.ai_move,
        )

    # --------------------------------------------------------
    # UI
    # --------------------------------------------------------

    def create_ui(self):

        main = ctk.CTkFrame(
            self.root,
            fg_color="transparent",
        )

        main.pack(
            padx=24,
            pady=24,
        )

        # Header
        header = ctk.CTkFrame(
            main,
            fg_color="transparent",
        )

        header.pack(
            fill="x",
            pady=(0, 18),
        )

        ctk.CTkLabel(
            header,
            text="♔ CHESS ARENA ♚",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=28,
                weight="bold",
            ),
            text_color=self.TEXT,
        ).pack(side="left")

        self.game_badge = ctk.CTkLabel(
            header,
            text="  AI MODE  ",
            corner_radius=10,
            fg_color="#334155",
            text_color="#BFDBFE",
            font=ctk.CTkFont(
                size=12,
                weight="bold",
            ),
        )

        self.game_badge.pack(
            side="right",
            pady=5,
        )

        # Content
        content = ctk.CTkFrame(
            main,
            fg_color="transparent",
        )

        content.pack()

        # ----------------------------------------------------
        # Board panel
        # ----------------------------------------------------

        board_panel = ctk.CTkFrame(
            content,
            corner_radius=18,
            fg_color=self.PANEL,
        )

        board_panel.grid(
            row=0,
            column=0,
            padx=(0, 20),
        )

        board_inner = tk.Frame(
            board_panel,
            bg="#0B1019",
            padx=10,
            pady=10,
        )

        board_inner.pack(
            padx=10,
            pady=10,
        )

        size = self.square_size * 8

        self.canvas = tk.Canvas(
            board_inner,
            width=size,
            height=size,
            bg="#0B1019",
            highlightthickness=0,
            bd=0,
        )

        self.canvas.pack()

        self.canvas.bind(
            "<Button-1>",
            self.on_board_click,
        )

        # ----------------------------------------------------
        # Sidebar
        # ----------------------------------------------------

        side = ctk.CTkFrame(
            content,
            width=260,
            height=size + 20,
            corner_radius=18,
            fg_color=self.PANEL,
        )

        side.grid(
            row=0,
            column=1,
            sticky="ns",
        )

        side.grid_propagate(False)

        # Turn card
        self.turn_card = ctk.CTkFrame(
            side,
            corner_radius=12,
            fg_color=self.PANEL_2,
        )

        self.turn_card.pack(
            fill="x",
            padx=16,
            pady=(16, 10),
        )

        self.turn_label = ctk.CTkLabel(
            self.turn_card,
            text="",
            font=ctk.CTkFont(
                size=16,
                weight="bold",
            ),
            text_color=self.TEXT,
        )

        self.turn_label.pack(
            padx=14,
            pady=(12, 2),
        )

        self.status_label = ctk.CTkLabel(
            self.turn_card,
            text="",
            font=ctk.CTkFont(
                size=12,
            ),
            text_color=self.MUTED,
            wraplength=210,
        )

        self.status_label.pack(
            padx=14,
            pady=(0, 12),
        )

        # Captured pieces
        ctk.CTkLabel(
            side,
            text="CAPTURED PIECES",
            font=ctk.CTkFont(
                size=12,
                weight="bold",
            ),
            text_color=self.MUTED,
        ).pack(
            anchor="w",
            padx=18,
            pady=(12, 5),
        )

        self.captured_label = ctk.CTkLabel(
            side,
            text="None",
            justify="left",
            anchor="w",
            font=ctk.CTkFont(
                family="Segoe UI Symbol",
                size=22,
            ),
            text_color=self.TEXT,
            wraplength=220,
        )

        self.captured_label.pack(
            fill="x",
            padx=18,
        )

        # Last move
        ctk.CTkLabel(
            side,
            text="LAST MOVE",
            font=ctk.CTkFont(
                size=12,
                weight="bold",
            ),
            text_color=self.MUTED,
        ).pack(
            anchor="w",
            padx=18,
            pady=(18, 5),
        )

        self.last_move_label = ctk.CTkLabel(
            side,
            text="Game started",
            anchor="w",
            text_color=self.TEXT,
            font=ctk.CTkFont(
                size=14,
            ),
        )

        self.last_move_label.pack(
            fill="x",
            padx=18,
        )

        # Spacer
        spacer = ctk.CTkFrame(
            side,
            fg_color="transparent",
        )

        spacer.pack(
            fill="both",
            expand=True,
        )

        # New game button
        self.new_game_button = ctk.CTkButton(
            side,
            text="♟  NEW GAME",
            height=46,
            corner_radius=12,
            font=ctk.CTkFont(
                size=14,
                weight="bold",
            ),
            command=self.new_game,
        )

        self.new_game_button.pack(
            fill="x",
            padx=16,
            pady=16,
        )

    # --------------------------------------------------------
    # DRAW BOARD
    # --------------------------------------------------------

    def draw_board(self):

        self.canvas.delete("all")

        checked_king = None

        if self.board.is_in_check(self.board.turn):
            checked_king = self.board.find_king(self.board.turn)

        for row in range(8):
            for col in range(8):

                x1 = col * self.square_size
                y1 = row * self.square_size

                x2 = x1 + self.square_size
                y2 = y1 + self.square_size

                color = self.LIGHT if (row + col) % 2 == 0 else self.DARK

                # Last move
                if self.board.last_move:

                    if (row, col) in (
                        self.board.last_move.start,
                        self.board.last_move.end,
                    ):
                        color = self.LAST_MOVE

                # Selected square
                if self.selected_square == (row, col):
                    color = self.SELECTED

                # Check
                if checked_king == (row, col):
                    color = self.CHECK

                self.canvas.create_rectangle(
                    x1,
                    y1,
                    x2,
                    y2,
                    fill=color,
                    outline=color,
                )

                # Rank labels
                if col == 0:

                    label_color = self.DARK if (row + col) % 2 == 0 else self.LIGHT

                    self.canvas.create_text(
                        x1 + 7,
                        y1 + 7,
                        text=str(8 - row),
                        anchor="nw",
                        font=(
                            "Segoe UI",
                            9,
                            "bold",
                        ),
                        fill=label_color,
                    )

                # File labels
                if row == 7:

                    label_color = self.DARK if (row + col) % 2 == 0 else self.LIGHT

                    self.canvas.create_text(
                        x2 - 7,
                        y2 - 6,
                        text=FILES[col],
                        anchor="se",
                        font=(
                            "Segoe UI",
                            9,
                            "bold",
                        ),
                        fill=label_color,
                    )

        # Legal move indicators
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

                margin = 6

                self.canvas.create_rectangle(
                    col * self.square_size + margin,
                    row * self.square_size + margin,
                    (col + 1) * self.square_size - margin,
                    (row + 1) * self.square_size - margin,
                    outline=self.LEGAL_MOVE,
                    width=4,
                )

        # Pieces
        for row in range(8):
            for col in range(8):

                piece = self.board.board[row][col]

                if piece is None:
                    continue

                x = col * self.square_size + self.square_size / 2

                y = row * self.square_size + self.square_size / 2 + 2

                # Small shadow
                self.canvas.create_text(
                    x + 1,
                    y + 2,
                    text=piece.symbol(),
                    font=(
                        "Segoe UI Symbol",
                        50,
                    ),
                    fill="#000000",
                )

                # Piece
                self.canvas.create_text(
                    x,
                    y,
                    text=piece.symbol(),
                    font=(
                        "Segoe UI Symbol",
                        50,
                    ),
                    fill=(
                        self.WHITE_PIECE if piece.color == WHITE else self.BLACK_PIECE
                    ),
                )

        self.update_status()

    # --------------------------------------------------------
    # CLICK HANDLER
    # --------------------------------------------------------

    def on_board_click(self, event):

        if self.ai_thinking or self.game_over:
            return

        if self.board.turn != BLACK:
            return

        col = event.x // self.square_size
        row = event.y // self.square_size

        if not self.board.inside(row, col):
            return

        clicked_piece = self.board.board[row][col]

        # Select a black piece
        if self.selected_square is None:

            if clicked_piece and clicked_piece.color == BLACK:

                self.select_piece(row, col)

            return

        # Select another black piece
        if clicked_piece and clicked_piece.color == BLACK:

            self.select_piece(row, col)
            return

        # Find destination
        candidates = [move for move in self.selected_moves if move.end == (row, col)]

        if not candidates:

            self.selected_square = None
            self.selected_moves = []

            self.draw_board()
            return

        promotion_moves = [move for move in candidates if move.promotion]

        if promotion_moves:
            self.show_promotion_dialog(promotion_moves)
        else:
            self.execute_user_move(candidates[0])

    # --------------------------------------------------------
    # SELECT PIECE
    # --------------------------------------------------------

    def select_piece(
        self,
        row,
        col,
    ):

        self.selected_square = (
            row,
            col,
        )

        self.selected_moves = self.board.legal_moves_for_piece(
            row,
            col,
        )

        self.draw_board()

    # --------------------------------------------------------
    # USER MOVE
    # --------------------------------------------------------

    def execute_user_move(
        self,
        move: Move,
    ):

        self.board.apply_move(
            move,
            record_history=True,
            switch_turn=True,
        )

        self.selected_square = None
        self.selected_moves = []

        self.draw_board()

        if self.check_game_over():
            return

        self.ai_thinking = True

        self.update_status()

        self.root.after(
            600,
            self.ai_move,
        )

    # --------------------------------------------------------
    # PROMOTION DIALOG
    # --------------------------------------------------------

    def show_promotion_dialog(
        self,
        moves: List[Move],
    ):

        dialog = ctk.CTkToplevel(self.root)

        dialog.title("Pawn Promotion")
        dialog.geometry("420x210")
        dialog.resizable(False, False)

        dialog.transient(self.root)
        dialog.grab_set()

        ctk.CTkLabel(
            dialog,
            text="Choose your promotion",
            font=ctk.CTkFont(
                size=20,
                weight="bold",
            ),
        ).pack(pady=(22, 15))

        frame = ctk.CTkFrame(
            dialog,
            fg_color="transparent",
        )

        frame.pack()

        names = {
            "Q": "Queen",
            "R": "Rook",
            "B": "Bishop",
            "N": "Knight",
        }

        for move in moves:

            button = ctk.CTkButton(
                frame,
                text=(
                    f"{UNICODE_PIECES[BLACK][move.promotion]}\n"
                    f"{names[move.promotion]}"
                ),
                width=85,
                height=90,
                corner_radius=12,
                font=ctk.CTkFont(
                    size=15,
                    weight="bold",
                ),
                command=lambda m=move: (
                    dialog.destroy(),
                    self.execute_user_move(m),
                ),
            )

            button.pack(
                side="left",
                padx=4,
            )

    # --------------------------------------------------------
    # AI MOVE
    # --------------------------------------------------------

    def ai_move(self):

        if self.game_over:
            self.ai_thinking = False
            return

        if self.board.turn != WHITE:
            self.ai_thinking = False
            return

        move = self.ai.choose_move(self.board)

        if move is None:

            self.ai_thinking = False
            self.check_game_over()

            return

        self.board.apply_move(
            move,
            record_history=True,
            switch_turn=True,
        )

        self.ai_thinking = False

        self.draw_board()

        self.check_game_over()

    # --------------------------------------------------------
    # STATUS
    # --------------------------------------------------------

    def update_status(self):

        if self.game_over:
            return

        if self.ai_thinking:

            turn_text = "WHITE • COMPUTER"

            status = "AI is calculating its next move..."

        elif self.board.turn == WHITE:

            turn_text = "WHITE • COMPUTER"

            status = "Computer's turn"

        else:

            turn_text = "BLACK • YOU"

            status = "Your turn — select a piece"

        state = self.board.game_state(self.board.turn)

        if state == "check":
            status = "⚠ CHECK! The king is under attack."

        elif state == "checkmate":
            status = "CHECKMATE"

        elif state == "stalemate":
            status = "STALEMATE — DRAW"

        self.turn_label.configure(text=turn_text)

        self.status_label.configure(text=status)

        if self.board.last_move:

            self.last_move_label.configure(text=self.board.last_move.notation())

        else:

            self.last_move_label.configure(text="Game started")

        parts = []

        if self.board.captured_black:

            symbols = "".join(piece.symbol() for piece in self.board.captured_black)

            parts.append(f"White lost:\n{symbols}")

        if self.board.captured_white:

            symbols = "".join(piece.symbol() for piece in self.board.captured_white)

            parts.append(f"Black lost:\n{symbols}")

        self.captured_label.configure(text=("\n\n".join(parts) if parts else "None"))

    # --------------------------------------------------------
    # GAME OVER
    # --------------------------------------------------------

    def check_game_over(self) -> bool:

        state = self.board.game_state(self.board.turn)

        if state == "playing":
            return False

        if state == "check":

            self.draw_board()

            if self.board.turn == BLACK:

                self.root.after(
                    100,
                    lambda: self.show_message(
                        "CHECK",
                        "Your king is in check!",
                    ),
                )

            return False

        self.game_over = True

        self.draw_board()

        if state == "checkmate":

            if self.board.turn == WHITE:

                self.show_message(
                    "CHECKMATE",
                    "Congratulations!\n\n" "You defeated the computer.",
                )

            else:

                self.show_message(
                    "CHECKMATE",
                    "The computer wins this game.",
                )

        elif state == "stalemate":

            self.show_message(
                "DRAW",
                "Stalemate.\n\n" "The game ends in a draw.",
            )

        return True

    # --------------------------------------------------------
    # MODERN MESSAGE DIALOG
    # --------------------------------------------------------

    def show_message(
        self,
        title,
        message,
    ):

        dialog = ctk.CTkToplevel(self.root)

        dialog.title(title)
        dialog.geometry("400x240")
        dialog.resizable(False, False)

        dialog.transient(self.root)
        dialog.grab_set()

        ctk.CTkLabel(
            dialog,
            text=title,
            font=ctk.CTkFont(
                size=24,
                weight="bold",
            ),
        ).pack(pady=(30, 15))

        ctk.CTkLabel(
            dialog,
            text=message,
            justify="center",
            font=ctk.CTkFont(
                size=15,
            ),
        ).pack(padx=25, pady=(0, 20))

        ctk.CTkButton(
            dialog,
            text="OK",
            width=140,
            height=40,
            command=dialog.destroy,
        ).pack()

    # --------------------------------------------------------
    # NEW GAME
    # --------------------------------------------------------

    def new_game(self):

        self.board.reset()

        self.selected_square = None
        self.selected_moves = []

        self.ai_thinking = True
        self.game_over = False

        self.draw_board()

        self.root.after(
            600,
            self.ai_move,
        )


# ============================================================
# MAIN
# ============================================================


def main():

    root = ctk.CTk()

    ChessGame(root)

    root.mainloop()


if __name__ == "__main__":
    main()

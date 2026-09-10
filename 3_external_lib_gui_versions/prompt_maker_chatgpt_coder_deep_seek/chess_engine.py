"""
Chess Rules Engine - Complete implementation of standard chess rules.
No external dependencies.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import copy


class Color(Enum):
    WHITE = "white"
    BLACK = "black"

    @property
    def opposite(self) -> "Color":
        return Color.BLACK if self is Color.WHITE else Color.WHITE


class PieceType(Enum):
    PAWN = "P"
    KNIGHT = "N"
    BISHOP = "B"
    ROOK = "R"
    QUEEN = "Q"
    KING = "K"


PIECE_SYMBOLS = {
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

PIECE_VALUES = {
    PieceType.PAWN: 100,
    PieceType.KNIGHT: 320,
    PieceType.BISHOP: 330,
    PieceType.ROOK: 500,
    PieceType.QUEEN: 900,
    PieceType.KING: 20000,
}


@dataclass
class Piece:
    color: Color
    piece_type: PieceType

    def symbol(self) -> str:
        return PIECE_SYMBOLS[(self.color, self.piece_type)]

    def __repr__(self) -> str:
        return f"{self.color.value[0].upper()}{self.piece_type.value}"


@dataclass
class Move:
    from_sq: tuple[int, int]
    to_sq: tuple[int, int]
    piece: Optional[Piece] = None
    captured: Optional[Piece] = None
    promotion: Optional[PieceType] = None
    is_en_passant: bool = False
    is_castling: bool = False
    is_double_pawn: bool = False

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Move):
            return NotImplemented
        return (
            self.from_sq == other.from_sq
            and self.to_sq == other.to_sq
            and self.promotion == other.promotion
        )


class Board:
    def __init__(self) -> None:
        self.grid: list[list[Optional[Piece]]] = [
            [None for _ in range(8)] for _ in range(8)
        ]

    @classmethod
    def initial(cls) -> "Board":
        b = cls()
        back_rank = [
            PieceType.ROOK,
            PieceType.KNIGHT,
            PieceType.BISHOP,
            PieceType.QUEEN,
            PieceType.KING,
            PieceType.BISHOP,
            PieceType.KNIGHT,
            PieceType.ROOK,
        ]
        for col in range(8):
            b.grid[0][col] = Piece(Color.BLACK, back_rank[col])
            b.grid[1][col] = Piece(Color.BLACK, PieceType.PAWN)
            b.grid[6][col] = Piece(Color.WHITE, PieceType.PAWN)
            b.grid[7][col] = Piece(Color.WHITE, back_rank[col])
        return b

    def copy(self) -> "Board":
        new = Board()
        for r in range(8):
            for c in range(8):
                p = self.grid[r][c]
                new.grid[r][c] = Piece(p.color, p.piece_type) if p else None
        return new

    @staticmethod
    def in_bounds(r: int, c: int) -> bool:
        return 0 <= r < 8 and 0 <= c < 8

    def piece_at(self, r: int, c: int) -> Optional[Piece]:
        if not self.in_bounds(r, c):
            return None
        return self.grid[r][c]

    def find_king(self, color: Color) -> Optional[tuple[int, int]]:
        for r in range(8):
            for c in range(8):
                p = self.grid[r][c]
                if p and p.color is color and p.piece_type is PieceType.KING:
                    return (r, c)
        return None


@dataclass
class GameState:
    board: Board
    side_to_move: Color
    castling_rights: dict
    en_passant_target: Optional[tuple[int, int]]
    halfmove_clock: int
    fullmove_number: int

    def copy(self) -> "GameState":
        return GameState(
            board=self.board.copy(),
            side_to_move=self.side_to_move,
            castling_rights={
                Color.WHITE: dict(self.castling_rights[Color.WHITE]),
                Color.BLACK: dict(self.castling_rights[Color.BLACK]),
            },
            en_passant_target=self.en_passant_target,
            halfmove_clock=self.halfmove_clock,
            fullmove_number=self.fullmove_number,
        )


class GameStatus(Enum):
    ONGOING = "ongoing"
    CHECK = "check"
    CHECKMATE = "checkmate"
    STALEMATE = "stalemate"
    DRAW_FIFTY = "draw_fifty"
    DRAW_REPETITION = "draw_repetition"
    DRAW_MATERIAL = "draw_material"
    RESIGNED = "resigned"


class ChessGame:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.state = GameState(
            board=Board.initial(),
            side_to_move=Color.WHITE,
            castling_rights={
                Color.WHITE: {"K": True, "Q": True},
                Color.BLACK: {"K": True, "Q": True},
            },
            en_passant_target=None,
            halfmove_clock=0,
            fullmove_number=1,
        )
        self.history: list = []
        self.position_history: list[str] = [self._position_key()]
        self.status: GameStatus = GameStatus.ONGOING
        self.resigned_by: Optional[Color] = None

    def clone(self) -> "ChessGame":
        """Deep, independent copy of the entire game.

        Used by the AI so that search never mutates the live game object
        that the GUI is rendering from.
        """
        new = ChessGame.__new__(ChessGame)
        new.state = self.state.copy()
        new.history = list(self.history)
        new.position_history = list(self.position_history)
        new.status = self.status
        new.resigned_by = self.resigned_by
        return new

    # ---------------------------------------------------------------
    def _position_key(self) -> str:
        rows = []
        for r in range(8):
            for c in range(8):
                p = self.state.board.grid[r][c]
                if p:
                    rows.append(f"{r}{c}{p.color.value[0]}{p.piece_type.value}")
                else:
                    rows.append(f"{r}{c}.")
        cast = self.state.castling_rights
        cast_str = (
            ("K" if cast[Color.WHITE]["K"] else "")
            + ("Q" if cast[Color.WHITE]["Q"] else "")
            + ("k" if cast[Color.BLACK]["K"] else "")
            + ("q" if cast[Color.BLACK]["Q"] else "")
            + (
                "-"
                if not any(
                    [
                        cast[Color.WHITE]["K"],
                        cast[Color.WHITE]["Q"],
                        cast[Color.BLACK]["K"],
                        cast[Color.BLACK]["Q"],
                    ]
                )
                else ""
            )
        )
        ep = self.state.en_passant_target
        ep_str = f"{ep[0]}{ep[1]}" if ep else "-"
        return "".join(rows) + f"|{self.state.side_to_move.value}|{cast_str}|{ep_str}"

    # ---------------------------------------------------------------
    def _pseudo_legal_moves(self, color: Color) -> list[Move]:
        moves: list[Move] = []
        for r in range(8):
            for c in range(8):
                p = self.state.board.grid[r][c]
                if p and p.color is color:
                    moves.extend(self._piece_moves(r, c, p))
        return moves

    def _piece_moves(self, r: int, c: int, piece: Piece) -> list[Move]:
        if piece.piece_type is PieceType.PAWN:
            return self._pawn_moves(r, c, piece)
        if piece.piece_type is PieceType.KNIGHT:
            return self._knight_moves(r, c, piece)
        if piece.piece_type is PieceType.BISHOP:
            return self._sliding_moves(
                r, c, piece, [(1, 1), (1, -1), (-1, 1), (-1, -1)]
            )
        if piece.piece_type is PieceType.ROOK:
            return self._sliding_moves(r, c, piece, [(1, 0), (-1, 0), (0, 1), (0, -1)])
        if piece.piece_type is PieceType.QUEEN:
            return self._sliding_moves(
                r,
                c,
                piece,
                [
                    (1, 1),
                    (1, -1),
                    (-1, 1),
                    (-1, -1),
                    (1, 0),
                    (-1, 0),
                    (0, 1),
                    (0, -1),
                ],
            )
        if piece.piece_type is PieceType.KING:
            return self._king_moves(r, c, piece)
        return []

    def _pawn_moves(self, r: int, c: int, piece: Piece) -> list[Move]:
        moves: list[Move] = []
        direction = -1 if piece.color is Color.WHITE else 1
        start_row = 6 if piece.color is Color.WHITE else 1
        promo_row = 0 if piece.color is Color.WHITE else 7

        nr = r + direction
        if Board.in_bounds(nr, c) and self.state.board.grid[nr][c] is None:
            if nr == promo_row:
                for pt in (
                    PieceType.QUEEN,
                    PieceType.ROOK,
                    PieceType.BISHOP,
                    PieceType.KNIGHT,
                ):
                    moves.append(Move((r, c), (nr, c), piece=piece, promotion=pt))
            else:
                moves.append(Move((r, c), (nr, c), piece=piece))
            if r == start_row:
                nr2 = r + 2 * direction
                if self.state.board.grid[nr2][c] is None:
                    moves.append(
                        Move((r, c), (nr2, c), piece=piece, is_double_pawn=True)
                    )

        for dc in (-1, 1):
            nc = c + dc
            if not Board.in_bounds(nr, nc):
                continue
            target = self.state.board.grid[nr][nc]
            if target and target.color is not piece.color:
                if nr == promo_row:
                    for pt in (
                        PieceType.QUEEN,
                        PieceType.ROOK,
                        PieceType.BISHOP,
                        PieceType.KNIGHT,
                    ):
                        moves.append(
                            Move(
                                (r, c),
                                (nr, nc),
                                piece=piece,
                                captured=target,
                                promotion=pt,
                            )
                        )
                else:
                    moves.append(Move((r, c), (nr, nc), piece=piece, captured=target))
            elif self.state.en_passant_target == (nr, nc):
                cap_piece = self.state.board.grid[r][nc]
                if (
                    cap_piece
                    and cap_piece.color is not piece.color
                    and cap_piece.piece_type is PieceType.PAWN
                ):
                    moves.append(
                        Move(
                            (r, c),
                            (nr, nc),
                            piece=piece,
                            captured=cap_piece,
                            is_en_passant=True,
                        )
                    )
        return moves

    def _knight_moves(self, r: int, c: int, piece: Piece) -> list[Move]:
        moves: list[Move] = []
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
            nr, nc = r + dr, c + dc
            if not Board.in_bounds(nr, nc):
                continue
            target = self.state.board.grid[nr][nc]
            if target is None:
                moves.append(Move((r, c), (nr, nc), piece=piece))
            elif target.color is not piece.color:
                moves.append(Move((r, c), (nr, nc), piece=piece, captured=target))
        return moves

    def _sliding_moves(
        self, r: int, c: int, piece: Piece, directions: list[tuple[int, int]]
    ) -> list[Move]:
        moves: list[Move] = []
        for dr, dc in directions:
            nr, nc = r + dr, c + dc
            while Board.in_bounds(nr, nc):
                target = self.state.board.grid[nr][nc]
                if target is None:
                    moves.append(Move((r, c), (nr, nc), piece=piece))
                elif target.color is not piece.color:
                    moves.append(Move((r, c), (nr, nc), piece=piece, captured=target))
                    break
                else:
                    break
                nr += dr
                nc += dc
        return moves

    def _king_moves(self, r: int, c: int, piece: Piece) -> list[Move]:
        moves: list[Move] = []
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = r + dr, c + dc
                if not Board.in_bounds(nr, nc):
                    continue
                target = self.state.board.grid[nr][nc]
                if target is None:
                    moves.append(Move((r, c), (nr, nc), piece=piece))
                elif target.color is not piece.color:
                    moves.append(Move((r, c), (nr, nc), piece=piece, captured=target))
        moves.extend(self._castling_moves(r, c, piece))
        return moves

    def _castling_moves(self, r: int, c: int, piece: Piece) -> list[Move]:
        moves: list[Move] = []
        color = piece.color
        if self.is_in_check(color):
            return moves
        home_row = 7 if color is Color.WHITE else 0
        if r != home_row or c != 4:
            return moves
        rights = self.state.castling_rights[color]

        if rights["K"]:
            if (
                self.state.board.grid[home_row][5] is None
                and self.state.board.grid[home_row][6] is None
            ):
                rook = self.state.board.grid[home_row][7]
                if rook and rook.color is color and rook.piece_type is PieceType.ROOK:
                    if not self._square_attacked(
                        home_row, 5, color.opposite
                    ) and not self._square_attacked(home_row, 6, color.opposite):
                        moves.append(
                            Move((r, c), (home_row, 6), piece=piece, is_castling=True)
                        )

        if rights["Q"]:
            if (
                self.state.board.grid[home_row][3] is None
                and self.state.board.grid[home_row][2] is None
                and self.state.board.grid[home_row][1] is None
            ):
                rook = self.state.board.grid[home_row][0]
                if rook and rook.color is color and rook.piece_type is PieceType.ROOK:
                    if not self._square_attacked(
                        home_row, 3, color.opposite
                    ) and not self._square_attacked(home_row, 2, color.opposite):
                        moves.append(
                            Move((r, c), (home_row, 2), piece=piece, is_castling=True)
                        )
        return moves

    # ---------------------------------------------------------------
    def _square_attacked(
        self, row: int, col: int, by_color: Color, board: Optional[Board] = None
    ) -> bool:
        if board is None:
            board = self.state.board

        pawn_dir = -1 if by_color is Color.WHITE else 1
        for dc in (-1, 1):
            pr, pc = row - pawn_dir, col - dc
            if Board.in_bounds(pr, pc):
                p = board.grid[pr][pc]
                if p and p.color is by_color and p.piece_type is PieceType.PAWN:
                    return True

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
            nr, nc = row + dr, col + dc
            if Board.in_bounds(nr, nc):
                p = board.grid[nr][nc]
                if p and p.color is by_color and p.piece_type is PieceType.KNIGHT:
                    return True

        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = row + dr, col + dc
                if Board.in_bounds(nr, nc):
                    p = board.grid[nr][nc]
                    if p and p.color is by_color and p.piece_type is PieceType.KING:
                        return True

        for dr, dc in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            nr, nc = row + dr, col + dc
            while Board.in_bounds(nr, nc):
                p = board.grid[nr][nc]
                if p:
                    if p.color is by_color and p.piece_type in (
                        PieceType.ROOK,
                        PieceType.QUEEN,
                    ):
                        return True
                    break
                nr += dr
                nc += dc

        for dr, dc in [(1, 1), (1, -1), (-1, 1), (-1, -1)]:
            nr, nc = row + dr, col + dc
            while Board.in_bounds(nr, nc):
                p = board.grid[nr][nc]
                if p:
                    if p.color is by_color and p.piece_type in (
                        PieceType.BISHOP,
                        PieceType.QUEEN,
                    ):
                        return True
                    break
                nr += dr
                nc += dc

        return False

    def is_in_check(self, color: Color, board: Optional[Board] = None) -> bool:
        if board is None:
            board = self.state.board
        king_pos = board.find_king(color)
        if king_pos is None:
            return False
        return self._square_attacked(king_pos[0], king_pos[1], color.opposite, board)

    # ---------------------------------------------------------------
    def _apply_move_to_state(self, state: GameState, move: Move) -> GameState:
        new = state.copy()
        b = new.board
        r, c = move.from_sq
        nr, nc = move.to_sq
        piece = b.grid[r][c]
        assert piece is not None

        b.grid[nr][nc] = piece
        b.grid[r][c] = None

        if move.is_en_passant:
            b.grid[r][nc] = None

        if move.promotion is not None:
            b.grid[nr][nc] = Piece(piece.color, move.promotion)

        if move.is_castling:
            home_row = r
            if nc == 6:
                rook = b.grid[home_row][7]
                b.grid[home_row][7] = None
                b.grid[home_row][5] = rook
            else:
                rook = b.grid[home_row][0]
                b.grid[home_row][0] = None
                b.grid[home_row][3] = rook

        if piece.piece_type is PieceType.KING:
            new.castling_rights[piece.color]["K"] = False
            new.castling_rights[piece.color]["Q"] = False
        elif piece.piece_type is PieceType.ROOK:
            home_row = 7 if piece.color is Color.WHITE else 0
            if r == home_row and c == 0:
                new.castling_rights[piece.color]["Q"] = False
            elif r == home_row and c == 7:
                new.castling_rights[piece.color]["K"] = False
        if move.captured and move.captured.piece_type is PieceType.ROOK:
            cap_color = move.captured.color
            home_row = 7 if cap_color is Color.WHITE else 0
            if nr == home_row and nc == 0:
                new.castling_rights[cap_color]["Q"] = False
            elif nr == home_row and nc == 7:
                new.castling_rights[cap_color]["K"] = False

        if move.is_double_pawn:
            mid_row = (r + nr) // 2
            new.en_passant_target = (mid_row, c)
        else:
            new.en_passant_target = None

        if piece.piece_type is PieceType.PAWN or move.captured is not None:
            new.halfmove_clock = 0
        else:
            new.halfmove_clock = state.halfmove_clock + 1

        if state.side_to_move is Color.BLACK:
            new.fullmove_number = state.fullmove_number + 1

        new.side_to_move = state.side_to_move.opposite
        return new

    # ---------------------------------------------------------------
    def legal_moves(self, color: Optional[Color] = None) -> list[Move]:
        if color is None:
            color = self.state.side_to_move
        pseudo = self._pseudo_legal_moves(color)
        legal: list[Move] = []
        for mv in pseudo:
            new_state = self._apply_move_to_state(self.state, mv)
            if not self.is_in_check(color, new_state.board):
                legal.append(mv)
        return legal

    def legal_moves_from(self, r: int, c: int) -> list[Move]:
        piece = self.state.board.grid[r][c]
        if piece is None or piece.color is not self.state.side_to_move:
            return []
        return [m for m in self.legal_moves() if m.from_sq == (r, c)]

    # ---------------------------------------------------------------
    def _move_to_san(self, move: Move, legal_moves_before: list[Move]) -> str:
        piece = move.piece
        assert piece is not None

        if move.is_castling:
            san = "O-O" if move.to_sq[1] == 6 else "O-O-O"
        elif piece.piece_type is PieceType.PAWN:
            if move.captured:
                san = (
                    f"{chr(ord('a') + move.from_sq[1])}x"
                    f"{chr(ord('a') + move.to_sq[1])}{8 - move.to_sq[0]}"
                )
            else:
                san = f"{chr(ord('a') + move.to_sq[1])}{8 - move.to_sq[0]}"
            if move.promotion is not None:
                san += f"={move.promotion.value}"
        else:
            letter = piece.piece_type.value
            same_target = [
                m
                for m in legal_moves_before
                if m.to_sq == move.to_sq
                and m.from_sq != move.from_sq
                and m.piece is not None
                and m.piece.piece_type is piece.piece_type
                and m.piece.color is piece.color
            ]
            disamb = ""
            if same_target:
                same_file = any(m.from_sq[1] == move.from_sq[1] for m in same_target)
                same_rank = any(m.from_sq[0] == move.from_sq[0] for m in same_target)
                if not same_file:
                    disamb = chr(ord("a") + move.from_sq[1])
                elif not same_rank:
                    disamb = str(8 - move.from_sq[0])
                else:
                    disamb = chr(ord("a") + move.from_sq[1]) + str(8 - move.from_sq[0])
            cap = "x" if move.captured else ""
            san = (
                f"{letter}{disamb}{cap}"
                f"{chr(ord('a') + move.to_sq[1])}{8 - move.to_sq[0]}"
            )

        new_state = self._apply_move_to_state(self.state, move)
        opp = self.state.side_to_move.opposite
        if self.is_in_check(opp, new_state.board):
            saved_state = self.state
            self.state = new_state
            try:
                opp_moves = self.legal_moves(opp)
            finally:
                self.state = saved_state
            san += "#" if not opp_moves else "+"
        return san

    # ---------------------------------------------------------------
    def make_move(self, move: Move) -> bool:
        legal = self.legal_moves()
        matched: Optional[Move] = None
        for m in legal:
            if (
                m.from_sq == move.from_sq
                and m.to_sq == move.to_sq
                and m.promotion == move.promotion
            ):
                matched = m
                break
        if matched is None:
            return False

        san = self._move_to_san(matched, legal)
        prev_state = self.state.copy()
        new_state = self._apply_move_to_state(self.state, matched)
        self.state = new_state
        self.history.append((prev_state, matched, san))
        self.position_history.append(self._position_key())
        self._update_status()
        return True

    def _update_status(self) -> None:
        if self.resigned_by is not None:
            self.status = GameStatus.RESIGNED
            return

        color = self.state.side_to_move
        moves = self.legal_moves(color)
        in_check = self.is_in_check(color)

        if not moves:
            if in_check:
                self.status = GameStatus.CHECKMATE
            else:
                self.status = GameStatus.STALEMATE
            return

        if self.state.halfmove_clock >= 100:
            self.status = GameStatus.DRAW_FIFTY
            return

        current_key = self._position_key()
        if self.position_history.count(current_key) >= 3:
            self.status = GameStatus.DRAW_REPETITION
            return

        if self._insufficient_material():
            self.status = GameStatus.DRAW_MATERIAL
            return

        self.status = GameStatus.CHECK if in_check else GameStatus.ONGOING

    def _insufficient_material(self) -> bool:
        pieces: list[tuple[Color, PieceType]] = []
        for r in range(8):
            for c in range(8):
                p = self.state.board.grid[r][c]
                if p:
                    pieces.append((p.color, p.piece_type))
        non_kings = [pt for (_, pt) in pieces if pt is not PieceType.KING]
        if not non_kings:
            return True
        if len(non_kings) == 1:
            return non_kings[0] in (PieceType.KNIGHT, PieceType.BISHOP)
        if len(non_kings) == 2:
            types = sorted(non_kings)
            if types == [PieceType.BISHOP, PieceType.BISHOP]:
                bishop_squares = []
                for r in range(8):
                    for c in range(8):
                        p = self.state.board.grid[r][c]
                        if p and p.piece_type is PieceType.BISHOP:
                            bishop_squares.append((r + c) % 2)
                if len(bishop_squares) == 2 and bishop_squares[0] == bishop_squares[1]:
                    return True
        return False

    def undo(self) -> bool:
        if not self.history:
            return False
        prev_state, _, _ = self.history.pop()
        self.state = prev_state
        if self.position_history:
            self.position_history.pop()
        self.resigned_by = None
        self._update_status()
        return True

    def resign(self, color: Color) -> None:
        self.resigned_by = color
        self.status = GameStatus.RESIGNED

    # ---------------------------------------------------------------
    def winner(self) -> Optional[Color]:
        if self.status is GameStatus.CHECKMATE:
            return self.state.side_to_move.opposite
        if self.status is GameStatus.RESIGNED and self.resigned_by is not None:
            return self.resigned_by.opposite
        return None

    def result_text(self) -> str:
        s = self.status
        if s is GameStatus.CHECKMATE:
            w = self.winner()
            return f"Checkmate! {'White' if w is Color.WHITE else 'Black'} wins."
        if s is GameStatus.STALEMATE:
            return "Stalemate! Draw."
        if s is GameStatus.DRAW_FIFTY:
            return "Draw by fifty-move rule."
        if s is GameStatus.DRAW_REPETITION:
            return "Draw by threefold repetition."
        if s is GameStatus.DRAW_MATERIAL:
            return "Draw by insufficient material."
        if s is GameStatus.RESIGNED:
            w = self.winner()
            if w is None:
                return "Game resigned."
            return (
                f"{'Black' if self.resigned_by is Color.BLACK else 'White'} resigned. "
                f"{'White' if w is Color.WHITE else 'Black'} wins."
            )
        return ""

    def board(self) -> Board:
        return self.state.board

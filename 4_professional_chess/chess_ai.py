"""Chess AI: Minimax with Alpha-Beta pruning and positional evaluation."""

from __future__ import annotations
import random
from typing import Optional
from chess_engine import (
    ChessGame,
    Move,
    Piece,
    PieceType,
    Color,
    GameStatus,
    PIECE_VALUES,
)

# Piece-square tables (from White's perspective, row 0 = rank 8)
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
    [-40, -20, 0, 0, 0, 0, -20, -40],
    [-30, 0, 10, 15, 15, 10, 0, -30],
    [-30, 5, 15, 20, 20, 15, 5, -30],
    [-30, 0, 15, 20, 20, 15, 0, -30],
    [-30, 5, 10, 15, 15, 10, 5, -30],
    [-40, -20, 0, 5, 5, 0, -20, -40],
    [-50, -40, -30, -30, -30, -30, -40, -50],
]

BISHOP_TABLE = [
    [-20, -10, -10, -10, -10, -10, -10, -20],
    [-10, 0, 0, 0, 0, 0, 0, -10],
    [-10, 0, 5, 10, 10, 5, 0, -10],
    [-10, 5, 5, 10, 10, 5, 5, -10],
    [-10, 0, 10, 10, 10, 10, 0, -10],
    [-10, 10, 10, 10, 10, 10, 10, -10],
    [-10, 5, 0, 0, 0, 0, 5, -10],
    [-20, -10, -10, -10, -10, -10, -10, -20],
]

ROOK_TABLE = [
    [0, 0, 0, 0, 0, 0, 0, 0],
    [5, 10, 10, 10, 10, 10, 10, 5],
    [-5, 0, 0, 0, 0, 0, 0, -5],
    [-5, 0, 0, 0, 0, 0, 0, -5],
    [-5, 0, 0, 0, 0, 0, 0, -5],
    [-5, 0, 0, 0, 0, 0, 0, -5],
    [-5, 0, 0, 0, 0, 0, 0, -5],
    [0, 0, 0, 5, 5, 0, 0, 0],
]

QUEEN_TABLE = [
    [-20, -10, -10, -5, -5, -10, -10, -20],
    [-10, 0, 0, 0, 0, 0, 0, -10],
    [-10, 0, 5, 5, 5, 5, 0, -10],
    [-5, 0, 5, 5, 5, 5, 0, -5],
    [0, 0, 5, 5, 5, 5, 0, -5],
    [-10, 5, 5, 5, 5, 5, 0, -10],
    [-10, 0, 5, 0, 0, 0, 0, -10],
    [-20, -10, -10, -5, -5, -10, -10, -20],
]

KING_MID_TABLE = [
    [-30, -40, -40, -50, -50, -40, -40, -30],
    [-30, -40, -40, -50, -50, -40, -40, -30],
    [-30, -40, -40, -50, -50, -40, -40, -30],
    [-30, -40, -40, -50, -50, -40, -40, -30],
    [-20, -30, -30, -40, -40, -30, -30, -20],
    [-10, -20, -20, -20, -20, -20, -20, -10],
    [20, 20, 0, 0, 0, 0, 20, 20],
    [20, 30, 10, 0, 0, 10, 30, 20],
]

TABLES = {
    PieceType.PAWN: PAWN_TABLE,
    PieceType.KNIGHT: KNIGHT_TABLE,
    PieceType.BISHOP: BISHOP_TABLE,
    PieceType.ROOK: ROOK_TABLE,
    PieceType.QUEEN: QUEEN_TABLE,
    PieceType.KING: KING_MID_TABLE,
}


class ChessAI:
    """Minimax with alpha-beta pruning."""

    def __init__(self, difficulty: str = "medium") -> None:
        self.set_difficulty(difficulty)

    def set_difficulty(self, difficulty: str) -> None:
        d = difficulty.lower()
        self.difficulty = d
        if d == "easy":
            self.depth = 2
            self.randomness = 60  # add noise
        elif d == "hard":
            self.depth = 4
            self.randomness = 0
        else:  # medium
            self.depth = 3
            self.randomness = 15

    # ---------------------------------------------------------------
    # Public: pick a move for the side to move in game
    # ---------------------------------------------------------------
    def choose_move(self, game: ChessGame) -> Optional[Move]:
        moves = game.legal_moves()
        if not moves:
            return None
        color = game.state.side_to_move
        scored: list[tuple[float, Move]] = []
        for mv in moves:
            new_state = game._apply_move_to_state(game.state, mv)
            # Temporarily swap state for evaluation
            saved = game.state
            game.state = new_state
            try:
                score = -self._negamax(
                    game, self.depth - 1, -float("inf"), float("inf"), color.opposite
                )
            finally:
                game.state = saved
            # Small random noise for variety
            score += random.uniform(-self.randomness, self.randomness)
            scored.append((score, mv))
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[0][1]

    # ---------------------------------------------------------------
    # Negamax with alpha-beta
    # ---------------------------------------------------------------
    def _negamax(
        self, game: ChessGame, depth: int, alpha: float, beta: float, color: Color
    ) -> float:
        # Terminal check
        if depth == 0:
            return self._quiescence(game, alpha, beta, color, 3)

        # Check game over
        moves = game.legal_moves(color)
        if not moves:
            if game.is_in_check(color):
                return -100000 + (self.depth - depth)  # prefer faster mate
            return 0  # stalemate

        # Move ordering: captures first
        moves = self._order_moves(moves)

        best = -float("inf")
        for mv in moves:
            new_state = game._apply_move_to_state(game.state, mv)
            saved = game.state
            game.state = new_state
            try:
                score = -self._negamax(game, depth - 1, -beta, -alpha, color.opposite)
            finally:
                game.state = saved
            if score > best:
                best = score
            if best > alpha:
                alpha = best
            if alpha >= beta:
                break
        return best

    def _quiescence(
        self, game: ChessGame, alpha: float, beta: float, color: Color, depth: int
    ) -> float:
        stand = self._evaluate(game, color)
        if depth == 0:
            return stand
        if stand >= beta:
            return beta
        if stand > alpha:
            alpha = stand

        moves = game.legal_moves(color)
        # Only captures & promotions
        tactical = [m for m in moves if m.captured or m.promotion]
        tactical = self._order_moves(tactical)

        for mv in tactical:
            new_state = game._apply_move_to_state(game.state, mv)
            saved = game.state
            game.state = new_state
            try:
                score = -self._quiescence(
                    game, -beta, -alpha, color.opposite, depth - 1
                )
            finally:
                game.state = saved
            if score >= beta:
                return beta
            if score > alpha:
                alpha = score
        return alpha

    def _order_moves(self, moves: list[Move]) -> list[Move]:
        def score(m: Move) -> int:
            s = 0
            if m.captured is not None:
                s += (
                    10 * PIECE_VALUES[m.captured.piece_type]
                    - PIECE_VALUES[m.piece.piece_type]
                )
            if m.promotion is not None:
                s += PIECE_VALUES[m.promotion]
            return s

        return sorted(moves, key=score, reverse=True)

    # ---------------------------------------------------------------
    # Evaluation
    # ---------------------------------------------------------------
    def _evaluate(self, game: ChessGame, color: Color) -> float:
        """Static evaluation from `color`'s perspective."""
        board = game.state.board
        score = 0
        white_bishops = 0
        black_bishops = 0
        white_pawns_files = [0] * 8
        black_pawns_files = [0] * 8

        for r in range(8):
            for c in range(8):
                p = board.grid[r][c]
                if p is None:
                    continue
                val = PIECE_VALUES[p.piece_type]
                table = TABLES[p.piece_type]
                # For white, row index directly; for black, mirror
                if p.color is Color.WHITE:
                    positional = table[r][c]
                else:
                    positional = table[7 - r][c]
                total = val + positional

                if p.color is Color.WHITE:
                    score += total
                    if p.piece_type is PieceType.BISHOP:
                        white_bishops += 1
                    if p.piece_type is PieceType.PAWN:
                        white_pawns_files[c] += 1
                else:
                    score -= total
                    if p.piece_type is PieceType.BISHOP:
                        black_bishops += 1
                    if p.piece_type is PieceType.PAWN:
                        black_pawns_files[c] += 1

        # Bishop pair bonus
        if white_bishops >= 2:
            score += 30
        if black_bishops >= 2:
            score -= 30

        # Doubled pawns penalty
        for f in range(8):
            if white_pawns_files[f] > 1:
                score -= 15 * (white_pawns_files[f] - 1)
            if black_pawns_files[f] > 1:
                score += 15 * (black_pawns_files[f] - 1)

        # Mobility
        mob_w = len(game._pseudo_legal_moves(Color.WHITE))
        mob_b = len(game._pseudo_legal_moves(Color.BLACK))
        score += (mob_w - mob_b) * 2

        # Return from `color`'s perspective
        if color is Color.WHITE:
            return score
        return -score

"""Tkinter GUI for the chess game. Black at bottom (player view)."""

from __future__ import annotations
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Optional

from chess_engine import (
    ChessGame,
    Move,
    Piece,
    PieceType,
    Color,
    GameStatus,
    PIECE_SYMBOLS,
)
from chess_ai import ChessAI

# ---------- Colors ----------
COLOR_LIGHT = "#eedfcc"
COLOR_DARK = "#b58863"
COLOR_HIGHLIGHT = "#f7ec74"  # selected / destination
COLOR_CHECK = "#e57373"  # king in check
COLOR_LAST_MOVE = "#d4c17f"
BG_MAIN = "#2c2c2c"
BG_SIDEBAR = "#1f1f1f"
FG_TEXT = "#f0f0f0"
FG_MUTED = "#a0a0a0"
ACCENT = "#4a90d9"

SQUARE_SIZE = 78
BOARD_SIZE = SQUARE_SIZE * 8


class ChessGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Chess — You (Black) vs Computer (White)")
        self.root.configure(bg=BG_MAIN)

        self.game = ChessGame()
        self.ai = ChessAI("medium")
        self.selected: Optional[tuple[int, int]] = None
        self.legal_destinations: list[Move] = []
        self.last_move: Optional[Move] = None
        self.ai_thinking = False
        self.game_over = False

        self._build_ui()
        self._render_board()

        # White (computer) moves first
        self.root.after(500, self._computer_move)

    # ---------------------------------------------------------------
    # UI construction
    # ---------------------------------------------------------------
    def _build_ui(self) -> None:
        container = tk.Frame(self.root, bg=BG_MAIN)
        container.pack(padx=18, pady=18)

        # Board frame
        board_frame = tk.Frame(container, bg=BG_MAIN)
        board_frame.grid(row=0, column=0, padx=(0, 18))

        self.canvas = tk.Canvas(
            board_frame,
            width=BOARD_SIZE,
            height=BOARD_SIZE,
            highlightthickness=0,
            bg=BG_MAIN,
        )
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self._on_click)

        # Sidebar
        sidebar = tk.Frame(container, bg=BG_SIDEBAR, width=300)
        sidebar.grid(row=0, column=1, sticky="n")
        sidebar.grid_propagate(False)

        tk.Label(
            sidebar,
            text="♞ CHESS ♞",
            font=("Segoe UI", 20, "bold"),
            bg=BG_SIDEBAR,
            fg=ACCENT,
        ).pack(pady=(18, 6))

        players = tk.Frame(sidebar, bg=BG_SIDEBAR)
        players.pack(fill="x", padx=18, pady=(6, 12))
        tk.Label(
            players,
            text="Computer — White",
            font=("Segoe UI", 11),
            bg=BG_SIDEBAR,
            fg=FG_TEXT,
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            players,
            text="You — Black",
            font=("Segoe UI", 11, "bold"),
            bg=BG_SIDEBAR,
            fg=FG_TEXT,
            anchor="w",
        ).pack(fill="x")

        tk.Frame(sidebar, bg="#3a3a3a", height=1).pack(fill="x", padx=18)

        self.turn_label = tk.Label(
            sidebar,
            text="White to move",
            font=("Segoe UI", 13, "bold"),
            bg=BG_SIDEBAR,
            fg=ACCENT,
        )
        self.turn_label.pack(pady=(14, 4))

        self.status_label = tk.Label(
            sidebar,
            text="",
            font=("Segoe UI", 11),
            bg=BG_SIDEBAR,
            fg="#ff7675",
            wraplength=260,
        )
        self.status_label.pack(pady=(0, 10))

        self.last_move_label = tk.Label(
            sidebar,
            text="Last move: —",
            font=("Segoe UI", 10),
            bg=BG_SIDEBAR,
            fg=FG_MUTED,
        )
        self.last_move_label.pack(pady=(0, 4))

        self.move_count_label = tk.Label(
            sidebar, text="Move: 1", font=("Segoe UI", 10), bg=BG_SIDEBAR, fg=FG_MUTED
        )
        self.move_count_label.pack(pady=(0, 12))

        tk.Label(
            sidebar,
            text="Move history",
            font=("Segoe UI", 11, "bold"),
            bg=BG_SIDEBAR,
            fg=FG_TEXT,
        ).pack(anchor="w", padx=18)

        hist_frame = tk.Frame(sidebar, bg=BG_SIDEBAR)
        hist_frame.pack(fill="both", expand=True, padx=18, pady=(6, 10))
        scrollbar = tk.Scrollbar(hist_frame)
        scrollbar.pack(side="right", fill="y")
        self.history_box = tk.Listbox(
            hist_frame,
            yscrollcommand=scrollbar.set,
            bg="#151515",
            fg=FG_TEXT,
            selectbackground=ACCENT,
            font=("Consolas", 11),
            borderwidth=0,
            highlightthickness=0,
            activestyle="none",
        )
        self.history_box.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.history_box.yview)

        # Difficulty selector
        diff_frame = tk.Frame(sidebar, bg=BG_SIDEBAR)
        diff_frame.pack(fill="x", padx=18, pady=(4, 4))
        tk.Label(
            diff_frame,
            text="Difficulty:",
            font=("Segoe UI", 10),
            bg=BG_SIDEBAR,
            fg=FG_TEXT,
        ).pack(side="left")
        self.diff_var = tk.StringVar(value="Medium")
        diff_menu = ttk.Combobox(
            diff_frame,
            textvariable=self.diff_var,
            values=["Easy", "Medium", "Hard"],
            state="readonly",
            width=9,
        )
        diff_menu.pack(side="right")
        diff_menu.bind("<<ComboboxSelected>>", self._on_difficulty_change)

        # Buttons
        btn_frame = tk.Frame(sidebar, bg=BG_SIDEBAR)
        btn_frame.pack(fill="x", padx=18, pady=(8, 18))

        self._make_button(btn_frame, "New Game", self._new_game, ACCENT)
        self._make_button(btn_frame, "Undo", self._undo, "#3d8b40")
        self._make_button(btn_frame, "Resign", self._resign, "#b54545")

    def _make_button(self, parent: tk.Frame, text: str, cmd, color: str) -> None:
        b = tk.Button(
            parent,
            text=text,
            command=cmd,
            bg=color,
            fg="white",
            activebackground=color,
            activeforeground="white",
            relief="flat",
            font=("Segoe UI", 10, "bold"),
            cursor="hand2",
            padx=8,
            pady=6,
            borderwidth=0,
        )
        b.pack(side="left", fill="x", expand=True, padx=3)

    # ---------------------------------------------------------------
    # Board rendering (black at bottom)
    # ---------------------------------------------------------------
    def _display_square(self, row: int, col: int) -> tuple[int, int]:
        """Convert internal (row,col) to display coords with black at bottom.

        Internal: row 0 = rank 8, col 0 = file a.
        For black player view we rotate 180 degrees:
        display_row = 7 - row, display_col = 7 - col.
        """
        return (7 - row, 7 - col)

    def _internal_square(self, disp_row: int, disp_col: int) -> tuple[int, int]:
        return (7 - disp_row, 7 - disp_col)

    def _render_board(self) -> None:
        self.canvas.delete("all")

        # Draw squares
        for dr in range(8):
            for dc in range(8):
                x1 = dc * SQUARE_SIZE
                y1 = dr * SQUARE_SIZE
                x2 = x1 + SQUARE_SIZE
                y2 = y1 + SQUARE_SIZE
                # Determine internal color: standard chess board
                ir, ic = self._internal_square(dr, dc)
                is_light = (ir + ic) % 2 == 0  # a1 (row 7, col 0) sum 7 -> odd
                # Actually a1 is dark. (7+0)%2 = 1 -> odd -> should be dark.
                # So light when (ir+ic)%2 == 0? Let's check h1: (7+7)=14 even -> light. Correct.
                color = COLOR_LIGHT if is_light else COLOR_DARK
                self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="")

        # Highlight last move
        if self.last_move is not None:
            for sq in (self.last_move.from_sq, self.last_move.to_sq):
                self._fill_square(sq, COLOR_LAST_MOVE)

        # Highlight selected square
        if self.selected is not None:
            self._fill_square(self.selected, COLOR_HIGHLIGHT)

        # Highlight king in check
        if (
            self.game.status in (GameStatus.CHECK, GameStatus.CHECKMATE)
            and not self.game_over
        ):
            king_sq = self.game.state.board.find_king(self.game.state.side_to_move)
            if king_sq:
                self._fill_square(king_sq, COLOR_CHECK)

        # Draw pieces
        for r in range(8):
            for c in range(8):
                p = self.game.state.board.grid[r][c]
                if p is None:
                    continue
                dr, dc = self._display_square(r, c)
                x = dc * SQUARE_SIZE + SQUARE_SIZE // 2
                y = dr * SQUARE_SIZE + SQUARE_SIZE // 2
                symbol = PIECE_SYMBOLS[(p.color, p.piece_type)]
                # Text color contrast
                if p.color is Color.WHITE:
                    fill = "#ffffff"
                    shadow = "#444444"
                else:
                    fill = "#111111"
                    shadow = "#888888"
                # Shadow for depth
                self.canvas.create_text(
                    x + 1, y + 2, text=symbol, font=("Segoe UI Symbol", 46), fill=shadow
                )
                self.canvas.create_text(
                    x, y, text=symbol, font=("Segoe UI Symbol", 46), fill=fill
                )

        # Highlight move destinations
        for mv in self.legal_destinations:
            dr, dc = self._display_square(*mv.to_sq)
            cx = dc * SQUARE_SIZE + SQUARE_SIZE // 2
            cy = dr * SQUARE_SIZE + SQUARE_SIZE // 2
            if mv.captured is not None:
                # Ring for capture
                r_out = SQUARE_SIZE // 2 - 6
                self.canvas.create_oval(
                    cx - r_out,
                    cy - r_out,
                    cx + r_out,
                    cy + r_out,
                    outline="#d64848",
                    width=4,
                )
            else:
                r_dot = 9
                self.canvas.create_oval(
                    cx - r_dot,
                    cy - r_dot,
                    cx + r_dot,
                    cy + r_dot,
                    fill="#4caf50",
                    outline="",
                )

        # Coordinates (files a-h at bottom, ranks 1-8 on left for black view)
        # For black view, file letters go h..a left-to-right and ranks 1..8 top-to-bottom
        for i in range(8):
            file_label = chr(ord("h") - i)  # h g f e d c b a
            self.canvas.create_text(
                i * SQUARE_SIZE + 8,
                BOARD_SIZE - 8,
                text=file_label,
                fill="#2b2b2b",
                font=("Segoe UI", 9, "bold"),
                anchor="sw",
            )
            rank_label = str(i + 1)
            self.canvas.create_text(
                8,
                i * SQUARE_SIZE + 8,
                text=rank_label,
                fill="#f5f5f5",
                font=("Segoe UI", 9, "bold"),
                anchor="nw",
            )

        # Update sidebar
        self._update_sidebar()

    def _fill_square(self, sq: tuple[int, int], color: str) -> None:
        dr, dc = self._display_square(*sq)
        x1 = dc * SQUARE_SIZE
        y1 = dr * SQUARE_SIZE
        self.canvas.create_rectangle(
            x1, y1, x1 + SQUARE_SIZE, y1 + SQUARE_SIZE, fill=color, outline=""
        )

    # ---------------------------------------------------------------
    # Sidebar updates
    # ---------------------------------------------------------------
    def _update_sidebar(self) -> None:
        st = self.game.status
        if self.game_over:
            if st is GameStatus.CHECKMATE:
                w = self.game.winner()
                self.turn_label.config(
                    text=f"Checkmate — {'White' if w is Color.WHITE else 'Black'} wins"
                )
            elif st is GameStatus.RESIGNED:
                self.turn_label.config(text="Resigned")
            else:
                self.turn_label.config(text="Game over")
            self.status_label.config(text=self.game.result_text())
        else:
            side = self.game.state.side_to_move
            if side is Color.WHITE:
                self.turn_label.config(
                    text="Computer thinking..." if self.ai_thinking else "White to move"
                )
            else:
                self.turn_label.config(text="Your turn (Black)")
            if st is GameStatus.CHECK:
                self.status_label.config(text="Check!")
            elif st is GameStatus.ONGOING:
                self.status_label.config(text="")

        if self.last_move is not None:
            from_sq = self._sq_name(self.last_move.from_sq)
            to_sq = self._sq_name(self.last_move.to_sq)
            san = self.game.history[-1][2] if self.game.history else ""
            self.last_move_label.config(text=f"Last: {from_sq}→{to_sq}  ({san})")
        else:
            self.last_move_label.config(text="Last move: —")

        self.move_count_label.config(text=f"Move: {self.game.state.fullmove_number}")

        # History box
        self.history_box.delete(0, tk.END)
        h = self.game.history
        i = 0
        move_num = 1
        while i < len(h):
            white_san = h[i][2]
            black_san = h[i + 1][2] if i + 1 < len(h) else ""
            self.history_box.insert(
                tk.END, f"{move_num:>3}. {white_san:<8} {black_san}"
            )
            i += 2
            move_num += 1
        if self.history_box.size() > 0:
            self.history_box.see(tk.END)

    @staticmethod
    def _sq_name(sq: tuple[int, int]) -> str:
        r, c = sq
        return f"{chr(ord('a') + c)}{8 - r}"

    # ---------------------------------------------------------------
    # Mouse handling
    # ---------------------------------------------------------------
    def _on_click(self, event: tk.Event) -> None:
        if self.game_over or self.ai_thinking:
            return
        if self.game.state.side_to_move is not Color.BLACK:
            return

        disp_col = event.x // SQUARE_SIZE
        disp_row = event.y // SQUARE_SIZE
        if not (0 <= disp_row < 8 and 0 <= disp_col < 8):
            return
        r, c = self._internal_square(disp_row, disp_col)

        piece = self.game.state.board.grid[r][c]

        # If a piece already selected and destination chosen
        if self.selected is not None:
            target_moves = [m for m in self.legal_destinations if m.to_sq == (r, c)]
            if target_moves:
                mv = target_moves[0]
                if mv.promotion is not None:
                    pt = self._ask_promotion()
                    if pt is None:
                        return
                    mv = next(m for m in target_moves if m.promotion is pt)
                self._play_player_move(mv)
                return

            # If clicking another own piece, reselect
            if piece is not None and piece.color is Color.BLACK:
                self._select_piece(r, c)
                return

            # Otherwise deselect
            self.selected = None
            self.legal_destinations = []
            self._render_board()
            return

        # No selection yet: pick own piece
        if piece is not None and piece.color is Color.BLACK:
            self._select_piece(r, c)

    def _select_piece(self, r: int, c: int) -> None:
        self.selected = (r, c)
        self.legal_destinations = self.game.legal_moves_from(r, c)
        self._render_board()

    def _ask_promotion(self) -> Optional[PieceType]:
        dlg = tk.Toplevel(self.root)
        dlg.title("Promotion")
        dlg.configure(bg=BG_SIDEBAR)
        dlg.transient(self.root)
        dlg.grab_set()
        dlg.resizable(False, False)
        tk.Label(
            dlg,
            text="Choose promotion piece:",
            bg=BG_SIDEBAR,
            fg=FG_TEXT,
            font=("Segoe UI", 12, "bold"),
        ).pack(padx=20, pady=12)

        result: dict[str, Optional[PieceType]] = {"v": None}

        row = tk.Frame(dlg, bg=BG_SIDEBAR)
        row.pack(padx=16, pady=(0, 16))
        options = [
            (PieceType.QUEEN, "♛"),
            (PieceType.ROOK, "♜"),
            (PieceType.BISHOP, "♝"),
            (PieceType.KNIGHT, "♞"),
        ]
        for pt, sym in options:
            b = tk.Button(
                row,
                text=sym,
                font=("Segoe UI Symbol", 32),
                bg=COLOR_DARK,
                fg="white",
                relief="flat",
                width=3,
                height=1,
                cursor="hand2",
                command=lambda p=pt: (result.update({"v": p}), dlg.destroy()),
            )
            b.pack(side="left", padx=4)

        self.root.wait_window(dlg)
        return result["v"]

    def _play_player_move(self, mv: Move) -> None:
        if not self.game.make_move(mv):
            return
        self.selected = None
        self.legal_destinations = []
        self.last_move = mv
        self._render_board()
        self._check_game_end()
        if not self.game_over:
            self.root.after(120, self._computer_move)

    # ---------------------------------------------------------------
    # Computer move
    # ---------------------------------------------------------------
    def _computer_move(self) -> None:
        if self.game_over:
            return
        if self.game.state.side_to_move is not Color.WHITE:
            return
        self.ai_thinking = True
        self._update_sidebar()

        def worker() -> None:
            mv = self.ai.choose_move(self.game)
            self.root.after(0, lambda: self._apply_computer_move(mv))

        threading.Thread(target=worker, daemon=True).start()

    def _apply_computer_move(self, mv: Optional[Move]) -> None:
        self.ai_thinking = False
        if mv is None:
            self._check_game_end()
            return
        if not self.game.make_move(mv):
            return
        self.last_move = mv
        self._render_board()
        self._check_game_end()

    # ---------------------------------------------------------------
    # Game end / buttons
    # ---------------------------------------------------------------
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
            self.ai_thinking = False
            self._render_board()
            messagebox.showinfo("Game Over", self.game.result_text())

    def _new_game(self) -> None:
        if not self.game_over and self.game.history:
            if not messagebox.askyesno("New Game", "Start a new game?"):
                return
        self.game.reset()
        self.ai.set_difficulty(self.diff_var.get().lower())
        self.selected = None
        self.legal_destinations = []
        self.last_move = None
        self.ai_thinking = False
        self.game_over = False
        self._render_board()
        self.root.after(500, self._computer_move)

    def _undo(self) -> None:
        if self.ai_thinking:
            return
        if self.game_over and self.game.status is GameStatus.RESIGNED:
            # Can't undo resignation cleanly; still allow new state
            self.game_over = False
        if not self.game.history:
            return
        # Undo player + computer move (or just last if only one exists)
        if len(self.game.history) >= 2:
            self.game.undo()
            self.game.undo()
        else:
            self.game.undo()
        # Update last_move
        self.last_move = self.game.history[-1][1] if self.game.history else None
        self.selected = None
        self.legal_destinations = []
        self.game_over = False
        self._render_board()
        # If it's now White's turn (shouldn't happen if we undo pairs), let AI move
        if self.game.state.side_to_move is Color.WHITE:
            self.root.after(300, self._computer_move)

    def _resign(self) -> None:
        if self.game_over:
            return
        if not messagebox.askyesno("Resign", "Resign the game?"):
            return
        self.game.resign(Color.BLACK)
        self.game_over = True
        self._render_board()
        messagebox.showinfo("Resigned", self.game.result_text())

    def _on_difficulty_change(self, _event=None) -> None:
        self.ai.set_difficulty(self.diff_var.get().lower())


def run() -> None:
    root = tk.Tk()
    try:
        # Use higher DPI scaling on Windows if available
        root.tk.call("tk", "scaling", 1.2)
    except tk.TclError:
        pass
    ChessGUI(root)
    root.mainloop()


if __name__ == "__main__":
    run()

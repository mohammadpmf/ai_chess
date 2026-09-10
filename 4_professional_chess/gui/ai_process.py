"""Out-of-process AI computation with cancellation and request tracking.

Uses multiprocessing (spawn) so heavy CPU-bound pure-Python search does not
hold the GIL and freeze the Qt event loop.
"""

from __future__ import annotations

import multiprocessing as mp
from dataclasses import dataclass
from typing import Optional

from chess_engine import Move


@dataclass(frozen=True)
class AIResult:
    """Result coming back from the child process."""

    request_id: int
    move: Optional[Move]
    elapsed_seconds: float
    depth: int


def _worker_main(
    state_snapshot,
    difficulty: str,
    result_queue: "mp.Queue",
    request_id: int,
) -> None:
    """Child process entry point. Runs in an isolated interpreter."""
    import time

    from chess_engine import ChessGame
    from chess_ai import ChessAI

    game = ChessGame()
    game.state = state_snapshot

    ai = ChessAI(difficulty)
    t0 = time.perf_counter()
    move = ai.choose_move(game)
    elapsed = time.perf_counter() - t0

    try:
        result_queue.put(
            AIResult(
                request_id=request_id,
                move=move,
                elapsed_seconds=elapsed,
                depth=ai.depth,
            )
        )
    except Exception:
        # Queue may be closed on shutdown; swallow.
        pass


class AIProcessController:
    """Owns the lifecycle of AI child processes.

    Guarantees:
    - Only one AI process runs at a time.
    - Stale results are filtered via request_id.
    - Cancellation is prompt (terminate).
    - Clean shutdown on app exit.
    """

    def __init__(self) -> None:
        # spawn is safest on Windows and works on macOS/Linux.
        self._ctx = mp.get_context("spawn")
        self._queue: "mp.Queue" = self._ctx.Queue()
        self._process: Optional[mp.Process] = None
        self._next_id: int = 1
        self._active_id: Optional[int] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    @property
    def active_request_id(self) -> Optional[int]:
        return self._active_id

    def is_busy(self) -> bool:
        return self._process is not None and self._process.is_alive()

    def start(self, game, difficulty: str) -> int:
        """Spawn a new AI process. Returns the request_id."""
        # Never let two AI processes run concurrently.
        self.cancel()

        request_id = self._next_id
        self._next_id += 1
        self._active_id = request_id

        # Deep snapshot — child gets its own state, no sharing.
        state_snapshot = game.state.copy()

        self._process = self._ctx.Process(
            target=_worker_main,
            args=(state_snapshot, difficulty, self._queue, request_id),
            daemon=True,
        )
        self._process.start()
        return request_id

    def try_fetch(self) -> Optional[AIResult]:
        """Non-blocking poll. Returns a *valid* result or None.

        A result is valid only if it belongs to the currently active
        request. Stale results (from cancelled/older requests) are dropped.
        """
        collected: list[AIResult] = []
        while True:
            try:
                item: AIResult = self._queue.get_nowait()
            except Exception:
                break
            collected.append(item)

        # Join child if it finished.
        if self._process is not None and not self._process.is_alive():
            try:
                self._process.join(timeout=0.05)
            except Exception:
                pass
            self._process = None

        if self._active_id is None:
            return None

        for res in collected:
            if res.request_id == self._active_id:
                self._active_id = None
                return res
        return None

    def cancel(self) -> None:
        """Terminate any running process and invalidate its result."""
        self._active_id = None
        if self._process is not None and self._process.is_alive():
            try:
                self._process.terminate()
                self._process.join(timeout=1.0)
            except Exception:
                pass
        self._process = None

    def shutdown(self) -> None:
        """Called on application close."""
        self.cancel()
        try:
            self._queue.close()
            self._queue.join_thread()
        except Exception:
            pass

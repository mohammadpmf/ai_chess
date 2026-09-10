<div align="center">

# ♟️ Chess — Python Chess Game

**A complete chess game with a modern PySide6 GUI and a Minimax AI opponent.**

</div>

---

<div dir="ltr">

### 📖 Overview

**Chess — Python Chess Game** is a fully playable chess application written
in Python. It implements the complete rules of standard chess from scratch —
no third-party chess library is used for the game logic or for the AI.

The project offers two game modes:

- **Play vs Computer** — a minimax AI with alpha-beta pruning. You can
  choose to play as White or Black.
- **Two Players** — Human vs Human on the same computer.

The graphical interface is built with **PySide6**, styled with a custom
dark QSS theme, and renders chess pieces as scalable vector graphics.
AI search runs in a **separate process** so the interface never freezes,
even on the Hard difficulty.

---

### ✨ Features

#### Game Modes
- **Play vs Computer** — Human vs AI, with a choice of side (White or Black).
- **Two Players** — Human vs Human on the same machine.
- **Automatic board orientation** — the human player's side is always shown
  at the bottom of the screen.

#### AI
- **Minimax search with alpha-beta pruning**
- **Quiescence search** on captures and promotions to reduce the horizon effect
- **Move ordering** — captures and promotions are searched first
- **Static evaluation** with material values, piece-square tables for every
  piece, bishop-pair bonus, doubled-pawn penalty, and mobility
- **Three difficulty presets** — Easy, Medium, Hard

#### Chess Rules
- All standard piece movement (pawn, knight, bishop, rook, queen, king)
- **Castling** (kingside and queenside) with full legality checks
- **En passant**
- **Pawn promotion** to queen, rook, bishop, or knight
- **Check**, **Checkmate**, **Stalemate**
- **Fifty-move rule**, **Threefold repetition**, **Insufficient material**
- **Resignation**

#### User Interface
- Modern dark theme, styled entirely with **QSS**
- Vector chess pieces rendered at runtime (anti-aliased at any size)
- Piece animations using `QPropertyAnimation`
- Highlighting for selection, legal destinations, last move, and check
- Promotion dialog and game-over dialog, styled to match the theme
- Scrollable move history in SAN notation
- Live status bar showing turn, thinking state, and game result

#### User Experience
- **Non-blocking AI** — the AI runs out-of-process, so the GUI stays
  responsive even during long Hard searches
- **Safe cancellation** — pressing Undo, New Game, or Resign while the AI
  is thinking immediately discards the pending result
- **Undo** — takes back a single move or a full pair depending on the mode
- **New Game** — restart at any time with a fresh mode selection

---

### 🛠️ Technologies

| Technology | Role |
|---|---|
| **Python 3.10+** | Core language |
| **PySide6** | Qt 6 bindings used for the entire GUI |
| **QtSvg** | Renders SVG chess pieces into cached pixmaps |
| **multiprocessing** | Runs AI search in a separate process |

The chess engine (`chess_engine.py`) and the AI (`chess_ai.py`) have
**no external dependencies**. Only the GUI layer requires PySide6.

---

### 📋 Prerequisites

- **Python 3.10 or newer**
- **pip**
- A desktop environment capable of running Qt 6 applications
  (Windows, macOS, or Linux with X11/Wayland)

---

### 🚀 Installation & Running ▶️

```bash
git clone https://github.com/mohammadpmf/ai_chess.git
cd ai_chess/4_professional_chess
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux / macOS:
source venv/bin/activate
pip install -r requirements.txt
python main.py
```
### 🎮 How to Play
1. Launch the application. A Select Game Mode dialog appears:

    - Play as White — you play White, computer plays Black.

    - Play as Black — you play Black, computer plays White.

    - Two Players — Human vs Human.

2. Click a piece to select it. Legal destinations appear as green
dots (empty squares) or red rings (captures).

3. Click a destination to make the move.

4. When a pawn reaches the last rank, a promotion dialog appears.

5. Use the sidebar buttons:

    - New Game — pick a new mode and start fresh.

    - Undo — take back the last move.

    - Resign — resign the game.

    - Exit — close the application.

6. The Move History panel shows every move in SAN notation.
The status bar shows whose turn it is and the game result.

Difficulty (Easy / Medium / Hard) is selected from the sidebar and only applies to *Play vs Computer* games.

---

### 🤖 AI Difficulty

The AI is a **negamax search with alpha-beta pruning**, augmented with a quiescence search and a static evaluation function.

| Difficulty | Search depth | Randomization |
| :--- | :--- | :--- |
| **Easy** | 2 plies | ±60 centipawns |
| **Medium** | 3 plies | ±15 centipawns |
| **Hard** | 4 plies | 0 (deterministic) |

Evaluation uses:

* Material values: pawn = 100, knight = 320, bishop = 330, rook = 500, queen = 900
* Piece-square tables for every piece type
* Bishop-pair bonus (+30)
* Doubled-pawn penalty (–15 per extra pawn on a file)
* Mobility (+2 per legal pseudo-move difference)

> The AI is a hobbyist engine — solid but not tournament-strength. It does not use a transposition table, opening book, or endgame tablebase.
### ⚡ Responsive User Interface

The AI search is **CPU-bound pure Python** — it does not release the GIL during minimax traversal. Running it in a thread would still block the Qt event loop and freeze the window. To avoid this, the AI runs in a **separate process** via `multiprocessing` (using the `spawn` method, which is required on Windows).

```text
+-----------------------------+          +-----------------------------+
|         GUI Process         |          |       AI Child Process      |
|-----------------------------|          |-----------------------------|
| MainWindow                  |          | ChessGame (snapshot)        |
| ChessBoardWidget            |  start   | ChessAI                     |
| QTimer (50 ms poll)         | -------> | negamax + alpha-beta        |
|                             |          |                             |
|                             |  Queue   |                             |
| apply if request id         | <------- | AIResult(move, time)        |
| is still active             |          |                             |
+-----------------------------+          +-----------------------------+
```
* **Snapshot isolation** — the child receives a deep copy of the game state, so it never shares mutable state with the GUI.
* **Non-blocking polling** — the GUI polls a queue every 50 ms with a `QTimer`. The event loop stays free during the search.
* **Stale-result protection** — every request has a monotonic `request_id`; only the result matching the active id is applied.
* **Prompt cancellation** — Undo / New Game / Resign terminate the child and invalidate the active id.
* **Clean shutdown** — `closeEvent` stops the timer and shuts down the AI process controller.
---
📁 **Project Structure**

```text
chess/
│
├── main.py                 # Entry point
├── requirements.txt        # Python dependencies
├── README.md               # Documentation
│
├── chess_engine.py         # Full chess rules engine
├── chess_ai.py             # Minimax + alpha-beta AI
│
├── styles/
│   └── dark_theme.qss      # QSS stylesheet
│
└── gui/
    ├── __init__.py
    ├── main_window.py      # Dashboard and wiring
    ├── chess_board.py      # Custom board widget
    ├── player_panel.py     # Player info card
    ├── move_history.py     # SAN move list
    ├── dialogs.py          # Mode, promotion, game-over dialogs
    ├── game_mode.py        # GameMode enum
    ├── ai_process.py       # Out-of-process AI controller
    └── resources.py        # SVG piece renderer
```

**File roles:**

* `chess_engine.py` — the complete chess rules. Defines `Color`, `PieceType`, `Piece`, `Move`, `Board`, `GameState`, `GameStatus`, and `ChessGame`. Handles move generation, legality, castling, en passant, promotion, check detection, SAN, and undo.
* `chess_ai.py` — the AI. `ChessAI.choose_move()` runs a negamax search with alpha-beta pruning, a quiescence search, move ordering, and static evaluation.
* `gui/main_window.py` — the dashboard. Owns the `ChessGame`, the `AIProcessController`, the polling `QTimer`, and every user action.
* `gui/chess_board.py` — a `QWidget` that paints the board, pieces, highlights, and markers; handles mouse input and animations; can be flipped to put either side at the bottom.
* `gui/ai_process.py` — `AIProcessController`: spawns the AI child process, polls for results, filters stale ones by `request_id`, and cancels via `terminate()`.
* `gui/resources.py` — renders each chess piece from an inline SVG template into a cached `QPixmap`.
* `gui/dialogs.py` — `GameModeDialog`, `PromotionDialog`, and `GameOverDialog`, all styled to match the dark theme.
* `styles/dark_theme.qss` — all Qt styling in one place.

---
🏛️ **Architecture**

The project is split into three layers:

* **Rules** — `chess_engine.py`. Pure Python, no Qt, no AI.
* **AI** — `chess_ai.py`. Depends only on the rules layer.
* **Presentation** — `gui/` and `main.py`. Owns all Qt code.

The GUI talks to the engine through direct method calls. The AI is invoked **out of process**: the GUI snapshots the state, sends it to a child process with a `request_id`, and polls for the result. This means the GUI is never blocked, the engine is never mutated from another thread, and a stale result can never corrupt a new game.

---

♟️ **Chess Rules Implemented**

* Pawn single/double push, captures, en passant, promotion
* Knight, bishop, rook, queen, and king movement
* Castling (kingside / queenside) with full legality checks
* Pinned piece detection via post-move legality verification
* Check, checkmate, and stalemate
* Fifty-move rule, threefold repetition, insufficient material
* Resignation

Every pseudo-legal move is applied to a copy of the state and the mover's king is checked for attacks. If the king is (or remains) in check, the move is rejected. This automatically handles pins, moving into check, and castling through attacked squares.

---

🧩 **Development Process**

The project was built incrementally:

1. **Rules engine** — `chess_engine.py` first, validated in isolation.
2. **AI** — `chess_ai.py` next, testable on its own.
3. **GUI** — board, pieces, highlights, dialogs, and dark theme.
4. **Out-of-process AI** — the search was moved to a `multiprocessing` worker to keep the GUI responsive.
5. **Modes and orientation** — *Play vs Computer* (with side choice) and *Two Players*; board orientation made mode-aware.
6. **Polish** — refined undo semantics, mode-aware resignation, and win/loss/draw styling in the game-over dialog.
7. **Documentation** — this README and inline comments.

---

🤖 **Role of Artificial Intelligence**

AI tools — primarily **ChatGPT** and **DeepSeek** — were used throughout this project as a **coding assistant and learning aid**. They were not the authors of the project. Every design decision, every test, every debugging session, and every final commit was made by the developer.

AI assisted with planning, architecture discussions, Python and Qt concept explanations, algorithm suggestions (negamax, alpha-beta, quiescence), first-draft code, refactoring, debugging, edge-case reviews, UI improvements, feature additions, and documentation.

> AI was used as a supporting tool. All decisions, verification, testing, and finalization were performed by the developer.

---

💡 **AI-Assisted Development**

This project was developed with the help of **free AI-assisted tools**. No paid API, paid plan, or commercial chess library was used. The engine, the AI, and the GUI are all hand-written Python using only the standard library plus PySide6.

> The project was developed using free AI-assisted tools and resources.

---

🎓 **Educational Purpose**

This project was developed as a practical exercise for the **Artificial Intelligence course** taught by **Mr. Mohammad Hadi Haji Hosseini** on the [**CodingYar**](https://codingyar.com) platform.

---
🧠 **Learning Through AI**

Using AI here was not about getting ready-made code. The actual workflow was iterative:

* Ask a specific question.
* Read the suggestion.
* Run the code.
* Observe errors.
* Refine the prompt.
* Fix the code.
* Retest.
* Repeat.

The final codebase reflects the developer's understanding, not a copy-paste of generated output.

---

### 📸 Screenshots
<img width="1180" height="829" alt="pyside" src="https://github.com/user-attachments/assets/e56a23d5-e137-4d11-b2f0-080bbe614b72" />
<img width="1179" height="827" alt="pyside2" src="https://github.com/user-attachments/assets/7a32a05e-2aeb-45a6-9b38-39666eb8e58b" />
<img width="922" height="688" alt="deepseek_tkinter" src="https://github.com/user-attachments/assets/731347a5-a9de-4a5c-98ec-365f89e355e4" />
<img width="1047" height="801" alt="chatgpt_custom_tkinter" src="https://github.com/user-attachments/assets/37c9f6a7-a731-4164-a5ba-ce64998bd0fc" />
<img width="1085" height="819" alt="deepseek_pygame" src="https://github.com/user-attachments/assets/4f4854ad-f90e-4c82-ab05-a0af7a46d0d8" />


---
### 👨‍💻 Credits

* **Developer** — designed, implemented, tested, and documented by Mohammad Pourmohammadi Fallah.
* **AI assistance** — ChatGPT and DeepSeek as coding assistants.
* This project was developed as a practical exercise for the **Artificial Intelligence course** taught by **Mr. Mohammad Hadi Haji Hosseini** on the [**CodingYar**](https://codingyar.com) platform.
* **PySide6 / Qt** — the GUI framework used for the presentation layer.

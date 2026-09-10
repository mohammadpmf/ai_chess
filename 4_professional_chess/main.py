"""Entry point. Run: python main.py"""

from __future__ import annotations

import multiprocessing as mp
import sys

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from gui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Chess")
    app.setOrganizationName("ChessApp")
    app.setFont(QFont("Segoe UI", 10))

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    # Required on Windows for multiprocessing 'spawn'.
    mp.freeze_support()
    sys.exit(main())

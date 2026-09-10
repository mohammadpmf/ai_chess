"""Game mode enumeration shared across the GUI layer."""

from __future__ import annotations

from enum import Enum


class GameMode(Enum):
    COMPUTER = "computer"
    TWO_PLAYERS = "two_players"

    @property
    def is_computer(self) -> bool:
        return self is GameMode.COMPUTER

    @property
    def is_two_players(self) -> bool:
        return self is GameMode.TWO_PLAYERS

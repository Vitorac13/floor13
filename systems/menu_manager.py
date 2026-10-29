"""Navegacao entre menu, selecao, jogo e resultado."""

from __future__ import annotations

from enum import Enum

from systems.progress_manager import ProgressManager


class Screen(Enum):
    MAIN_MENU = "main_menu"
    LEVEL_SELECT = "level_select"
    GAME = "game"
    RESULT = "result"


class MenuManager:
    def __init__(self) -> None:
        self.screen = Screen.MAIN_MENU
        self.active_level: int | None = None
        self.result_level: int | None = None

    def show_main_menu(self) -> None:
        self.screen = Screen.MAIN_MENU

    def show_level_select(self) -> None:
        self.screen = Screen.LEVEL_SELECT

    def continue_game(self, progress: ProgressManager) -> int | None:
        next_level = progress.recommended_level
        if next_level is None:
            self.show_level_select()
            return None
        self.start_level(next_level, progress)
        return next_level

    def start_level(self, level: int, progress: ProgressManager) -> bool:
        if not progress.can_start(level):
            return False
        self.active_level = level
        self.result_level = None
        self.screen = Screen.GAME
        return True

    def show_result(self, level: int) -> None:
        self.result_level = level
        self.screen = Screen.RESULT

    def replay(self, progress: ProgressManager) -> int | None:
        level = self.result_level
        if level is None or not self.start_level(level, progress):
            return None
        return level

    def continue_after_result(self, progress: ProgressManager) -> int | None:
        self.result_level = None
        return self.continue_game(progress)

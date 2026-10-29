"""Regras de desbloqueio e conclusao das fases."""

from __future__ import annotations

from collections.abc import Iterable


class ProgressManager:
    def __init__(
        self,
        phase_count: int = 5,
        unlocked_levels: Iterable[int] | None = None,
        completed_levels: Iterable[int] | None = None,
    ) -> None:
        if type(phase_count) is not int or phase_count < 1:
            raise ValueError("O jogo deve possuir ao menos uma fase.")
        self.phase_count = phase_count
        unlocked_values = tuple(unlocked_levels) if unlocked_levels is not None else (1,)
        completed_values = tuple(completed_levels) if completed_levels is not None else ()
        self.unlocked_levels = set(unlocked_values)
        self.completed_levels = set(completed_values)
        if any(not self._valid_level(level) for level in unlocked_values):
            raise ValueError("A lista de fases desbloqueadas contem fase invalida.")
        if any(not self._valid_level(level) for level in self.completed_levels):
            raise ValueError("A lista de fases concluidas contem fase invalida.")
        contiguous_completed = 0
        while contiguous_completed + 1 in self.completed_levels:
            contiguous_completed += 1
        self.completed_levels = set(range(1, contiguous_completed + 1))
        highest_unlocked = min(self.phase_count, contiguous_completed + 1)
        self.unlocked_levels = set(range(1, highest_unlocked + 1))

    def _valid_level(self, level: int) -> bool:
        return type(level) is int and 1 <= level <= self.phase_count

    def can_start(self, level: int) -> bool:
        return self._valid_level(level) and level in self.unlocked_levels

    def complete_level(self, level: int) -> bool:
        if not self.can_start(level):
            raise ValueError(f"A fase {level} esta bloqueada ou nao existe.")
        first_completion = level not in self.completed_levels
        self.completed_levels.add(level)
        if level < self.phase_count:
            self.unlocked_levels.add(level + 1)
        return first_completion

    @property
    def recommended_level(self) -> int | None:
        return next(
            (
                level
                for level in range(1, self.phase_count + 1)
                if level not in self.completed_levels
                and level in self.unlocked_levels
            ),
            None,
        )

    @property
    def all_levels_complete(self) -> bool:
        return len(self.completed_levels) == self.phase_count

    def restore(self, progress: dict[str, object]) -> None:
        unlocked = progress.get("unlocked_levels", [1])
        completed = progress.get("completed_levels", [])
        if not isinstance(unlocked, list) or not isinstance(completed, list):
            raise ValueError("Dados de progressao invalidos.")
        self.__init__(self.phase_count, unlocked, completed)

    def to_dict(self) -> dict[str, list[int]]:
        return {
            "unlocked_levels": sorted(self.unlocked_levels),
            "completed_levels": sorted(self.completed_levels),
        }

"""Regras de desbloqueio e conclusao das fases ordenadas."""

from __future__ import annotations

from collections.abc import Iterable


LevelKey = int | str


class ProgressManager:
    def __init__(
        self,
        phase_count: int | Iterable[str] = 5,
        unlocked_levels: Iterable[LevelKey] | None = None,
        completed_levels: Iterable[LevelKey] | None = None,
    ) -> None:
        if type(phase_count) is int:
            if phase_count < 1:
                raise ValueError("O jogo deve possuir ao menos uma fase.")
            self.level_ids = tuple(str(number) for number in range(1, phase_count + 1))
            self._legacy_numbers = True
        else:
            self.level_ids = tuple(phase_count)
            if any(not isinstance(level_id, str) or not level_id for level_id in self.level_ids):
                raise ValueError("A lista de identificadores de fase e invalida.")
            if len(self.level_ids) != len(set(self.level_ids)):
                raise ValueError("Os identificadores das fases devem ser unicos.")
            self._legacy_numbers = False

        self.phase_count = len(self.level_ids)
        default_unlocked: tuple[LevelKey, ...] = (
            (1,) if self._legacy_numbers else self.level_ids[:1]
        )
        unlocked_values = (
            tuple(unlocked_levels) if unlocked_levels is not None else default_unlocked
        )
        completed_values = tuple(completed_levels or ())
        if any(not self._valid_level(level) for level in unlocked_values):
            raise ValueError("A lista de fases desbloqueadas contem fase invalida.")
        if any(not self._valid_level(level) for level in completed_values):
            raise ValueError("A lista de fases concluidas contem fase invalida.")

        self.completed_levels = set(completed_values)
        self.unlocked_levels: set[LevelKey] = set()
        self._refresh_unlocked()

    def _valid_level(self, level: LevelKey) -> bool:
        if self._legacy_numbers:
            return type(level) is int and 1 <= level <= self.phase_count
        return isinstance(level, str) and level in self.level_ids

    def _ordered_ids(self) -> tuple[LevelKey, ...]:
        if self._legacy_numbers:
            return tuple(range(1, self.phase_count + 1))
        return self.level_ids

    def _refresh_unlocked(self) -> None:
        ordered = self._ordered_ids()
        self.unlocked_levels = set(
            level for level in ordered if level in self.completed_levels
        )
        next_level = next(
            (level for level in ordered if level not in self.completed_levels), None
        )
        if next_level is not None:
            self.unlocked_levels.add(next_level)

    def update_levels(self, level_ids: Iterable[str]) -> None:
        updated_ids = tuple(level_ids)
        if (
            any(not isinstance(level_id, str) or not level_id for level_id in updated_ids)
            or len(updated_ids) != len(set(updated_ids))
        ):
            raise ValueError("A lista de identificadores de fase e invalida.")
        self._legacy_numbers = False
        self.level_ids = updated_ids
        self.phase_count = len(updated_ids)
        self.completed_levels.intersection_update(updated_ids)
        self._refresh_unlocked()

    def can_start(self, level: LevelKey) -> bool:
        return self._valid_level(level) and (
            level in self.completed_levels or level in self.unlocked_levels
        )

    def complete_level(self, level: LevelKey) -> bool:
        if not self.can_start(level):
            raise ValueError(f"A fase {level} esta bloqueada ou nao existe.")
        first_completion = level not in self.completed_levels
        self.completed_levels.add(level)
        self._refresh_unlocked()
        return first_completion

    @property
    def recommended_level(self) -> LevelKey | None:
        return next(
            (
                level
                for level in self._ordered_ids()
                if level not in self.completed_levels
            ),
            None,
        )

    @property
    def all_levels_complete(self) -> bool:
        return bool(self.level_ids) and all(
            level in self.completed_levels for level in self._ordered_ids()
        )

    def restore(self, progress: dict[str, object]) -> None:
        if self._legacy_numbers:
            completed = progress.get("completed_levels", [])
        else:
            completed = progress.get(
                "completed_level_ids", progress.get("completed_levels", [])
            )
        if not isinstance(completed, list):
            raise ValueError("Dados de progressao invalidos.")
        current_completed = [
            level for level in completed if self._valid_level(level)
        ]
        self.__init__(self.level_ids if not self._legacy_numbers else self.phase_count,
                      completed_levels=current_completed)

    def to_dict(self) -> dict[str, list[LevelKey]]:
        if self._legacy_numbers:
            return {
                "unlocked_levels": sorted(self.unlocked_levels),
                "completed_levels": sorted(self.completed_levels),
            }
        return {
            "unlocked_level_ids": [
                level for level in self.level_ids if level in self.unlocked_levels
            ],
            "completed_level_ids": [
                level for level in self.level_ids if level in self.completed_levels
            ],
        }

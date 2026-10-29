"""Calculo de pontuacao deterministico e sem recompensas duplicadas."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Iterable

from level import Collectible, ItemKind, OptionalObjective


@dataclass(frozen=True)
class AttemptResult:
    level_number: int
    score: int
    essential_items: tuple[str, ...]
    bonus_items: tuple[str, ...]
    completed_challenges: tuple[str, ...]
    completed_objectives: tuple[str, ...]
    movements: int
    elapsed_seconds: float | None

    def to_dict(self) -> dict[str, object]:
        return {
            "score": self.score,
            "essential_items": list(self.essential_items),
            "bonus_items": list(self.bonus_items),
            "completed_challenges": list(self.completed_challenges),
            "completed_objectives": list(self.completed_objectives),
            "movements": self.movements,
            "elapsed_seconds": self.elapsed_seconds,
        }


class ScoreManager:
    def __init__(self, challenge_completion_score: int = 300) -> None:
        if type(challenge_completion_score) is not int or challenge_completion_score < 0:
            raise ValueError("A pontuacao de conclusao deve ser nao negativa.")
        self.challenge_completion_score = challenge_completion_score
        self._finalized_attempts: dict[str, AttemptResult] = {}
        self._active_attempt_id: str | None = None
        self._current_items: dict[str, Collectible] = {}
        self._current_objectives: dict[str, OptionalObjective] = {}
        self.current_attempt_score = 0

    def begin_attempt(self, attempt_id: str) -> None:
        if not attempt_id or attempt_id in self._finalized_attempts:
            raise ValueError("Identificador de tentativa ausente ou ja finalizado.")
        self._active_attempt_id = attempt_id
        self._current_items.clear()
        self._current_objectives.clear()
        self.current_attempt_score = 0

    def cancel_attempt(self, attempt_id: str) -> bool:
        """Descarta uma tentativa ativa sem registrar recompensas ou conclusao."""
        if attempt_id != self._active_attempt_id:
            return False
        self._active_attempt_id = None
        self._current_items.clear()
        self._current_objectives.clear()
        self.current_attempt_score = 0
        return True

    def record_items(self, attempt_id: str, items: Iterable[Collectible]) -> None:
        self._ensure_active_attempt(attempt_id)
        for item in items:
            self._current_items.setdefault(item.identifier, item)
        self._refresh_current_score()

    def record_objectives(
        self, attempt_id: str, objectives: Iterable[OptionalObjective]
    ) -> None:
        self._ensure_active_attempt(attempt_id)
        for objective in objectives:
            self._current_objectives.setdefault(objective.identifier, objective)
        self._refresh_current_score()

    def _ensure_active_attempt(self, attempt_id: str) -> None:
        if attempt_id != self._active_attempt_id:
            raise ValueError("A tentativa informada nao esta ativa.")

    def _refresh_current_score(self) -> None:
        self.current_attempt_score = sum(
            item.score for item in self._current_items.values()
        ) + sum(
            objective.reward for objective in self._current_objectives.values()
        )

    @staticmethod
    def calculate_score(
        items: Iterable[Collectible],
        objectives: Iterable[OptionalObjective] = (),
        challenge_completed: bool = False,
        completion_score: int | None = None,
        challenge_completion_score: int = 300,
    ) -> int:
        """Calcula a pontuacao de uma tentativa sem contar IDs repetidos."""
        reward = (
            challenge_completion_score
            if completion_score is None
            else completion_score
        )
        if type(reward) is not int or reward < 0:
            raise ValueError("A recompensa de conclusao deve ser nao negativa.")
        unique_items = {item.identifier: item for item in items}
        unique_objectives = {
            objective.identifier: objective for objective in objectives
        }
        return (
            sum(item.score for item in unique_items.values())
            + sum(objective.reward for objective in unique_objectives.values())
            + (reward if challenge_completed else 0)
        )

    def finalize_attempt(
        self,
        attempt_id: str,
        level_number: int,
        *,
        items: Iterable[Collectible],
        objectives: Iterable[OptionalObjective],
        completed_challenges: Iterable[str],
        movements: int,
        elapsed_seconds: float | None,
        completion_score: int | None = None,
    ) -> AttemptResult:
        if not attempt_id:
            raise ValueError("A tentativa precisa de um identificador.")
        if type(level_number) is not int or level_number < 1:
            raise ValueError("O numero da fase deve ser positivo.")
        if type(movements) is not int or movements < 0:
            raise ValueError("O numero de deslocamentos deve ser nao negativo.")
        if elapsed_seconds is not None and (
            type(elapsed_seconds) not in (int, float)
            or not isfinite(elapsed_seconds)
            or elapsed_seconds < 0
        ):
            raise ValueError("O tempo da tentativa deve ser finito e nao negativo.")
        if attempt_id in self._finalized_attempts:
            return self._finalized_attempts[attempt_id]

        unique_items = {item.identifier: item for item in items}
        unique_objectives = {
            objective.identifier: objective for objective in objectives
        }
        challenge_ids = tuple(dict.fromkeys(completed_challenges))
        score = self.calculate_score(
            unique_items.values(),
            unique_objectives.values(),
            challenge_completed=bool(challenge_ids),
            completion_score=completion_score,
            challenge_completion_score=self.challenge_completion_score,
        )
        result = AttemptResult(
            level_number=level_number,
            score=score,
            essential_items=tuple(
                item_id
                for item_id, item in unique_items.items()
                if item.kind is ItemKind.REQUIRED
            ),
            bonus_items=tuple(
                item_id
                for item_id, item in unique_items.items()
                if item.kind is ItemKind.BONUS
            ),
            completed_challenges=challenge_ids,
            completed_objectives=tuple(unique_objectives),
            movements=movements,
            elapsed_seconds=elapsed_seconds,
        )
        self._finalized_attempts[attempt_id] = result
        if attempt_id == self._active_attempt_id:
            self.current_attempt_score = result.score
            self._active_attempt_id = None
        return result

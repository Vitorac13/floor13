"""Registro de desafios e criacao de estados a partir de uma fase."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from level import Level


class ChallengeState(Protocol):
    current_floor: int
    is_complete: bool
    visited_sequence: list[int]

    def move_to(self, destination: int) -> str: ...

    def reset(self) -> None: ...


ChallengeFactory = Callable[["Level"], ChallengeState]


@dataclass(frozen=True)
class ChallengeRegistration:
    completion_id: str
    factory: ChallengeFactory
    parameter_fields: frozenset[str]


class ChallengeRegistry:
    _factories: dict[str, ChallengeRegistration] = {}

    @classmethod
    def register(
        cls,
        challenge_type: str,
        completion_id: str,
        factory: ChallengeFactory,
        parameter_fields: tuple[str, ...] = (),
    ) -> None:
        if (
            not challenge_type
            or not completion_id
            or challenge_type in cls._factories
            or any(not field for field in parameter_fields)
            or len(parameter_fields) != len(set(parameter_fields))
        ):
            raise ValueError(f"Tipo de desafio invalido ou ja registrado: {challenge_type!r}.")
        cls._factories[challenge_type] = ChallengeRegistration(
            completion_id,
            factory,
            frozenset(parameter_fields),
        )

    @classmethod
    def types(cls) -> frozenset[str]:
        return frozenset(cls._factories)

    @classmethod
    def completion_id(cls, challenge_type: str) -> str:
        try:
            return cls._factories[challenge_type].completion_id
        except KeyError as error:
            raise ValueError(f"Tipo de desafio desconhecido: {challenge_type!r}.") from error

    @classmethod
    def allowed_fields(cls, challenge_type: str) -> set[str]:
        try:
            return {"type", *cls._factories[challenge_type].parameter_fields}
        except KeyError as error:
            raise ValueError(f"Tipo de desafio desconhecido: {challenge_type!r}.") from error

    @classmethod
    def create_state(cls, level: Level) -> ChallengeState:
        try:
            factory = cls._factories[level.challenge_type].factory
        except KeyError as error:
            raise ValueError(
                f"Fase {level.identifier}: tipo de desafio desconhecido: "
                f"{level.challenge_type!r}."
            ) from error
        return factory(level)


def _generic_state(level: Level) -> ChallengeState:
    from game_state import GameState

    return GameState(level)


def _hamilton_state(level: Level) -> ChallengeState:
    from hamilton_challenge import HamiltonChallengeManager
    from hamilton_game_state import HamiltonGameState

    challenge = HamiltonChallengeManager.create_for_level(level)
    return HamiltonGameState(challenge)


def _economic_state(level: Level) -> ChallengeState:
    from economic_challenge import EconomicChallengeManager
    from economic_game_state import EconomicGameState

    challenge = EconomicChallengeManager.create_for_level(level)
    return EconomicGameState(challenge)


def _euler_state(level: Level) -> ChallengeState:
    from euler_challenge import EulerChallengeManager
    from euler_game_state import EulerGameState

    challenge = EulerChallengeManager.create_for_level(level)
    return EulerGameState(challenge)


def _final_state(level: Level) -> ChallengeState:
    from final_challenge import FinalChallengeManager
    from final_game_state import FinalGameState

    challenge = FinalChallengeManager.create_for_level(level)
    return FinalGameState(challenge)


ChallengeRegistry.register(
    "collect_and_exit",
    "collect_and_exit",
    _generic_state,
)
ChallengeRegistry.register(
    "hamilton", "hamilton", _hamilton_state, ("end_floor",)
)
ChallengeRegistry.register(
    "economic", "economic_optimal_route", _economic_state, ("destination_floor",)
)
ChallengeRegistry.register(
    "euler", "euler_trail", _euler_state, ("reference_trail",)
)
ChallengeRegistry.register(
    "final",
    "minimum_round_trip",
    _final_state,
    ("destination_floor", "return_floor"),
)

"""Tipos de dados para fases e itens colecionaveis."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from graph import Graph


class ItemKind(Enum):
    REQUIRED = "Obrigatório"
    BONUS = "Bônus"


@dataclass(frozen=True)
class Collectible:
    identifier: str
    name: str
    floor: int
    kind: ItemKind
    score: int = 100
    is_key: bool = False


@dataclass(frozen=True)
class OptionalObjective:
    identifier: str
    name: str
    description: str
    reward: int
    kind: str
    floor: int | None = None


@dataclass(frozen=True)
class ConnectionRequirement:
    first_floor: int
    second_floor: int
    key_ids: tuple[str, ...]


@dataclass(frozen=True)
class Level:
    name: str
    graph: Graph[int]
    start_floor: int
    exit_floor: int
    items: tuple[Collectible, ...]
    identifier: str = "phase-01"
    number: int = 1
    exit_requires_keys: tuple[str, ...] = ()
    connection_requirements: tuple[ConnectionRequirement, ...] = ()
    required_challenges: tuple[str, ...] = ()
    optional_objectives: tuple[OptionalObjective, ...] = ()
    completion_score: int = 300
    challenge_type: str = "collect_and_exit"
    challenge_parameters: dict[str, Any] = field(default_factory=dict)

    @property
    def items_by_floor(self) -> dict[int, tuple[Collectible, ...]]:
        """Return every floor's configured items, including empty floors."""
        grouped: dict[int, list[Collectible]] = {
            floor: [] for floor in self.graph.vertices
        }
        for item in self.items:
            grouped[item.floor].append(item)
        return {floor: tuple(items) for floor, items in grouped.items()}

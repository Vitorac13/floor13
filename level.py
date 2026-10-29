"""Tipos de dados para fases e itens colecionaveis."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

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


@dataclass(frozen=True)
class Level:
    name: str
    graph: Graph[int]
    start_floor: int
    exit_floor: int
    items: tuple[Collectible, ...]

    @property
    def items_by_floor(self) -> dict[int, tuple[Collectible, ...]]:
        """Return every floor's configured items, including empty floors."""
        grouped: dict[int, list[Collectible]] = {
            floor: [] for floor in self.graph.vertices
        }
        for item in self.items:
            grouped[item.floor].append(item)
        return {floor: tuple(items) for floor, items in grouped.items()}

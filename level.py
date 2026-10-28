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

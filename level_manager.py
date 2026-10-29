"""Definicao e validacao dos dados de fases."""

from __future__ import annotations

from collections import deque

from algorithms import is_connected
from graph import Graph
from level import Collectible, ItemKind, Level


class LevelManager:
    @staticmethod
    def create_first_contact() -> Level:
        """Constroi a fase de demonstracao Primeiro contato."""
        graph = Graph(range(1, 7))
        for first, second in (
            (1, 2),
            (2, 3),
            (3, 4),
            (4, 6),
            (2, 5),
            (5, 6),
        ):
            graph.add_edge(first, second)

        level = Level(
            name="Primeiro contato",
            graph=graph,
            start_floor=1,
            exit_floor=6,
            items=(
                Collectible("chave", "Chave antiga", 2, ItemKind.REQUIRED),
                Collectible("fusivel", "Fusivel", 3, ItemKind.REQUIRED),
                Collectible("cartao", "Cartao de acesso", 4, ItemKind.REQUIRED),
                Collectible("foto", "Fotografia", 5, ItemKind.BONUS),
            ),
        )
        LevelManager.validate(level)
        return level

    @classmethod
    def validate(cls, level: Level) -> None:
        """Recusa fases mal configuradas ou sem solucao jogavel."""
        if not level.graph.has_vertex(level.start_floor):
            raise ValueError("O andar inicial nao existe no grafo.")
        if not level.graph.has_vertex(level.exit_floor):
            raise ValueError("O andar de saida nao existe no grafo.")
        if not is_connected(level.graph):
            raise ValueError("O grafo da fase deve ser conectado.")

        identifiers = [item.identifier for item in level.items]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("Os identificadores dos itens devem ser unicos.")
        if any(not level.graph.has_vertex(item.floor) for item in level.items):
            raise ValueError("Todos os itens devem estar em andares existentes.")

        if any(not isinstance(item.kind, ItemKind) for item in level.items):
            raise ValueError("Todos os itens devem ter uma categoria valida.")
        required = [
            item for item in level.items if item.kind is ItemKind.REQUIRED
        ]
        bonuses = [item for item in level.items if item.kind is ItemKind.BONUS]

        required_floors = [item.floor for item in required]
        bonus_floors = [item.floor for item in bonuses]
        if set(required_floors) & set(bonus_floors):
            raise ValueError("Itens bonus nao podem compartilhar andar com obrigatorios.")
        if not cls.has_completion_route(level):
            raise ValueError("Nao existe rota viavel para concluir a fase.")

    @staticmethod
    def has_completion_route(level: Level) -> bool:
        """Verifica se ha uma rota que visita os objetivos e termina na saida."""
        required_by_floor: dict[int, frozenset[str]] = {}
        for item in level.items:
            if item.kind is ItemKind.REQUIRED:
                required_by_floor.setdefault(item.floor, frozenset())
                required_by_floor[item.floor] |= frozenset((item.identifier,))

        required_ids = frozenset(
            identifier
            for identifiers in required_by_floor.values()
            for identifier in identifiers
        )
        initial_items = required_by_floor.get(level.start_floor, frozenset())
        initial_state = (level.start_floor, initial_items)
        queue = deque([initial_state])
        visited = {initial_state}

        while queue:
            floor, collected = queue.popleft()
            if floor == level.exit_floor and collected == required_ids:
                return True

            for neighbor, _ in level.graph.neighbors(floor):
                next_collected = collected | required_by_floor.get(
                    neighbor, frozenset()
                )
                state = (neighbor, next_collected)
                if state not in visited:
                    visited.add(state)
                    queue.append(state)
        return False

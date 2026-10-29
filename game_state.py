"""Estado e regras de progressao do jogador durante uma fase."""

from __future__ import annotations

from level import Collectible, ItemKind, Level


class GameState:
    def __init__(self, level: Level) -> None:
        self.level = level
        self.current_floor = level.start_floor
        self.visited_floors = {level.start_floor}
        self.collected_required: set[str] = set()
        self.collected_bonus: set[str] = set()
        self.is_complete = False

    @property
    def missing_required_items(self) -> tuple[Collectible, ...]:
        return tuple(
            item
            for item in self.level.items
            if item.kind is ItemKind.REQUIRED
            and item.identifier not in self.collected_required
        )

    @property
    def items_on_current_floor(self) -> tuple[Collectible, ...]:
        collected = self.collected_required | self.collected_bonus
        return tuple(
            item
            for item in self.all_items_on_current_floor
            if item.identifier not in collected
        )

    @property
    def all_items_on_current_floor(self) -> tuple[Collectible, ...]:
        return self.level.items_by_floor[self.current_floor]

    def move_to(self, destination: int) -> str:
        if self.is_complete:
            return "A fase ja foi concluida."
        if not self.level.graph.has_edge(self.current_floor, destination):
            return f"Nao ha elevador do andar {self.current_floor:02d} para {destination:02d}."

        self.current_floor = destination
        self.visited_floors.add(destination)

        if destination == self.level.exit_floor:
            if self.missing_required_items:
                missing_names = ", ".join(
                    item.name for item in self.missing_required_items
                )
                return f"Saida bloqueada. Faltam: {missing_names}."
            self.is_complete = True
            return f"Fase concluida: {self.level.name}!"

        return f"Voce chegou ao andar {destination:02d}."

    def collect_items_here(self) -> tuple[Collectible, ...]:
        if self.is_complete:
            return ()

        collected = self.items_on_current_floor
        for item in collected:
            if item.kind is ItemKind.REQUIRED:
                self.collected_required.add(item.identifier)
            else:
                self.collected_bonus.add(item.identifier)
        return collected

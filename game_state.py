"""Estado e regras de progressao do jogador durante uma fase."""

from __future__ import annotations

from level import Collectible, ItemKind, Level


class GameState:
    def __init__(self, level: Level) -> None:
        self.level = level
        self.reset()

    def reset(self) -> None:
        self.current_floor = self.level.start_floor
        self.visited_sequence = [self.level.start_floor]
        self.visited_floors = {self.level.start_floor}
        self.collected_required: set[str] = set()
        self.collected_bonus: set[str] = set()
        self.collected_keys: set[str] = set()
        self.movement_count = 0
        self.returned_to_start = False
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
    def missing_keys(self) -> tuple[Collectible, ...]:
        required_ids = set(self.level.exit_requires_keys)
        return tuple(
            item
            for item in self.level.items
            if item.identifier in required_ids
            and item.identifier not in self.collected_keys
        )

    def missing_connection_keys(
        self, first_floor: int, second_floor: int
    ) -> tuple[Collectible, ...]:
        required_ids = {
            key_id
            for requirement in self.level.connection_requirements
            if {requirement.first_floor, requirement.second_floor}
            == {first_floor, second_floor}
            for key_id in requirement.key_ids
        }
        return tuple(
            item
            for item in self.level.items
            if item.identifier in required_ids
            and item.identifier not in self.collected_keys
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
        missing_connection_keys = self.missing_connection_keys(
            self.current_floor, destination
        )
        if missing_connection_keys:
            names = ", ".join(item.name for item in missing_connection_keys)
            return f"Conexao bloqueada. Falta a chave: {names}."

        self.current_floor = destination
        self.visited_sequence.append(destination)
        self.visited_floors.add(destination)
        self.movement_count += 1
        if destination == self.level.start_floor and self.movement_count > 1:
            self.returned_to_start = True

        if destination == self.level.exit_floor:
            if self.missing_required_items or self.missing_keys:
                missing_key_ids = set(self.level.exit_requires_keys)
                missing_names = ", ".join(
                    item.name
                    for item in self.missing_required_items
                    if item.identifier not in missing_key_ids
                )
                missing_key_names = ", ".join(
                    item.name for item in self.missing_keys
                )
                missing_parts = []
                if missing_key_names:
                    missing_parts.append(f"chave necessaria: {missing_key_names}")
                if missing_names:
                    missing_parts.append(missing_names)
                return f"Saida bloqueada. Faltam: {', '.join(missing_parts)}."
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
                if item.is_key:
                    self.collected_keys.add(item.identifier)
            else:
                self.collected_bonus.add(item.identifier)
        return collected

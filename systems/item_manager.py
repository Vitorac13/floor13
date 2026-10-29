"""Coleta unica de itens e registro de exploracao por tentativa."""

from __future__ import annotations

from level import Collectible, ItemKind, Level, OptionalObjective


class ItemProgress:
    def __init__(self, level: Level) -> None:
        self.level = level
        self.collected_required: set[str] = set()
        self.collected_bonus: set[str] = set()
        self.collected_keys: set[str] = set()
        self.visited_floors: set[int] = {level.start_floor}
        self.movement_count = 0
        self.returned_to_start = False

    @property
    def collected_item_ids(self) -> frozenset[str]:
        return frozenset(self.collected_required | self.collected_bonus)

    def items_on_floor(self, floor: int) -> tuple[Collectible, ...]:
        collected = self.collected_item_ids
        return tuple(
            item
            for item in self.level.items_by_floor[floor]
            if item.identifier not in collected
        )

    def record_movement(self, floor: int) -> None:
        self.movement_count += 1
        self.visited_floors.add(floor)
        if floor == self.level.start_floor and self.movement_count > 1:
            self.returned_to_start = True

    def collect(self, floor: int) -> tuple[Collectible, ...]:
        items = self.items_on_floor(floor)
        for item in items:
            if item.kind is ItemKind.REQUIRED:
                self.collected_required.add(item.identifier)
                if item.is_key:
                    self.collected_keys.add(item.identifier)
            else:
                self.collected_bonus.add(item.identifier)
        return items

    @property
    def completed_objectives(self) -> tuple[OptionalObjective, ...]:
        completed: list[OptionalObjective] = []
        for objective in self.level.optional_objectives:
            if objective.kind == "visit_floor" and objective.floor in self.visited_floors:
                completed.append(objective)
            elif objective.kind == "collect_all_bonus":
                bonus_ids = {
                    item.identifier
                    for item in self.level.items
                    if item.kind is ItemKind.BONUS
                }
                if bonus_ids.issubset(self.collected_bonus):
                    completed.append(objective)
            elif objective.kind == "return_to_start" and self.returned_to_start:
                completed.append(objective)
        return tuple(completed)

import unittest
from dataclasses import replace

from algorithms import is_connected
from game_state import GameState
from level import Collectible, ItemKind
from level_manager import LevelManager


class FirstContactTests(unittest.TestCase):
    def setUp(self) -> None:
        self.level = LevelManager.create_first_contact()
        self.game = GameState(self.level)

    def collect_required_on(self, floor: int) -> None:
        self.game.move_to(floor)
        collected = self.game.collect_items_here()
        self.assertTrue(collected)
        self.assertTrue(all(item.kind is ItemKind.REQUIRED for item in collected))

    def test_level_starts_on_first_floor_with_only_it_visited(self) -> None:
        self.assertEqual(self.level.name, "Primeiro contato")
        self.assertEqual(self.level.start_floor, 1)
        self.assertEqual(self.level.exit_floor, 6)
        self.assertEqual(self.game.current_floor, self.level.start_floor)
        self.assertEqual(self.game.visited_floors, {self.level.start_floor})

    def test_movement_requires_an_existing_connection(self) -> None:
        message = self.game.move_to(4)

        self.assertIn("Nao ha elevador", message)
        self.assertEqual(self.game.current_floor, 1)
        self.assertEqual(self.game.visited_floors, {1})

    def test_successful_movement_registers_visited_floors(self) -> None:
        self.game.move_to(2)
        self.game.move_to(3)

        self.assertEqual(self.game.current_floor, 3)
        self.assertEqual(self.game.visited_floors, {1, 2, 3})

    def test_required_items_are_collected_separately_and_only_once(self) -> None:
        self.game.move_to(2)
        collected = self.game.collect_items_here()

        self.assertEqual([item.identifier for item in collected], ["chave"])
        self.assertEqual(self.game.collected_required, {"chave"})
        self.assertEqual(self.game.missing_required_items[0].identifier, "fusivel")
        self.game.move_to(3)
        self.game.move_to(2)
        self.assertEqual(self.game.items_on_current_floor, ())
        self.assertEqual(self.game.collect_items_here(), ())

    def test_bonus_items_can_be_collected_without_becoming_required(self) -> None:
        self.game.move_to(2)
        self.game.move_to(5)
        collected = self.game.collect_items_here()

        self.assertEqual([item.identifier for item in collected], ["foto"])
        self.assertEqual(self.game.collected_bonus, {"foto"})
        self.assertEqual(len(self.game.missing_required_items), 3)
        self.game.move_to(2)
        self.game.move_to(5)
        self.assertEqual(self.game.collect_items_here(), ())

    def test_floor_without_items_is_a_valid_empty_state(self) -> None:
        self.assertEqual(self.level.items_by_floor[1], ())
        self.assertEqual(self.level.items_by_floor[6], ())
        self.assertEqual(self.game.items_on_current_floor, ())
        self.assertEqual(self.game.collect_items_here(), ())
        self.assertEqual(self.game.collected_required, set())
        self.assertEqual(self.game.collected_bonus, set())

    def test_visiting_an_empty_floor_does_not_change_item_progress(self) -> None:
        self.game.move_to(2)
        self.game.move_to(5)
        message = self.game.move_to(6)

        self.assertIn("Saida bloqueada", message)
        self.assertEqual(self.game.visited_floors, {1, 2, 5, 6})
        self.assertEqual(self.game.items_on_current_floor, ())
        self.assertEqual(self.game.collect_items_here(), ())
        self.assertEqual(self.game.collected_required, set())

    def test_exit_does_not_finish_phase_while_required_items_are_missing(self) -> None:
        self.game.move_to(2)
        self.game.move_to(5)
        message = self.game.move_to(6)

        self.assertIn("Saida bloqueada", message)
        self.assertIn("Chave antiga", message)
        self.assertIn("Fusivel", message)
        self.assertIn("Cartao de acesso", message)
        self.assertFalse(self.game.is_complete)
        self.assertEqual(self.game.current_floor, self.level.exit_floor)

    def test_collecting_all_required_items_does_not_finish_before_exit(self) -> None:
        for floor in (2, 3, 4):
            self.collect_required_on(floor)
            self.assertFalse(self.game.is_complete)

        self.assertEqual(self.game.current_floor, 4)
        self.assertEqual(self.game.missing_required_items, ())

    def test_phase_is_won_after_collecting_required_items_and_reaching_exit(self) -> None:
        for floor in (2, 3, 4):
            self.collect_required_on(floor)

        message = self.game.move_to(6)

        self.assertTrue(self.game.is_complete)
        self.assertIn("Fase concluida", message)

    def test_bonus_items_are_optional_for_victory(self) -> None:
        for floor in (2, 3, 4):
            self.collect_required_on(floor)
        self.game.move_to(6)

        self.assertTrue(self.game.is_complete)
        self.assertEqual(self.game.collected_bonus, set())

    def test_completed_phase_cannot_be_changed_by_later_actions(self) -> None:
        for floor in (2, 3, 4):
            self.collect_required_on(floor)
        self.game.move_to(6)

        message = self.game.move_to(5)
        collected = self.game.collect_items_here()

        self.assertTrue(self.game.is_complete)
        self.assertEqual(self.game.current_floor, 6)
        self.assertEqual(message, "A fase ja foi concluida.")
        self.assertEqual(collected, ())

    def test_level_has_connected_graph_and_viable_completion_route(self) -> None:
        self.assertEqual(len(self.level.graph.vertices), 6)
        self.assertTrue(is_connected(self.level.graph))
        self.assertTrue(LevelManager.has_completion_route(self.level))
        required_floors = {
            item.floor for item in self.level.items
            if item.kind is ItemKind.REQUIRED
        }
        bonus_floors = {
            item.floor for item in self.level.items
            if item.kind is ItemKind.BONUS
        }
        self.assertEqual(len(required_floors), 3)
        self.assertEqual(bonus_floors, {5})
        self.assertTrue(required_floors.isdisjoint(bonus_floors))

    def test_level_configuration_allows_variable_item_counts(self) -> None:
        level_without_bonus_items = replace(
            self.level,
            items=tuple(
                item for item in self.level.items
                if item.kind is ItemKind.REQUIRED
            ),
        )

        LevelManager.validate(level_without_bonus_items)

        self.assertTrue(LevelManager.has_completion_route(level_without_bonus_items))
        self.assertEqual(level_without_bonus_items.items_by_floor[5], ())
        self.assertEqual(level_without_bonus_items.items_by_floor[6], ())

    def test_bonus_and_required_items_cannot_share_a_floor(self) -> None:
        conflicting_level = replace(
            self.level,
            items=self.level.items
            + (Collectible("other", "Outro item", 2, ItemKind.BONUS),),
        )

        with self.assertRaisesRegex(ValueError, "nao podem compartilhar andar"):
            LevelManager.validate(conflicting_level)


if __name__ == "__main__":
    unittest.main()

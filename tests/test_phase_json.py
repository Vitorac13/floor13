import copy
import unittest

from game_state import GameState
from level import ItemKind
from level_manager import LevelManager


class PhaseJsonTests(unittest.TestCase):
    def test_all_seven_phase_files_load_and_keep_the_existing_graphs(self) -> None:
        levels = [
            LevelManager.load_level(f"phase-0{number}")
            for number in range(1, 8)
        ]

        self.assertEqual([level.number for level in levels], [1, 2, 3, 4, 5, 6, 7])
        self.assertEqual(
            [len(level.graph.vertices) for level in levels],
            [6, 6, 6, 5, 6, 6, 7],
        )
        self.assertEqual(levels[0].name, "Primeiro contato")
        self.assertEqual(levels[1].name, "Sem voltar atrás")
        self.assertEqual(levels[2].name, "Elevador econômico")
        self.assertEqual(levels[3].name, "Inspeção completa")
        self.assertEqual(levels[4].name, "A saída")
        self.assertEqual(levels[6].exit_floor, 7)
        self.assertEqual(
            levels[6].exit_requires_keys,
            ("chave-prateada", "chave-dourada"),
        )

    def test_loader_rejects_connections_to_unknown_vertices(self) -> None:
        config = LevelManager.load_phase_config("phase-01")
        invalid_config = copy.deepcopy(config)
        invalid_config["graph"]["edges"][0] = [1, 99]

        with self.assertRaisesRegex(ValueError, "vertice inexistente"):
            LevelManager.from_config(invalid_config)

    def test_loader_rejects_missing_required_key_and_duplicate_connection(self) -> None:
        config = LevelManager.load_phase_config("phase-01")
        missing_key = copy.deepcopy(config)
        missing_key["exit_requirements"]["keys"] = ["missing-key"]
        with self.assertRaisesRegex(ValueError, "chave exigida"):
            LevelManager.validate(LevelManager.from_config(missing_key))

        duplicate_edge = copy.deepcopy(config)
        duplicate_edge["graph"]["edges"].append([2, 1])
        with self.assertRaisesRegex(ValueError, "conexao duplicada"):
            LevelManager.from_config(duplicate_edge)

    def test_loader_rejects_invalid_item_floor_and_unknown_item_type(self) -> None:
        config = LevelManager.load_phase_config("phase-01")
        invalid_floor = copy.deepcopy(config)
        invalid_floor["items"][0]["floor"] = 99
        with self.assertRaisesRegex(ValueError, "andares existentes"):
            level = LevelManager.from_config(invalid_floor)
            LevelManager.validate(level)

        invalid_type = copy.deepcopy(config)
        invalid_type["items"][0]["type"] = "treasure"
        with self.assertRaisesRegex(ValueError, "tipo invalido"):
            LevelManager.from_config(invalid_type)

    def test_existing_leaf_floor_can_be_explored_and_returned_from(self) -> None:
        level = LevelManager.load_level("phase-01")
        game = GameState(level)

        self.assertEqual(len(level.graph.neighbors(1)), 1)
        game.move_to(2)
        message = game.move_to(1)
        self.assertIn("Voce chegou", message)
        self.assertEqual(game.current_floor, 1)
        game.move_to(2)
        self.assertEqual(game.movement_count, 3)
        self.assertTrue(game.returned_to_start)
        self.assertEqual(
            [objective.identifier for objective in level.optional_objectives],
            ["return-to-lobby"],
        )

    def test_exit_explicitly_reports_a_missing_key(self) -> None:
        game = GameState(LevelManager.load_level("phase-01"))
        game.move_to(2)
        game.move_to(3)
        game.collect_items_here()
        game.move_to(4)
        game.collect_items_here()

        message = game.move_to(6)

        self.assertIn("Saida bloqueada", message)
        self.assertIn("chave necessaria", message)
        self.assertEqual(game.collected_keys, set())
        self.assertFalse(game.is_complete)

    def test_key_collection_is_registered_as_one_required_reward(self) -> None:
        game = GameState(LevelManager.load_level("phase-01"))
        game.move_to(2)

        collected = game.collect_items_here()

        self.assertEqual(len(collected), 1)
        self.assertIs(collected[0].kind, ItemKind.REQUIRED)
        self.assertTrue(collected[0].is_key)
        self.assertEqual(game.collected_required, {"chave"})
        self.assertEqual(game.collected_keys, {"chave"})
        self.assertEqual(game.collect_items_here(), ())

    def test_key_can_unlock_a_connection_and_loader_rejects_unreachable_key(self) -> None:
        config = LevelManager.load_phase_config("phase-01")
        gated_config = copy.deepcopy(config)
        gated_config["items"][0]["floor"] = 1
        gated_config["connection_requirements"] = [
            {"from": 1, "to": 2, "keys": ["chave"]}
        ]
        level = LevelManager.from_config(gated_config)
        LevelManager.validate(level)
        game = GameState(level)

        message = game.move_to(2)
        self.assertIn("Conexao bloqueada", message)
        self.assertEqual(game.movement_count, 0)
        game.collect_items_here()
        self.assertIn("Voce chegou", game.move_to(2))
        self.assertEqual(game.collected_keys, {"chave"})

        impossible_config = copy.deepcopy(gated_config)
        impossible_config["items"][0]["floor"] = 2
        with self.assertRaisesRegex(ValueError, "rota viavel"):
            impossible_level = LevelManager.from_config(impossible_config)
            LevelManager.validate(impossible_level)


if __name__ == "__main__":
    unittest.main()

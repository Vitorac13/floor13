import json
import os
import shutil
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from game_state import GameState
from level_manager import DEFAULT_LEVELS_DIR, LevelManager
from main import ElevatorPrototype
from systems.progress_manager import ProgressManager
from systems.save_manager import SaveManager


def custom_phase(identifier: str = "phase-06", number: int = 6) -> dict[str, object]:
    return {
        "id": identifier,
        "number": number,
        "name": "A ramificacao",
        "graph": {
            "vertices": [1, 2, 3, 4, 5],
            "edges": [[1, 2], [2, 3], [3, 4], [4, 2], [4, 5]],
        },
        "start_floor": 1,
        "exit_floor": 5,
        "items": [
            {
                "id": "door-key",
                "name": "Chave da saida",
                "floor": 2,
                "type": "key",
                "score": 50,
            },
            {
                "id": "bonus-note",
                "name": "Bilhete bonus",
                "floor": 3,
                "type": "bonus",
                "score": 20,
            },
        ],
        "exit_requirements": {"keys": ["door-key"], "challenges": []},
        "connection_requirements": [
            {"from": 4, "to": 5, "keys": ["door-key"]}
        ],
        "challenge": {"type": "collect_and_exit"},
        "optional_objectives": [],
        "rewards": {"completion": 40},
    }


def write_config(directory: Path, filename: str, config: object) -> Path:
    path = directory / filename
    path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")
    return path


class DynamicLevelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.levels_dir = Path(self.temporary_directory.name)

    def tearDown(self) -> None:
        pygame.quit()
        self.temporary_directory.cleanup()

    def test_default_directory_discovers_all_seven_existing_phases(self) -> None:
        discovery = LevelManager.discover_levels()

        self.assertEqual(len(discovery.levels), 7)
        self.assertEqual(
            [level.identifier for level in discovery.levels],
            [f"phase-0{number}" for number in range(1, 8)],
        )
        self.assertFalse(
            [diagnostic for diagnostic in discovery.diagnostics if diagnostic.severity == "error"]
        )

    def test_custom_json_phase_appears_in_menu_and_progresses_without_python_changes(self) -> None:
        for number in range(1, 6):
            path = DEFAULT_LEVELS_DIR / f"phase-0{number}.json"
            shutil.copy(path, self.levels_dir / path.name)
        write_config(self.levels_dir, "phase-06.json", custom_phase())

        app = ElevatorPrototype(
            str(self.levels_dir / "progress.json"), str(self.levels_dir)
        )
        try:
            self.assertEqual(len(app.phase_levels), 6)
            for identifier in (f"phase-0{number}" for number in range(1, 6)):
                app.progress_manager.complete_level(identifier)
            self.assertTrue(app.progress_manager.can_start("phase-06"))

            app.menu.show_level_select()
            app._draw_level_select()
            self.assertIn("phase-06", app.level_rects)
            app._start_phase("phase-06")
            self.assertIsInstance(app.active_state, GameState)

            for floor, collect in (
                (2, True),
                (3, True),
                (4, False),
                (2, False),
                (4, False),
                (5, False),
            ):
                app.selected_floor = floor
                app._travel()
                if collect:
                    app._collect_items()

            self.assertEqual(app.menu.result_level, "phase-06")
            self.assertEqual(app.saved_progress["level_scores"]["phase-06"], 110)
            self.assertIn("phase-06", app.saved_progress["completed_level_ids"])
            self.assertTrue(app.progress_manager.all_levels_complete)
            self.assertIsNone(app.progress_manager.recommended_level)
        finally:
            pygame.quit()

    def test_invalid_json_is_reported_without_hiding_other_valid_phases(self) -> None:
        write_config(self.levels_dir, "valid.json", custom_phase("valid", 1))
        invalid = self.levels_dir / "broken.json"
        invalid.write_text("{", encoding="utf-8")

        discovery = LevelManager.discover_levels(self.levels_dir)

        self.assertEqual([level.identifier for level in discovery.levels], ["valid"])
        self.assertTrue(
            any(
                item.path == invalid and "JSON invalido" in item.message
                for item in discovery.diagnostics
            )
        )

    def test_duplicate_phase_ids_reject_every_conflicting_file(self) -> None:
        write_config(self.levels_dir, "first.json", custom_phase("duplicada", 1))
        write_config(self.levels_dir, "second.json", custom_phase("duplicada", 2))

        discovery = LevelManager.discover_levels(self.levels_dir)

        self.assertEqual(discovery.levels, ())
        duplicate_errors = [
            item for item in discovery.diagnostics if "Identificador duplicado" in item.message
        ]
        self.assertEqual(len(duplicate_errors), 2)

    def test_duplicate_display_numbers_are_rejected(self) -> None:
        write_config(self.levels_dir, "first.json", custom_phase("first", 2))
        write_config(self.levels_dir, "second.json", custom_phase("second", 2))

        discovery = LevelManager.discover_levels(self.levels_dir)

        self.assertEqual(discovery.levels, ())
        self.assertTrue(
            any("Numero duplicado" in item.message for item in discovery.diagnostics)
        )

    def test_invalid_vertex_references_in_edges_and_items_are_rejected(self) -> None:
        config = custom_phase("invalid-edge", 1)
        config["graph"]["edges"][0] = [1, 99]
        with self.assertRaisesRegex(ValueError, "vertice inexistente"):
            LevelManager.from_config(config)

        config = custom_phase("invalid-item", 1)
        config["items"][0]["floor"] = 99
        with self.assertRaisesRegex(ValueError, "andares existentes"):
            LevelManager.validate(LevelManager.from_config(config))

    def test_unreachable_exit_and_unobtainable_key_are_rejected(self) -> None:
        unreachable = custom_phase("unreachable", 1)
        unreachable["graph"] = {
            "vertices": [1, 2, 3],
            "edges": [[1, 2]],
        }
        unreachable["exit_floor"] = 3
        unreachable["items"] = []
        unreachable["exit_requirements"] = {"keys": [], "challenges": []}
        unreachable["connection_requirements"] = []
        with self.assertRaisesRegex(ValueError, "rota viavel"):
            LevelManager.validate(LevelManager.from_config(unreachable))

        impossible_key = custom_phase("impossible-key", 1)
        impossible_key["items"][0]["floor"] = 5
        with self.assertRaisesRegex(ValueError, "rota viavel"):
            LevelManager.validate(LevelManager.from_config(impossible_key))

    def test_disconnected_but_completable_graph_is_a_design_warning(self) -> None:
        config = custom_phase("intentional-island", 1)
        config["graph"] = {
            "vertices": [1, 2, 3, 4, 5, 6],
            "edges": [[1, 2], [2, 3], [4, 5], [5, 6]],
        }
        config["exit_floor"] = 3
        config["items"] = []
        config["exit_requirements"] = {"keys": [], "challenges": []}
        config["connection_requirements"] = []
        write_config(self.levels_dir, "island.json", config)

        discovery = LevelManager.discover_levels(self.levels_dir)

        self.assertEqual(len(discovery.levels), 1)
        self.assertTrue(
            any(item.severity == "warning" and "desconectado" in item.message
                for item in discovery.diagnostics)
        )

    def test_save_migration_preserves_existing_phase_results_when_adding_a_phase(self) -> None:
        phase_ids = [f"phase-0{number}" for number in range(1, 6)]
        legacy_result = {
            "score": 800,
            "movements": 6,
            "elapsed_seconds": 18.0,
            "essential_items": ["key"],
            "bonus_items": [],
            "completed_challenges": ["collect_and_exit"],
            "completed_objectives": [],
        }
        old_save = {
            "version": 1,
            "unlocked_levels": [1, 2, 3],
            "completed_levels": [1, 2],
            "level_scores": {"1": 800, "2": 700, "3": 0, "4": 0, "5": 0},
            "best_results": {"1": legacy_result},
            "last_results": {"1": legacy_result},
            "total_score": 1500,
        }
        save_path = self.levels_dir / "progress.json"
        save_path.write_text(json.dumps(old_save), encoding="utf-8")

        five_levels = tuple(
            level
            for level in LevelManager.discover_levels().levels
            if level.number <= 5
        )
        migrated = SaveManager(save_path, five_levels).load()
        self.assertEqual(migrated["level_scores"]["phase-01"], 800)
        self.assertEqual(migrated["best_results"]["phase-01"]["score"], 800)
        self.assertEqual(migrated["last_results"]["phase-01"]["score"], 800)
        self.assertEqual(migrated["completed_level_ids"], phase_ids[:2])

        new_phase = custom_phase()
        write_config(self.levels_dir, "phase-06.json", new_phase)
        six_levels = five_levels + (LevelManager.from_config(new_phase),)
        with_phase_six = SaveManager(save_path, six_levels).load()
        self.assertEqual(with_phase_six["best_results"]["phase-01"]["score"], 800)
        self.assertEqual(with_phase_six["level_scores"]["phase-01"], 800)
        self.assertEqual(with_phase_six["last_results"]["phase-01"]["score"], 800)
        self.assertNotIn("phase-06", with_phase_six["completed_level_ids"])
        progress = ProgressManager(level.identifier for level in six_levels)
        progress.restore(with_phase_six)
        self.assertEqual(progress.recommended_level, "phase-03")
        self.assertTrue(progress.can_start("phase-03"))

        renumbered = tuple(
            replace(level, number=20)
            if level.identifier == "phase-01"
            else level
            for level in six_levels
        )
        after_renumbering = SaveManager(save_path, renumbered).load()
        self.assertEqual(
            after_renumbering["best_results"]["phase-01"]["score"], 800
        )
        self.assertIn("phase-01", after_renumbering["completed_level_ids"])

    def test_order_is_deterministic_and_number_gaps_follow_available_order(self) -> None:
        write_config(self.levels_dir, "z.json", custom_phase("last", 9))
        write_config(self.levels_dir, "a.json", custom_phase("first", 2))

        first = LevelManager.discover_levels(self.levels_dir)
        second = LevelManager.discover_levels(self.levels_dir)

        self.assertEqual(
            [level.identifier for level in first.levels], ["first", "last"]
        )
        self.assertEqual(
            [(level.number, level.identifier) for level in first.levels],
            [(level.number, level.identifier) for level in second.levels],
        )

    def test_new_phase_is_recommended_after_all_current_phases_are_complete(self) -> None:
        old_ids = [f"phase-0{number}" for number in range(1, 6)]
        old_progress = ProgressManager(old_ids)
        for identifier in old_ids:
            old_progress.complete_level(identifier)

        expanded_progress = ProgressManager(old_ids + ["phase-06"])
        expanded_progress.restore(old_progress.to_dict())

        self.assertFalse(expanded_progress.all_levels_complete)
        self.assertEqual(expanded_progress.recommended_level, "phase-06")
        self.assertTrue(expanded_progress.can_start("phase-06"))


if __name__ == "__main__":
    unittest.main()

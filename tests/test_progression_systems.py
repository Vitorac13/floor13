import json
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from level_manager import LevelManager
from systems.menu_manager import MenuManager, Screen
from systems.progress_manager import ProgressManager
from systems.save_manager import SaveManager
from systems.score_manager import ScoreManager
from main import ElevatorPrototype


class ScoreManagerTests(unittest.TestCase):
    def test_current_attempt_score_updates_when_unique_items_are_recorded(self) -> None:
        level = LevelManager.load_level("phase-01")
        manager = ScoreManager()
        manager.begin_attempt("active")

        manager.record_items("active", (level.items[0], level.items[0]))
        self.assertEqual(manager.current_attempt_score, 100)
        manager.record_objectives("active", (level.optional_objectives[0],))

        self.assertEqual(manager.current_attempt_score, 300)

    def test_attempt_rewards_are_unique_and_finalization_is_idempotent(self) -> None:
        level = LevelManager.load_level("phase-01")
        essential = level.items[0]
        bonus = level.items[-1]
        objective = level.optional_objectives[0]
        manager = ScoreManager()

        result = manager.finalize_attempt(
            "attempt-1",
            1,
            items=(essential, essential, bonus),
            objectives=(objective, objective),
            completed_challenges=("collect_and_exit", "collect_and_exit"),
            movements=8,
            elapsed_seconds=12.5,
            completion_score=300,
        )
        repeated = manager.finalize_attempt(
            "attempt-1",
            1,
            items=(),
            objectives=(),
            completed_challenges=(),
            movements=0,
            elapsed_seconds=0,
        )

        self.assertEqual(result.score, 800)
        self.assertEqual(result, repeated)
        self.assertEqual(result.essential_items, ("chave",))
        self.assertEqual(result.bonus_items, ("foto",))
        self.assertEqual(result.movements, 8)


class ProgressManagerTests(unittest.TestCase):
    def test_next_phase_unlocks_and_completed_phases_remain_replayable(self) -> None:
        progress = ProgressManager(phase_count=5)

        self.assertEqual(progress.recommended_level, 1)
        self.assertFalse(progress.can_start(2))
        self.assertTrue(progress.complete_level(1))
        self.assertEqual(progress.recommended_level, 2)
        self.assertTrue(progress.can_start(1))
        self.assertTrue(progress.can_start(2))
        self.assertFalse(progress.complete_level(1))

    def test_recommendation_is_none_when_all_phases_are_complete(self) -> None:
        progress = ProgressManager(phase_count=2)
        progress.complete_level(1)
        progress.complete_level(2)

        self.assertTrue(progress.all_levels_complete)
        self.assertIsNone(progress.recommended_level)


class SaveManagerTests(unittest.TestCase):
    def test_missing_save_is_created_and_result_score_tracks_best_per_phase(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "progress.json"
            manager = SaveManager(path)
            progress = manager.load()
            self.assertTrue(path.exists())
            self.assertEqual(progress["unlocked_levels"], [1])

            progress["completed_levels"] = [1]
            progress["unlocked_levels"] = [1, 2]
            result = {
                "score": 500,
                "essential_items": ["key"],
                "bonus_items": [],
                "completed_challenges": ["standard"],
                "completed_objectives": [],
                "movements": 7,
                "elapsed_seconds": 18.0,
            }
            progress = manager.record_result(progress, 1, result)
            lower_result = dict(result, score=200)
            progress = manager.record_result(progress, 1, lower_result)

            self.assertEqual(progress["level_scores"]["1"], 500)
            self.assertEqual(progress["total_score"], 500)
            self.assertEqual(progress["best_results"]["1"]["score"], 500)
            self.assertEqual(progress["last_results"]["1"]["score"], 200)
            self.assertEqual(manager.load(), progress)

    def test_invalid_save_is_preserved_and_default_progress_is_recreated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "progress.json"
            path.write_text("{invalid json", encoding="utf-8")
            progress = SaveManager(path).load()

            self.assertEqual(progress["unlocked_levels"], [1])
            self.assertTrue(path.exists())
            backups = list(Path(directory).glob("progress.json.invalid-*"))
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_text(encoding="utf-8"), "{invalid json")

    def test_incomplete_save_is_normalized_without_losing_valid_completion(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "progress.json"
            path.write_text(
                json.dumps({"version": 1, "completed_levels": [1]}),
                encoding="utf-8",
            )
            progress = SaveManager(path).load()

            self.assertEqual(progress["unlocked_levels"], [1, 2])
            self.assertEqual(progress["completed_levels"], [1])
            self.assertEqual(progress["level_scores"]["5"], 0)


class MenuManagerTests(unittest.TestCase):
    def test_menu_flow_refuses_locked_phases_and_routes_to_result_and_next(self) -> None:
        menu = MenuManager()
        progress = ProgressManager(phase_count=2)

        self.assertEqual(menu.screen, Screen.MAIN_MENU)
        menu.show_level_select()
        self.assertFalse(menu.start_level(2, progress))
        self.assertTrue(menu.start_level(1, progress))
        self.assertEqual(menu.screen, Screen.GAME)
        menu.show_result(1)
        progress.complete_level(1)
        self.assertEqual(menu.screen, Screen.RESULT)
        self.assertEqual(menu.continue_after_result(progress), 2)
        self.assertEqual(menu.screen, Screen.GAME)


class ApplicationFlowTests(unittest.TestCase):
    def test_returning_to_the_degree_one_start_awards_optional_exploration_points(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            app = ElevatorPrototype(str(Path(directory) / "progress.json"))
            try:
                app._continue_game()
                for destination in (2, 1):
                    app.selected_floor = destination
                    app._travel()

                self.assertEqual(app.score_manager.current_attempt_score, 200)
                self.assertTrue(app.game.returned_to_start)
                self.assertEqual(app.menu.screen, Screen.GAME)
            finally:
                import pygame

                pygame.quit()

    def test_start_phase_result_unlock_and_continue_flow(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            app = ElevatorPrototype(str(Path(directory) / "progress.json"))
            try:
                app._continue_game()
                self.assertEqual(app.menu.screen, Screen.GAME)
                self.assertEqual(app.active_phase, 1)

                for destination in (2, 3, 4):
                    app.selected_floor = destination
                    app._travel()
                    app._collect_items()
                app.selected_floor = 6
                app._travel()

                self.assertEqual(app.menu.screen, Screen.RESULT)
                self.assertEqual(app.progress_manager.recommended_level, "phase-02")
                self.assertEqual(app.saved_progress["completed_levels"], [1])
                self.assertEqual(
                    app.saved_progress["best_results"]["phase-01"]["score"], 600
                )

                app._draw()
                app._continue_after_result()
                self.assertEqual(app.menu.screen, Screen.GAME)
                self.assertEqual(app.active_phase, 2)
                app._draw()
            finally:
                import pygame

                pygame.quit()

    def test_full_seven_phase_flow_preserves_special_challenge_rules(self) -> None:
        routes = {
            1: (2, 3, 4, 6),
            2: (2, 3, 4, 5, 6),
            3: (3, 5, 6),
            4: (2, 3, 1, 4, 5, 2, 4),
            5: (2, 6, 4, 3, 1),
            6: (2, 3, 6),
            7: (2, 4, 6, 5, 6, 7),
        }
        collect_floors = {
            1: {2, 3, 4},
            2: {3},
            3: {3},
            4: {5},
            5: {2},
            6: {3},
            7: {2, 5},
        }
        with tempfile.TemporaryDirectory() as directory:
            app = ElevatorPrototype(str(Path(directory) / "progress.json"))
            try:
                app._continue_game()
                for phase in range(1, 8):
                    self.assertEqual(app.active_phase, phase)
                    for destination in routes[phase]:
                        app.selected_floor = destination
                        app._travel()
                        if destination in collect_floors[phase]:
                            app._collect_items()
                    self.assertEqual(app.menu.screen, Screen.RESULT)
                    self.assertIn(
                        f"phase-0{phase}", app.progress_manager.completed_levels
                    )
                    if phase < 7:
                        app._continue_after_result()
                        self.assertEqual(app.active_phase, phase + 1)

                self.assertTrue(app.progress_manager.all_levels_complete)
                self.assertEqual(
                    app.saved_progress["completed_levels"],
                    [1, 2, 3, 4, 5, 6, 7],
                )
                self.assertEqual(app.progress_manager.recommended_level, None)
                app._continue_after_result()
                self.assertEqual(app.menu.screen, Screen.LEVEL_SELECT)
                app._draw()
            finally:
                import pygame

                pygame.quit()


if __name__ == "__main__":
    unittest.main()

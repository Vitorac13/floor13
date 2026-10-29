import json
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from level_editor import LevelEditor, new_level_config
from level_manager import DEFAULT_LEVELS_DIR, LevelManager
from main import ElevatorPrototype
from systems.menu_manager import Screen
from systems.score_manager import AttemptResult


class LevelEditorTests(unittest.TestCase):
    def setUp(self) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode((960, 640))
        self.editor = LevelEditor()

    def tearDown(self) -> None:
        pygame.quit()

    def _click(self, position: tuple[int, int]) -> None:
        self.editor.handle_event(
            pygame.event.Event(
                pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": position}
            )
        )

    def _type_text(self, text: str) -> None:
        self.editor.handle_event(
            pygame.event.Event(
                pygame.KEYDOWN,
                {"key": pygame.K_a, "mod": pygame.KMOD_CTRL, "unicode": ""},
            )
        )
        for character in text:
            self.editor.handle_event(
                pygame.event.Event(
                    pygame.KEYDOWN,
                    {"key": pygame.K_a, "mod": 0, "unicode": character},
                )
            )
        self.editor.handle_event(
            pygame.event.Event(
                pygame.KEYDOWN,
                {"key": pygame.K_RETURN, "mod": 0, "unicode": "\r"},
            )
        )

    def test_mouse_adds_selects_drags_and_deletes_vertices_and_edges(self) -> None:
        self.editor.draw(self.screen)
        self._click((90, 589))
        self._click((160, 330))
        self.editor.draw(self.screen)
        self._click((90, 589))
        self._click((480, 330))
        self.assertEqual(self.editor.vertices, [1, 2, 3])

        self.editor.draw(self.screen)
        self._click((160, 330))
        self.editor.handle_event(
            pygame.event.Event(
                pygame.MOUSEMOTION,
                {"pos": (180, 340), "rel": (20, 10), "buttons": (1, 0, 0)},
            )
        )
        self.editor.handle_event(
            pygame.event.Event(pygame.MOUSEBUTTONUP, {"button": 1, "pos": (180, 340)})
        )
        self.assertEqual(self.editor.positions[2], (180, 340))
        self.assertEqual(self.editor.selected_vertex, 2)

        self.editor.draw(self.screen)
        self._click((243, 589))
        self._click(self.editor.positions[1])
        self._click(self.editor.positions[2])
        self.assertEqual(self.editor.edges, [[1, 2]])

        self.editor.draw(self.screen)
        self._click((394, 589))
        midpoint = (
            (self.editor.positions[1][0] + self.editor.positions[2][0]) // 2,
            (self.editor.positions[1][1] + self.editor.positions[2][1]) // 2,
        )
        self._click(midpoint)
        self.assertEqual(self.editor.edges, [])

        self.editor.draw(self.screen)
        self._click((545, 589))
        self.assertNotIn(2, self.editor.vertices)
        self.assertEqual(self.editor.vertices, [1, 3])

    def test_mouse_sets_start_and_exit_and_items_can_be_added_and_edited(self) -> None:
        second = self.editor.add_vertex((480, 330))
        self.editor.draw(self.screen)
        self._click(self.editor.positions[1])
        self.editor.draw(self.screen)
        self._click((790, 201))
        self.assertEqual(self.editor.config["start_floor"], 1)

        self.editor.draw(self.screen)
        self._click(self.editor.positions[second])
        self.editor.draw(self.screen)
        self._click((790, 249))
        self.assertEqual(self.editor.config["exit_floor"], second)

        item_index = self.editor.add_item()
        self.editor._begin_edit("item_id")
        self.editor.field_buffer = "essential-key"
        self.assertTrue(self.editor._commit_field())
        self.editor._begin_edit("item_name")
        self.editor.field_buffer = "Chave principal"
        self.assertTrue(self.editor._commit_field())
        self.editor._begin_edit("item_type")
        self.editor.field_buffer = "essential"
        self.assertTrue(self.editor._commit_field())
        self.editor._begin_edit("item_score")
        self.editor.field_buffer = "75"
        self.assertTrue(self.editor._commit_field())
        self.editor.update_item(item_index, key=True, floor=1)

        bonus_index = self.editor.add_item()
        self.editor.update_item(
            bonus_index,
            id="bonus-gem",
            name="Gema bonus",
            floor=second,
            type="bonus",
            score=25,
        )
        self.editor.config["exit_requirements"]["keys"] = ["essential-key"]
        self.editor.config["graph"]["edges"] = [[1, second]]

        self.editor.validate()

        self.assertEqual(self.editor.items[0]["id"], "essential-key")
        self.assertEqual(self.editor.items[1]["type"], "bonus")
        self.assertEqual(self.editor.items[1]["floor"], second)

    def test_mouse_removes_item_and_edge_creation_rejects_duplicate_connections(self) -> None:
        self.editor.add_vertex((480, 330))
        self.editor.add_edge(1, 2)
        with self.assertRaisesRegex(ValueError, "ja existe"):
            self.editor.add_edge(2, 1)
        index = self.editor.add_item()
        self.editor.draw(self.screen)
        self._click((850, 138))
        self.assertEqual(self.editor.items, [])
        self.assertIsNone(self.editor.selected_item)

    def test_item_form_creates_and_edits_essential_and_bonus_items(self) -> None:
        self.editor.add_vertex((480, 330))
        self.editor.add_edge(1, 2)
        self.editor.config["exit_floor"] = 2
        self.editor.draw(self.screen)
        self._click((789, 93))
        self.editor.draw(self.screen)
        self._click((718, 138))

        self.editor.draw(self.screen)
        self._click(self.editor._field_rects["item_id"].center)
        self._type_text("essential-key")
        self.editor.draw(self.screen)
        self._click(self.editor._field_rects["item_name"].center)
        self._type_text("Chave essencial")
        self.editor.draw(self.screen)
        self._click(self.editor._field_rects["item_floor"].center)
        self._type_text("1")
        self.editor.draw(self.screen)
        self._click(self.editor._field_rects["item_score"].center)
        self._type_text("75")
        self.editor.draw(self.screen)
        self._click((790, 602))
        self.assertTrue(self.editor.items[0]["key"])

        self.editor.draw(self.screen)
        self._click((718, 138))
        self.editor.draw(self.screen)
        self._click(self.editor._field_rects["item_id"].center)
        self._type_text("bonus-gem")
        self.editor.draw(self.screen)
        self._click(self.editor._field_rects["item_name"].center)
        self._type_text("Gema bonus")
        self.editor.draw(self.screen)
        self._click(self.editor._field_rects["item_type"].center)
        self._type_text("bonus")
        self.editor.draw(self.screen)
        self._click(self.editor._field_rects["item_score"].center)
        self._type_text("25")

        self.editor.validate()

        self.assertEqual(self.editor.items[0]["type"], "essential")
        self.assertEqual(self.editor.items[0]["floor"], 1)
        self.assertEqual(self.editor.items[1]["type"], "bonus")
        self.assertEqual(self.editor.items[1]["floor"], 2)
        self.assertEqual(self.editor.items[1]["score"], 25)

    def test_optional_objective_can_be_configured_and_removed_visually(self) -> None:
        self.editor.add_vertex((480, 330))
        self.editor.add_edge(1, 2)
        self.editor.config["exit_floor"] = 2
        self.editor.draw(self.screen)
        self._click((909, 93))
        self.editor.draw(self.screen)
        self._click((732, 138))

        self.editor.draw(self.screen)
        self._click(self.editor._field_rects["objective_id"].center)
        self._type_text("visit-hidden-floor")
        self.editor.draw(self.screen)
        self._click(self.editor._field_rects["objective_name"].center)
        self._type_text("Explorar o andar secreto")
        self.editor.draw(self.screen)
        self._click(self.editor._field_rects["objective_reward"].center)
        self._type_text("125")

        self.editor.validate()
        self.assertEqual(self.editor.objectives[0]["id"], "visit-hidden-floor")
        self.assertEqual(self.editor.objectives[0]["reward"], 125)

        self.editor.draw(self.screen)
        self._click((874, 138))
        self.assertEqual(self.editor.objectives, [])

    def test_exit_requirements_can_be_selected_from_the_editor(self) -> None:
        self.editor.add_vertex((480, 330))
        self.editor.add_edge(1, 2)
        self.editor.config["exit_floor"] = 2
        self.editor.add_item()
        self.editor.update_item(0, id="exit-key", key=True, floor=1)
        self.editor.draw(self.screen)
        self._click((849, 93))
        self.editor.draw(self.screen)
        self._click((790, 169))

        self.assertEqual(self.editor.config["exit_requirements"]["keys"], ["exit-key"])

        self.editor.draw(self.screen)
        self._click((790, 369))
        self.assertEqual(
            self.editor.config["exit_requirements"]["challenges"],
            ["collect_and_exit"],
        )
        self.editor.validate()

    def test_import_export_round_trip_preserves_phase_seven_and_loads(self) -> None:
        original_path = DEFAULT_LEVELS_DIR / "phase-07.json"
        original = json.loads(original_path.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "phase-07.json"
            self.editor.import_file(original_path)

            self.assertEqual(self.editor.config, original)
            self.editor.export_file(output)

            exported = json.loads(output.read_text(encoding="utf-8"))
            loaded = LevelManager.load_level("phase-07", directory)
            self.assertEqual(exported, original)
            self.assertEqual(loaded.exit_requires_keys, ("chave-prateada", "chave-dourada"))
            self.assertEqual(loaded.challenge_type, "collect_and_exit")

    def test_new_phase_export_is_loadable_and_existing_files_need_confirmation(self) -> None:
        self.editor.add_vertex((480, 330))
        self.editor.add_edge(1, 2)
        self.editor.config["exit_floor"] = 2
        self.editor.config["id"] = "editor-test"
        self.editor.config["name"] = "Fase do editor"
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "editor-test.json"

            self.editor.export_file(output)
            level = LevelManager.load_level("editor-test", directory)

            self.assertEqual(level.graph.vertices, (1, 2))
            self.assertEqual(level.graph.edge_count, 1)
            with self.assertRaises(FileExistsError):
                self.editor.export_file(output)
            self.editor.export_file(output, overwrite=True)

    def test_export_dialog_waits_for_explicit_overwrite_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "existing.json"
            output.write_text("previous content", encoding="utf-8")
            self.editor.path_dialog = "export"
            self.editor.path_buffer = str(output)
            self.editor.handle_event(
                pygame.event.Event(
                    pygame.KEYDOWN,
                    {"key": pygame.K_RETURN, "mod": 0, "unicode": "\r"},
                )
            )

            self.assertEqual(self.editor.pending_overwrite, output)
            self.assertEqual(output.read_text(encoding="utf-8"), "previous content")
            self.editor.draw(self.screen)
            self._click(self.editor._buttons["overwrite_yes"].center)

            self.assertIsNone(self.editor.pending_overwrite)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["id"], self.editor.config["id"])

    def test_json_rule_fields_are_editable_and_invalid_challenges_are_rejected(self) -> None:
        self.editor.focused_field = "json:optional_objectives"
        self.editor.field_buffer = "[]"
        self.assertTrue(self.editor._commit_field())
        self.editor.config["challenge"]["type"] = "unknown"

        with self.assertRaisesRegex(ValueError, "tipo de desafio desconhecido"):
            self.editor.validate()
        self.assertIn("Fase invalida", self.editor.status)

    def test_new_phase_defaults_to_an_unused_identifier_and_number(self) -> None:
        config = new_level_config()
        existing = LevelManager.discover_levels().levels

        self.assertNotIn(config["id"], {level.identifier for level in existing})
        self.assertNotIn(config["number"], {level.number for level in existing})


class NavigationExitTests(unittest.TestCase):
    def setUp(self) -> None:
        pygame.init()
        self.temporary_directory = tempfile.TemporaryDirectory()
        save_path = str(Path(self.temporary_directory.name) / "progress.json")
        self.app = ElevatorPrototype(save_path)

    def tearDown(self) -> None:
        pygame.quit()
        self.temporary_directory.cleanup()

    def _click(self, position: tuple[int, int]) -> None:
        pygame.event.post(
            pygame.event.Event(
                pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": position}
            )
        )
        self.app._handle_events()

    def test_in_game_menu_discards_attempt_without_score_or_progress(self) -> None:
        self.app._start_phase("phase-01")
        self.app._select_floor(2)
        self.app._travel()
        self.app._collect_items()
        self.assertEqual(self.app.score_manager.current_attempt_score, 100)
        before_completed = set(self.app.progress_manager.completed_levels)
        before_scores = dict(self.app.saved_progress["level_scores"])

        self._click(self.app.game_menu_rect.center)

        self.assertEqual(self.app.menu.screen, Screen.MAIN_MENU)
        self.assertIsNone(self.app.active_state)
        self.assertIsNone(self.app.level)
        self.assertIsNone(self.app.item_progress)
        self.assertEqual(self.app.score_manager.current_attempt_score, 0)
        self.assertEqual(self.app.progress_manager.completed_levels, before_completed)
        self.assertEqual(self.app.saved_progress["level_scores"], before_scores)

    def test_result_has_next_select_and_menu_without_duplicate_select_action(self) -> None:
        level = self.app.levels_by_id["phase-01"]
        self.app.progress_manager.complete_level("phase-01")
        self.app.level = level
        self.app.attempt_result = AttemptResult(
            1, 300, (), (), ("collect_and_exit",), (), 4, 1.0
        )
        self.app.menu.show_result("phase-01")
        completed_before = set(self.app.progress_manager.completed_levels)

        self.app._draw()
        self.assertEqual(self.app.progress_manager.recommended_level, "phase-02")
        self.assertFalse(hasattr(self.app, "result_replay_rect"))
        self.assertTrue(hasattr(self.app, "result_menu_rect"))

        self._click(self.app.result_menu_rect.center)

        self.assertEqual(self.app.menu.screen, Screen.MAIN_MENU)
        self.assertEqual(self.app.progress_manager.completed_levels, completed_before)
        self.assertIsNone(self.app.attempt_result)

    def test_main_menu_opens_editor_and_editor_returns_to_menu(self) -> None:
        self.app._draw()
        self._click(self.app.main_editor_rect.center)

        self.assertEqual(self.app.menu.screen, Screen.LEVEL_EDITOR)
        self.app._draw()
        back_button = self.app.level_editor._buttons["back"]
        self._click(back_button.center)

        self.assertEqual(self.app.menu.screen, Screen.MAIN_MENU)


if __name__ == "__main__":
    unittest.main()

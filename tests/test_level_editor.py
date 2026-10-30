import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from level_editor import LevelEditor, new_level_config
from level_manager import DEFAULT_LEVELS_DIR, LevelManager
from game_state import GameState
from main import ElevatorPrototype
from economic_challenge import EconomicChallengeManager
from systems.menu_manager import Screen
from systems.item_manager import ItemProgress
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
        self.editor.handle_event(
            pygame.event.Event(
                pygame.TEXTINPUT,
                {"text": text},
            )
        )
        self.editor.handle_event(
            pygame.event.Event(
                pygame.KEYDOWN,
                {"key": pygame.K_RETURN, "mod": 0, "unicode": "\r"},
            )
        )

    def _choose_combo_option(self, combo: str, choice: str) -> None:
        self.editor.draw(self.screen)
        self._click(self.editor._buttons[f"{combo}_combo"].center)
        self.editor.draw(self.screen)
        self._click(self.editor._buttons[f"{combo}:{choice}"].center)

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
        self.assertEqual(self.editor.vertices, [1, 2])
        self.assertNotIn(3, self.editor.vertices)

    def test_removing_vertex_renumbers_graph_and_all_floor_references(self) -> None:
        for floor in range(2, 6):
            self.editor.add_vertex((150 + floor * 70, 260))
        self.editor.config["graph"]["edges"] = [
            [1, 4, 11],
            [4, 2, 12],
            [2, 5, 13],
            [5, 3, 14],
        ]
        self.editor.config.update({"start_floor": 5, "exit_floor": 3})
        self.editor.config["items"] = [
            {
                "id": "keep-key",
                "name": "Chave",
                "floor": 5,
                "type": "essential",
                "score": 100,
                "key": True,
            },
            {
                "id": "removed-item",
                "name": "Item removido",
                "floor": 4,
                "type": "bonus",
                "score": 20,
            },
        ]
        self.editor.config["exit_requirements"]["keys"] = ["keep-key"]
        self.editor.config["connection_requirements"] = [
            {"from": 2, "to": 5, "keys": ["keep-key"]},
            {"from": 1, "to": 4, "keys": []},
        ]
        self.editor.config["challenge"] = {
            "type": "economic",
            "destination_floor": 4,
        }
        self.editor.config["optional_objectives"] = [
            {
                "id": "visit",
                "name": "Visite",
                "description": "Visite o andar.",
                "type": "visit_floor",
                "floor": 5,
                "reward": 10,
            }
        ]

        self.editor.remove_vertex(4)
        new_floor = self.editor.add_vertex((400, 400))

        self.assertEqual(self.editor.vertices, [1, 2, 3, 4, 5])
        self.assertEqual(new_floor, 5)
        self.assertEqual(
            self.editor.edges,
            [[2, 4, 13], [4, 3, 14]],
        )
        self.assertEqual(self.editor.config["start_floor"], 4)
        self.assertEqual(self.editor.config["exit_floor"], 3)
        self.assertEqual(self.editor.items[0]["floor"], 4)
        self.assertEqual(self.editor.config["exit_requirements"]["keys"], ["keep-key"])
        self.assertEqual(
            self.editor.config["connection_requirements"],
            [{"from": 2, "to": 4, "keys": ["keep-key"]}],
        )
        self.assertEqual(self.editor.config["challenge"]["destination_floor"], 3)
        self.assertEqual(self.editor.objectives[0]["floor"], 4)

    def test_economic_cost_mode_selects_edges_and_escape_cancels_modes(self) -> None:
        self.editor.add_vertex((480, 330))
        self.editor.add_edge(1, 2)
        self.editor._set_challenge_type("economic")
        self.editor.tab = "edge"
        self.editor.draw(self.screen)
        self._click(self.editor._buttons["mode:edit_cost"].center)
        self.assertEqual(self.editor.mode, "edit_cost")

        midpoint = (
            (self.editor.positions[1][0] + self.editor.positions[2][0]) // 2,
            (self.editor.positions[1][1] + self.editor.positions[2][1]) // 2,
        )
        self._click(midpoint)
        self.assertEqual(self.editor.selected_edge, (1, 2))
        self.editor.draw(self.screen)
        self._click(self.editor._field_rects["edge_cost"].center)
        self._type_text("7")
        self.assertEqual(self.editor.edges[0][2], 7)

        self.editor._begin_edit("edge_cost")
        self.assertFalse(
            self.editor.handle_event(
                pygame.event.Event(
                    pygame.KEYDOWN,
                    {"key": pygame.K_ESCAPE, "mod": 0, "unicode": ""},
                )
            )
        )
        self.assertIsNone(self.editor.focused_field)
        self.assertEqual(self.editor.mode, "edit_cost")
        self.editor.handle_event(
            pygame.event.Event(
                pygame.KEYDOWN,
                {"key": pygame.K_ESCAPE, "mod": 0, "unicode": ""},
            )
        )
        self.assertEqual(self.editor.mode, "select")

        self.editor.mode = "add_edge"
        self.editor.edge_origin = 1
        self.editor.handle_event(
            pygame.event.Event(
                pygame.KEYDOWN,
                {"key": pygame.K_ESCAPE, "mod": 0, "unicode": ""},
            )
        )
        self.assertIsNone(self.editor.edge_origin)
        self.assertEqual(self.editor.mode, "select")

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
        self._choose_combo_option("item_type", "key")
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
        self._choose_combo_option("item_type", "bonus")
        self.editor.draw(self.screen)
        self._click(self.editor._field_rects["item_score"].center)
        self._type_text("25")

        self.editor.validate()

        self.assertEqual(self.editor.items[0]["type"], "key")
        self.assertEqual(self.editor.items[0]["floor"], 1)
        self.assertEqual(self.editor.items[1]["type"], "bonus")
        self.assertEqual(self.editor.items[1]["floor"], 2)
        self.assertEqual(self.editor.items[1]["score"], 25)

    def test_item_type_combobox_supports_keyboard_navigation(self) -> None:
        index = self.editor.add_item()
        self.editor.draw(self.screen)
        self._click(self.editor._buttons["item_type_combo"].center)
        for key in (pygame.K_DOWN, pygame.K_RETURN):
            self.editor.handle_event(
                pygame.event.Event(
                    pygame.KEYDOWN,
                    {"key": key, "mod": 0, "unicode": ""},
                )
            )
        self.assertEqual(self.editor.items[index]["type"], "bonus")
        self.assertFalse(self.editor.items[index]["key"])

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

    def test_supported_item_and_objective_types_round_trip_and_keep_game_rules(self) -> None:
        self.editor.add_vertex((480, 330))
        self.editor.add_edge(1, 2)
        self.editor.config["exit_floor"] = 1

        for item_type, identifier, floor in (
            ("essential", "required-part", 1),
            ("key", "door-key", 1),
            ("bonus", "bonus-map", 2),
        ):
            index = self.editor.add_item()
            self._choose_combo_option("item_type", item_type)
            self.editor.update_item(
                index,
                id=identifier,
                name=identifier,
                floor=floor,
                score=100,
            )
        self.editor.config["exit_requirements"]["keys"] = ["door-key"]

        for objective_type in (
            "visit_floor",
            "collect_all_bonus",
            "return_to_start",
        ):
            index = self.editor.add_objective()
            self._choose_combo_option("objective_type", objective_type)
            self.assertEqual(self.editor.objectives[index]["type"], objective_type)
            self.assertEqual(self.editor.objectives[index]["floor"], 2)

        first_objective = self.editor.objectives[0]
        self.editor.selected_objective = 0
        self._choose_combo_option("objective_type", "collect_all_bonus")
        self._choose_combo_option("objective_type", "visit_floor")
        self.assertEqual(first_objective["floor"], 2)
        self.editor.config["id"] = "combo-round-trip"
        self.editor.config["number"] = 1

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "combo-round-trip.json"
            self.editor.export_file(output)
            exported = json.loads(output.read_text(encoding="utf-8"))
            loaded = LevelManager.load_level("combo-round-trip", directory)

        self.assertEqual(
            [item["type"] for item in exported["items"]],
            ["essential", "key", "bonus"],
        )
        self.assertEqual(
            [objective["type"] for objective in exported["optional_objectives"]],
            ["visit_floor", "collect_all_bonus", "return_to_start"],
        )
        self.assertEqual(loaded.exit_requires_keys, ("door-key",))

        game = GameState(loaded)
        progress = ItemProgress(loaded)
        game.collect_items_here()
        progress.collect(1)
        self.assertEqual(game.collected_required, {"required-part", "door-key"})
        self.assertEqual(game.collected_keys, {"door-key"})
        self.assertEqual(progress.collected_keys, {"door-key"})
        self.assertIn("Voce chegou", game.move_to(2))
        progress.record_movement(2)
        game.collect_items_here()
        progress.collect(2)
        self.assertIn("Fase concluida", game.move_to(1))
        progress.record_movement(1)
        self.assertEqual(
            {objective.kind for objective in progress.completed_objectives},
            {"visit_floor", "collect_all_bonus", "return_to_start"},
        )

        self.editor.tab = "objectives"
        self.editor.draw(self.screen)
        self._click(self.editor._objective_rects[0][1].center)
        self.editor.draw(self.screen)
        self._click(self.editor._field_rects["objective_id"].center)
        self._type_text("edited-objective")
        self.assertEqual(self.editor.objectives[0]["id"], "edited-objective")
        self.editor.draw(self.screen)
        self._click(self.editor._buttons["remove_objective"].center)
        self.assertEqual(len(self.editor.objectives), 2)

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
        self.editor.config["name"] = "Fase do editor com ação"
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "editor-test.json"

            self.editor.export_file(output)
            level = LevelManager.load_level("editor-test", directory)
            exported_text = output.read_text(encoding="utf-8")
            self.assertIn('\n  "graph": {', exported_text)
            self.assertTrue(exported_text.endswith("\n"))

            self.assertEqual(level.graph.vertices, (1, 2))
            self.assertIn("ação", exported_text)
            self.assertEqual(level.name, "Fase do editor com ação")
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

    def test_text_cursor_uses_mouse_position_and_textinput_supports_unicode(self) -> None:
        self.editor.config["name"] = "Fase longa para editar"
        self.editor.draw(self.screen)
        name_rect = self.editor._field_rects["name"]
        self._click((name_rect.left + 38, name_rect.centery))

        self.assertEqual(self.editor.focused_field, "name")
        self.assertGreater(self.editor.cursor_index, 0)
        self.assertLess(self.editor.cursor_index, len(self.editor.field_buffer))
        self.editor.handle_event(
            pygame.event.Event(
                pygame.TEXTINPUT,
                {"text": "é"},
            )
        )
        self.assertIn("é", self.editor.field_buffer)

    def test_challenge_dropdown_maps_supported_labels_and_preserves_parameters(self) -> None:
        self.editor.add_vertex((480, 330))
        self.editor.add_edge(1, 2)
        self.editor.config["exit_floor"] = 2
        self.editor.draw(self.screen)
        self._click((790, 343))
        self.assertTrue(self.editor.dropdown_open)
        self.editor.draw(self.screen)
        self._click((700, 435))
        self.assertEqual(self.editor.config["challenge"]["type"], "economic")
        self.assertEqual(self.editor.config["challenge"]["destination_floor"], 2)
        self.editor._commit_field()
        self.editor._set_challenge_type("hamilton")
        self.editor._set_challenge_type("economic")
        self.assertEqual(self.editor.config["challenge"]["destination_floor"], 2)
        self.assertEqual(self.editor.edges, [[1, 2, 1]])

    def test_economic_edge_cost_round_trip_and_dijkstra_route(self) -> None:
        self.editor.add_vertex((360, 250))
        self.editor.add_vertex((500, 250))
        self.editor.add_edge(1, 2)
        self.editor.add_edge(2, 3)
        self.editor.add_edge(1, 3)
        self.editor._set_challenge_type("economic")
        self.editor.config["exit_floor"] = 3
        self.editor.config["challenge"]["destination_floor"] = 3
        self.editor.tab = "edge"
        self.editor.draw(self.screen)
        self._click(self.editor._buttons["mode:edit_cost"].center)
        midpoint = (
            (self.editor.positions[1][0] + self.editor.positions[2][0]) // 2,
            (self.editor.positions[1][1] + self.editor.positions[2][1]) // 2,
        )
        self._click(midpoint)
        self.assertEqual(self.editor.selected_edge, (1, 2))
        self.editor.draw(self.screen)
        self._click(self.editor._field_rects["edge_cost"].center)
        self._type_text("2")
        self.editor._set_edge_cost((2, 3), "3")
        self.editor._set_edge_cost((1, 3), "10")

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "weighted-test.json"
            self.editor.config["id"] = "weighted-test"
            self.editor.config["number"] = 1
            self.editor.export_file(output)
            level = LevelManager.load_level("weighted-test", directory)
            challenge = EconomicChallengeManager.create_for_level(level)

        self.assertEqual(level.graph.weight(1, 2), 2)
        self.assertEqual(level.graph.weight(2, 3), 3)
        self.assertEqual(challenge.optimal_cost, 5)
        self.assertEqual(challenge.optimal_route, (1, 2, 3))

    def test_economic_edge_cost_rejects_nonpositive_and_nonfinite_values(self) -> None:
        self.editor.add_vertex((480, 330))
        self.editor.add_edge(1, 2)
        self.editor._set_challenge_type("economic")

        for invalid in ("0", "-1", "nan", "inf", "invalid"):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    self.editor._set_edge_cost((1, 2), invalid)


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

    def _send_event(self, event: pygame.event.Event) -> None:
        pygame.event.post(event)
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
        self.assertTrue(hasattr(self.app, "result_replay_rect"))
        self.assertTrue(hasattr(self.app, "result_menu_rect"))

        self._click(self.app.result_menu_rect.center)

        self.assertEqual(self.app.menu.screen, Screen.MAIN_MENU)
        self.assertEqual(self.app.progress_manager.completed_levels, completed_before)
        self.assertIsNone(self.app.attempt_result)

    def test_main_menu_escape_and_window_close_request_confirmation(self) -> None:
        self.app.menu.show_level_select()
        self._send_event(
            pygame.event.Event(
                pygame.KEYDOWN,
                {"key": pygame.K_ESCAPE, "mod": 0, "unicode": ""},
            )
        )
        self.assertEqual(self.app.menu.screen, Screen.MAIN_MENU)
        self.assertFalse(self.app.quit_confirmation_open)

        self._send_event(
            pygame.event.Event(
                pygame.KEYDOWN,
                {"key": pygame.K_ESCAPE, "mod": 0, "unicode": ""},
            )
        )
        self.assertTrue(self.app.quit_confirmation_open)
        self.app._draw()
        self._click(self.app.quit_cancel_rect.center)
        self.assertFalse(self.app.quit_confirmation_open)
        self.assertEqual(self.app.menu.screen, Screen.MAIN_MENU)

        self._click(self.app.main_exit_rect.center)
        self.assertTrue(self.app.quit_confirmation_open)
        self._send_event(
            pygame.event.Event(
                pygame.KEYDOWN,
                {"key": pygame.K_n, "mod": 0, "unicode": "n"},
            )
        )
        self.assertFalse(self.app.quit_confirmation_open)

        self.app._request_quit()
        with patch.object(self.app, "_exit_game") as exit_game:
            self._send_event(
                pygame.event.Event(
                    pygame.MOUSEBUTTONDOWN,
                    {"button": 1, "pos": self.app.quit_confirm_rect.center},
                )
            )
        exit_game.assert_called_once_with()
        self.app.quit_confirmation_open = False

        self._send_event(pygame.event.Event(pygame.QUIT))
        self.assertTrue(self.app.quit_confirmation_open)
        self._send_event(
            pygame.event.Event(
                pygame.KEYDOWN,
                {"key": pygame.K_ESCAPE, "mod": 0, "unicode": ""},
            )
        )
        self.assertFalse(self.app.quit_confirmation_open)

    def test_replay_button_starts_clean_attempt_without_duplicate_completion_score(self) -> None:
        for level_id in ("phase-01", "phase-02", "phase-03", "phase-04", "phase-05"):
            self.app.progress_manager.complete_level(level_id)
        for level_id in ("phase-01", "phase-02", "phase-03", "phase-04", "phase-05"):
            level = self.app.levels_by_id[level_id]
            self.app._start_phase(level_id)
            self.app.saved_progress["level_scores"][level_id] = 432
            self.app.attempt_result = AttemptResult(
                level.number, 999, (), (), ("challenge",), (), 5, 3.0
            )
            self.app.menu.show_result(level_id)
            self.app._draw()
            self._click(self.app.result_replay_rect.center)

            self.assertEqual(self.app.menu.screen, Screen.GAME)
            self.assertEqual(self.app.active_level_id, level_id)
            self.assertEqual(self.app.current_floor, level.start_floor)
            self.assertFalse(self.app.active_state.is_complete)
            self.assertEqual(self.app.attempt_movements, 0)
            self.assertEqual(
                self.app.item_progress.visited_floors,
                {level.start_floor},
            )
            self.assertEqual(self.app.item_progress.movement_count, 0)
            self.assertEqual(self.app.score_manager.current_attempt_score, 0)
            self.assertEqual(self.app.saved_progress["level_scores"][level_id], 432)
            self.assertIn(level_id, self.app.progress_manager.completed_levels)

    def test_main_menu_opens_editor_and_editor_returns_to_menu(self) -> None:
        self.app._draw()
        self._click(self.app.main_editor_rect.center)

        self.assertEqual(self.app.menu.screen, Screen.LEVEL_EDITOR)
        self.app._draw()
        back_button = self.app.level_editor._buttons["back"]
        self._click(back_button.center)

        self.assertEqual(self.app.menu.screen, Screen.MAIN_MENU)

    def test_escape_in_editor_cancels_active_tool_without_quitting(self) -> None:
        self.app.menu.show_level_editor()
        self.app.level_editor.mode = "add_edge"
        self.app.level_editor.edge_origin = 1

        self._send_event(
            pygame.event.Event(
                pygame.KEYDOWN,
                {"key": pygame.K_ESCAPE, "mod": 0, "unicode": ""},
            )
        )

        self.assertEqual(self.app.menu.screen, Screen.LEVEL_EDITOR)
        self.assertEqual(self.app.level_editor.mode, "select")
        self.assertIsNone(self.app.level_editor.edge_origin)
        self.assertFalse(self.app.quit_confirmation_open)

    def test_export_refreshes_level_indexes_and_preserves_existing_progress(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            levels_dir = Path(directory) / "levels"
            levels_dir.mkdir()
            first = new_level_config(levels_dir)
            (levels_dir / f"{first['id']}.json").write_text(
                json.dumps(first), encoding="utf-8"
            )
            app = ElevatorPrototype(
                str(Path(directory) / "progress.json"),
                levels_dir=levels_dir,
            )
            app.progress_manager.complete_level(first["id"])
            app.saved_progress["level_scores"][first["id"]] = 120

            editor = app.level_editor
            editor.new_level()
            output = levels_dir / f"{editor.config['id']}.json"
            editor.export_file(output)

            self.assertEqual(len(app.phase_levels), 2)
            self.assertEqual(app._level_select_range_label(), "Fases 1-2 de 2")
            self.assertIn(editor.config["id"], app.levels_by_id)
            self.assertEqual(
                app.levels_by_number[editor.config["number"]].identifier,
                editor.config["id"],
            )
            self.assertIn(first["id"], app.progress_manager.completed_levels)
            self.assertEqual(app.saved_progress["level_scores"][first["id"]], 120)

            editor.export_file(output, overwrite=True)
            self.assertEqual(len(app.phase_levels), 2)

    def test_level_select_scrolls_all_levels_and_updates_visible_buttons(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            levels_dir = Path(directory) / "levels"
            levels_dir.mkdir()
            for number in range(1, 9):
                config = new_level_config(levels_dir)
                config["id"] = f"phase-{number:02d}"
                config["number"] = number
                (levels_dir / f"{config['id']}.json").write_text(
                    json.dumps(config), encoding="utf-8"
                )
            app = ElevatorPrototype(
                str(Path(directory) / "progress.json"),
                levels_dir=levels_dir,
            )
            app.menu.show_level_select()
            app._draw_level_select()
            self.assertEqual(len(app.level_rects), 6)
            self.assertEqual(
                app._level_select_range_label(),
                "Fases 1-6 de 8  |  Role para baixo para ver mais fases",
            )

            pygame.event.post(
                pygame.event.Event(pygame.MOUSEWHEEL, {"y": -1})
            )
            app._handle_events()
            self.assertEqual(app.level_select_offset, 1)
            app._draw_level_select()
            track, thumb = app._level_select_scroll_metrics()
            self.assertLess(thumb.height, track.height)
            pygame.event.post(
                pygame.event.Event(
                    pygame.MOUSEBUTTONDOWN,
                    {"button": 1, "pos": (track.centerx, thumb.bottom + 5)},
                )
            )
            app._handle_events()
            self.assertEqual(app.level_select_offset, 2)

            app._draw_level_select()
            track, thumb = app._level_select_scroll_metrics()
            pygame.event.post(
                pygame.event.Event(
                    pygame.MOUSEBUTTONDOWN,
                    {"button": 1, "pos": (track.centerx, track.top + 5)},
                )
            )
            app._handle_events()
            self.assertEqual(app.level_select_offset, 0)

            app._draw_level_select()
            track, thumb = app._level_select_scroll_metrics()
            pygame.event.post(
                pygame.event.Event(
                    pygame.MOUSEBUTTONDOWN,
                    {"button": 1, "pos": thumb.center},
                )
            )
            app._handle_events()
            self.assertTrue(app.level_select_dragging)
            pygame.event.post(
                pygame.event.Event(
                    pygame.MOUSEMOTION,
                    {
                        "pos": (track.centerx, track.bottom - 1),
                        "rel": (0, 100),
                        "buttons": (1, 0, 0),
                    },
                )
            )
            app._handle_events()
            self.assertEqual(app.level_select_offset, 2)
            self.assertEqual(app.menu.screen, Screen.LEVEL_SELECT)
            pygame.event.post(
                pygame.event.Event(
                    pygame.MOUSEBUTTONUP,
                    {"button": 1, "pos": (track.centerx, track.bottom - 1)},
                )
            )
            app._handle_events()
            self.assertFalse(app.level_select_dragging)

            app._draw_level_select()
            self.assertEqual(
                app._level_select_range_label(),
                "Fases 3-8 de 8  |  Role para baixo para ver mais fases",
            )
            self.assertEqual(
                list(app.level_rects),
                [f"phase-{number:02d}" for number in range(3, 9)],
            )
            app.progress_manager.complete_level("phase-01")
            app.progress_manager.complete_level("phase-02")
            pygame.event.post(
                pygame.event.Event(
                    pygame.MOUSEBUTTONDOWN,
                    {"button": 1, "pos": app.level_rects["phase-03"].center},
                )
            )
            app._handle_events()
            self.assertEqual(app.menu.screen, Screen.GAME)
            self.assertEqual(app.active_level_id, "phase-03")

            app.menu.show_level_select()
            app.level_select_offset = 0
            app._running = True
            app._resize_window(1600, 1000)
            app._draw_level_select()
            track, thumb = app._level_select_scroll_metrics()
            viewport, scale = app._content_viewport()

            def window_position(position: tuple[int, int]) -> tuple[int, int]:
                return (
                    round(viewport.x + position[0] * scale),
                    round(viewport.y + position[1] * scale),
                )

            pygame.event.post(
                pygame.event.Event(
                    pygame.MOUSEBUTTONDOWN,
                    {"button": 1, "pos": window_position(thumb.center)},
                )
            )
            app._handle_events()
            pygame.event.post(
                pygame.event.Event(
                    pygame.MOUSEMOTION,
                    {
                        "pos": window_position((track.centerx, track.bottom - 1)),
                        "rel": (100, 100),
                        "buttons": (1, 0, 0),
                    },
                )
            )
            app._handle_events()
            self.assertEqual(app.level_select_offset, 2)
            pygame.event.post(
                pygame.event.Event(
                    pygame.MOUSEBUTTONUP,
                    {"button": 1, "pos": window_position((track.centerx, track.bottom - 1))},
                )
            )
            app._handle_events()
            app._running = False


if __name__ == "__main__":
    unittest.main()

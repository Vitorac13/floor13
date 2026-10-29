import json
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from main import ElevatorPrototype, HEIGHT, WIDTH
from systems.menu_manager import Screen


class ControlsNavigationTests(unittest.TestCase):
    def setUp(self) -> None:
        pygame.init()
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.save_path = str(Path(self.temporary_directory.name) / "progress.json")
        self.app = ElevatorPrototype(self.save_path)
        pygame.event.clear()

    def tearDown(self) -> None:
        pygame.quit()
        self.temporary_directory.cleanup()

    def _post_click(
        self, position: tuple[int, int], app: ElevatorPrototype | None = None
    ) -> None:
        target = app or self.app
        pygame.event.post(
            pygame.event.Event(
                pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": position}
            )
        )
        target._handle_events()

    def _post_key(self, key: int, app: ElevatorPrototype | None = None) -> None:
        target = app or self.app
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, {"key": key, "mod": 0}))
        target._handle_events()

    def _start_phase(self, identifier: str) -> None:
        level = self.app.levels_by_id[identifier]
        for phase in self.app.phase_levels:
            if phase.number < level.number:
                self.app.progress_manager.complete_level(phase.identifier)
        self.app._start_phase(identifier)

    def _move_with_keyboard(self, destination: int) -> None:
        neighbor_count = len(
            self.app.active_graph.neighbors(self.app.current_floor)
        )
        for _ in range(neighbor_count):
            self._post_key(pygame.K_TAB)
            if self.app.selected_floor == destination:
                break
        self.assertEqual(self.app.selected_floor, destination)
        self._post_key(pygame.K_RETURN)
        self.assertEqual(self.app.current_floor, destination)

    def test_mouse_selects_destination_and_clicking_travel_moves(self) -> None:
        self._start_phase("phase-01")
        self.app._draw_destination_panel()
        destination_rect = self.app.destination_rects[2]

        self._post_click(destination_rect.center)
        self.assertEqual(self.app.selected_floor, 2)
        self._post_click(self.app.travel_rect.center)

        self.assertEqual(self.app.current_floor, 2)
        self.assertIsNone(self.app.selected_floor)

    def test_mouse_collect_button_collects_items(self) -> None:
        self._start_phase("phase-01")
        self.app._select_floor(2)
        self.app._travel()
        self.app._draw_destination_panel()

        self._post_click(self.app.collect_rect.center)

        self.assertEqual(self.app.game.collected_keys, {"chave"})

    def test_mouse_clicks_work_in_main_level_select_and_result_menus(self) -> None:
        self._post_click(self.app.main_select_rect.center)
        self.assertEqual(self.app.menu.screen, Screen.LEVEL_SELECT)

        self.app._draw_level_select()
        self._post_click(self.app.level_rects["phase-01"].center)
        self.assertEqual(self.app.menu.screen, Screen.GAME)

        self.app.menu.show_result("phase-01")
        self._post_click(self.app.result_select_rect.center)
        self.assertEqual(self.app.menu.screen, Screen.LEVEL_SELECT)

    def test_window_opens_large_and_resizes_with_a_minimum_logical_size(self) -> None:
        self.assertEqual(self.app.window.get_size(), (1280, 720))
        self.assertTrue(self.app.window.get_flags() & pygame.RESIZABLE)

        pygame.event.post(
            pygame.event.Event(
                pygame.VIDEORESIZE, {"w": 1440, "h": 900, "size": (1440, 900)}
            )
        )
        self.app._handle_events()
        self.assertEqual(self.app.window.get_size(), (1440, 900))

        self.app._resize_window(800, 500)
        self.assertEqual(self.app.window.get_size(), (WIDTH, HEIGHT))
        self.app._resize_window(1280, 720)

    def test_mouse_coordinates_are_scaled_after_resize(self) -> None:
        self.app._resize_window(1440, 900)
        self.app._running = True
        viewport, scale = self.app._content_viewport()
        button_center = self.app.main_select_rect.center
        physical_position = (
            viewport.x + round(button_center[0] * scale),
            viewport.y + round(button_center[1] * scale),
        )
        event = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            {"button": 1, "pos": physical_position},
        )
        pygame.event.clear()
        pygame.event.post(event)
        self.app._handle_events()

        self.assertEqual(self.app.menu.screen, Screen.LEVEL_SELECT)
        self.app._running = False

    def test_menu_background_is_optional_and_images_are_center_cropped(self) -> None:
        self.assertIsNone(self.app.menu_background)
        self.app._draw()
        with tempfile.TemporaryDirectory() as directory:
            image_path = Path(directory) / "menu_background.png"
            image = pygame.Surface((4, 2))
            image.fill((20, 40, 60))
            pygame.image.save(image, image_path)
            self.app.menu_background_path = image_path

            loaded = self.app._load_menu_background()
            covered = self.app._cover_image(loaded, (960, 640))

            self.assertEqual(covered.get_size(), (960, 640))
            self.assertEqual(covered.get_at((480, 320))[:3], (20, 40, 60))
            self.app.menu_background = loaded
            self.app._draw()
            self.assertEqual(
                self.app._scaled_menu_background_size, self.app.window.get_size()
            )
            self.app._resize_window(1400, 900)
            self.app._draw()
            self.assertEqual(
                self.app._scaled_menu_background_size, self.app.window.get_size()
            )

    def test_mouse_wheel_only_scrolls_the_level_list(self) -> None:
        self._start_phase("phase-01")
        pygame.event.post(
            pygame.event.Event(pygame.MOUSEWHEEL, {"x": 0, "y": 2})
        )

        self.app._handle_events()

        self.assertEqual(self.app.level_select_offset, 0)
        self.assertEqual(self.app.current_floor, 1)

    def test_phase_seven_keyboard_reaches_floor_seven_only_after_both_keys(self) -> None:
        self._start_phase("phase-07")

        for destination in (2,):
            self._move_with_keyboard(destination)
        self._post_key(pygame.K_e)
        self._move_with_keyboard(4)
        self._move_with_keyboard(6)
        self._move_with_keyboard(5)
        self._post_key(pygame.K_e)
        self.assertEqual(
            self.app.game.collected_keys,
            {"chave-prateada", "chave-dourada"},
        )
        self._move_with_keyboard(6)
        self._move_with_keyboard(7)

        self.assertTrue(self.app.game.is_complete)
        self.assertEqual(self.app.menu.result_level, "phase-07")

    def test_keyboard_navigation_handles_sparse_vertex_ids_above_nine(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            levels_dir = Path(directory)
            phase = {
                "id": "sparse-floors",
                "number": 1,
                "name": "Andares esparsos",
                "graph": {
                    "vertices": [2, 10, 20, 50],
                    "edges": [[2, 10], [10, 20], [10, 50], [50, 20]],
                },
                "start_floor": 2,
                "exit_floor": 20,
                "items": [],
                "exit_requirements": {"keys": [], "challenges": []},
                "challenge": {"type": "collect_and_exit"},
                "optional_objectives": [],
                "rewards": {"completion": 100},
            }
            (levels_dir / "sparse-floors.json").write_text(
                json.dumps(phase), encoding="utf-8"
            )
            app = ElevatorPrototype(
                str(levels_dir / "progress.json"), levels_dir
            )
            try:
                app._start_phase("sparse-floors")
                pygame.event.clear()
                app._handle_events()
                app._cycle_destination()
                self.assertEqual(app.selected_floor, 10)
                self._post_key(pygame.K_RETURN, app)
                self.assertEqual(app.current_floor, 10)

                app._cycle_destination()
                self.assertEqual(app.selected_floor, 2)
                app._cycle_destination()
                self.assertEqual(app.selected_floor, 20)
                self._post_key(pygame.K_RETURN, app)

                self.assertEqual(app.current_floor, 20)
                self.assertTrue(app.active_state.is_complete)
            finally:
                pygame.quit()

    def test_unconnected_destination_cannot_be_selected(self) -> None:
        self._start_phase("phase-07")

        self.app._select_floor(99)

        self.assertIsNone(self.app.selected_floor)
        self.assertIn("Nao ha elevador", self.app.message)
        self.assertNotIn(99, self.app.level.graph.vertices)

    def test_high_degree_panel_paginates_every_connected_destination_on_screen(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            levels_dir = Path(directory)
            vertices = [1, 10, 20, 30, 40, 50, 60]
            phase = {
                "id": "wide-floor",
                "number": 1,
                "name": "Muitas conexoes",
                "graph": {
                    "vertices": vertices,
                    "edges": [[1, floor] for floor in vertices[1:]],
                },
                "start_floor": 1,
                "exit_floor": 10,
                "items": [],
                "exit_requirements": {"keys": [], "challenges": []},
                "challenge": {"type": "collect_and_exit"},
                "optional_objectives": [],
                "rewards": {"completion": 100},
            }
            (levels_dir / "wide-floor.json").write_text(
                json.dumps(phase), encoding="utf-8"
            )
            app = ElevatorPrototype(
                str(levels_dir / "progress.json"), levels_dir
            )
            try:
                app._start_phase("wide-floor")
                app._draw_destination_panel()
                self.assertEqual(set(app.destination_rects), {10, 20, 30, 40})
                self.assertEqual(len(app.destination_page_rects), 2)
                self.assertTrue(
                    all(
                        rect.left >= 0
                        and rect.right <= WIDTH
                        and rect.top >= 0
                        and rect.bottom <= HEIGHT
                        for rect in (
                            list(app.destination_rects.values())
                            + list(app.destination_page_rects.values())
                        )
                    )
                )

                self._post_click(app.destination_page_rects["next"].center, app)
                app._draw_destination_panel()

                self.assertEqual(set(app.destination_rects), {50, 60})
                self._post_click(app.destination_rects[60].center, app)
                self.assertEqual(app.selected_floor, 60)
            finally:
                pygame.quit()

    def test_keyboard_navigation_keeps_hamilton_and_euler_restrictions(self) -> None:
        self._start_phase("phase-02")
        self._move_with_keyboard(2)
        self.app._cycle_destination()
        self.assertNotEqual(self.app.selected_floor, 1)

        self._start_phase("phase-04")
        self._move_with_keyboard(2)
        self.app._cycle_destination()
        self.assertNotEqual(self.app.selected_floor, 1)


if __name__ == "__main__":
    unittest.main()

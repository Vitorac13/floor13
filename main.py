"""Interface Pygame das fases implementadas de Floor 13."""

from __future__ import annotations

import sys
import time
from math import cos, pi, sin
from pathlib import Path
from uuid import uuid4

import pygame

from game_state import GameState
from graph import Graph
from level import ItemKind, Level, OptionalObjective
from level_editor import LevelEditor
from level_manager import DEFAULT_LEVELS_DIR, LevelManager
from challenge_registry import ChallengeRegistry, ChallengeState
from systems.item_manager import ItemProgress
from systems.menu_manager import MenuManager, Screen
from systems.progress_manager import ProgressManager
from systems.save_manager import SaveError, SaveManager
from systems.score_manager import AttemptResult, ScoreManager

WIDTH = 960
HEIGHT = 640
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
BACKGROUND = (19, 22, 32)
PANEL = (31, 36, 50)
PANEL_LIGHT = (43, 50, 67)
TEXT = (239, 241, 247)
MUTED = (160, 170, 190)
ACCENT = (100, 208, 190)
ACCENT_DARK = (43, 125, 117)
WARNING = (244, 190, 105)


class ElevatorPrototype:
    def __init__(
        self, save_path: str | None = None, levels_dir: str | Path | None = None
    ) -> None:
        pygame.init()
        self.levels_dir = Path(levels_dir) if levels_dir is not None else DEFAULT_LEVELS_DIR
        discovery = LevelManager.discover_levels(self.levels_dir)
        self.phase_levels = discovery.levels
        self.phase_diagnostics = discovery.diagnostics
        self.levels_by_id = {level.identifier: level for level in self.phase_levels}
        self.levels_by_number = {level.number: level for level in self.phase_levels}
        self.level: Level | None = None
        self.active_state: ChallengeState | None = None
        self.game: GameState | None = None
        self.hamilton_challenge = None
        self.hamilton_game = None
        self.economic_challenge = None
        self.economic_game = None
        self.euler_challenge = None
        self.euler_game = None
        self.final_challenge = None
        self.final_game = None
        self.active_phase: int | None = None
        self.active_level_id: str | None = None
        self.save_manager = SaveManager(save_path, self.phase_levels)
        self.saved_progress = self.save_manager.load()
        self.progress_manager = ProgressManager(
            level.identifier for level in self.phase_levels
        )
        self.progress_manager.restore(self.saved_progress)
        self.score_manager = ScoreManager()
        self.menu = MenuManager()
        self.level_editor = LevelEditor(self.levels_dir, self._refresh_levels)
        self.item_progress: ItemProgress | None = None
        self.level_select_offset = 0
        self.level_select_dragging = False
        self.level_select_drag_offset = 0
        self.attempt_result: AttemptResult | None = None
        self.attempt_id = str(uuid4())
        self.attempt_started_at = time.monotonic()
        self.attempt_movements = 0
        pygame.display.set_caption("Floor 13")
        self.window = pygame.display.set_mode(
            (WINDOW_WIDTH, WINDOW_HEIGHT), pygame.RESIZABLE
        )
        self.screen = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self._running = False
        self.menu_background_path = (
            Path(__file__).resolve().parent / "assets" / "menu_background.png"
        )
        self.menu_background = self._load_menu_background()
        self._scaled_menu_background: pygame.Surface | None = None
        self._scaled_menu_background_size: tuple[int, int] | None = None
        self._menu_background_overlay: pygame.Surface | None = None
        self._menu_background_overlay_size: tuple[int, int] | None = None
        self.clock = pygame.time.Clock()
        self.title_font = pygame.font.Font(None, 42)
        self.menu_title_font = pygame.font.Font(None, 76)
        self.heading_font = pygame.font.Font(None, 29)
        self.body_font = pygame.font.Font(None, 24)
        self.small_font = pygame.font.Font(None, 20)
        self.floor_font = pygame.font.Font(None, 96)
        self.selected_floor: int | None = None
        self.message = "Explore os andares e colete os itens para encontrar a saida."
        self.destination_rects: dict[int, pygame.Rect] = {}
        self.destination_page = 0
        self.destination_page_size = 4
        self.destination_page_rects: dict[str, pygame.Rect] = {}
        self.collect_rect = pygame.Rect(600, 444, 270, 54)
        self.travel_rect = pygame.Rect(600, 510, 270, 58)
        self.main_continue_rect = pygame.Rect(64, 250, 340, 56)
        self.main_select_rect = pygame.Rect(64, 318, 340, 56)
        self.main_editor_rect = pygame.Rect(64, 386, 340, 56)
        self.main_exit_rect = pygame.Rect(64, 454, 340, 56)
        self.level_rects: dict[str, pygame.Rect] = {}
        self.level_back_rect = pygame.Rect(64, 570, 190, 48)
        self.result_replay_rect = pygame.Rect(40, 520, 210, 54)
        self.result_continue_rect = pygame.Rect(260, 520, 210, 54)
        self.result_select_rect = pygame.Rect(480, 520, 210, 54)
        self.result_menu_rect = pygame.Rect(700, 520, 210, 54)
        self.game_menu_rect = pygame.Rect(786, 40, 110, 40)
        self.hint_rect = pygame.Rect(650, 40, 120, 40)
        self.hint_close_rect = pygame.Rect(405, 500, 150, 48)
        self.hint_open = False
        self.quit_confirmation_open = False
        self.quit_confirm_rect = pygame.Rect(280, 345, 180, 52)
        self.quit_cancel_rect = pygame.Rect(500, 345, 180, 52)

    @property
    def current_floor(self) -> int:
        if self.active_state is None:
            raise RuntimeError("Nao ha fase ativa.")
        return self.active_state.current_floor

    @property
    def active_graph(self) -> Graph[int]:
        if self.level is None:
            raise RuntimeError("Nao ha fase ativa.")
        return self.level.graph

    def run(self) -> None:
        self._running = True
        while True:
            self._handle_events()
            self._draw()
            self.clock.tick(60)

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type in (
                pygame.VIDEORESIZE,
                getattr(pygame, "WINDOWRESIZED", -1),
                getattr(pygame, "WINDOWSIZECHANGED", -1),
            ):
                size = getattr(event, "size", None)
                if size is None:
                    size = (
                        getattr(event, "w", getattr(event, "x", WINDOW_WIDTH)),
                        getattr(event, "h", getattr(event, "y", WINDOW_HEIGHT)),
                    )
                self._resize_window(*size)
                continue
            event = self._to_logical_event(event)
            if event.type == pygame.QUIT:
                self._request_quit()
                continue
            if self.quit_confirmation_open:
                self._handle_quit_confirmation(event)
                continue
            if self.menu.screen is Screen.LEVEL_EDITOR:
                if self.level_editor.handle_event(event):
                    self._return_to_main_menu()
                continue
            if self.hint_open:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.hint_open = False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.hint_close_rect.collidepoint(event.pos):
                        self.hint_open = False
                continue
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.menu.screen is Screen.MAIN_MENU:
                        self._request_quit()
                    elif self.menu.screen is Screen.LEVEL_SELECT:
                        self.menu.show_main_menu()
                    else:
                        self._return_to_main_menu()
                    continue
                if self.menu.screen is Screen.MAIN_MENU:
                    if event.key == pygame.K_RETURN:
                        self._continue_game()
                    elif event.key == pygame.K_s:
                        self.menu.show_level_select()
                    continue
                if self.menu.screen is Screen.LEVEL_SELECT:
                    if event.key == pygame.K_BACKSPACE:
                        self.menu.show_main_menu()
                    elif pygame.K_1 <= event.key <= pygame.K_9:
                        level = self.levels_by_number.get(event.key - pygame.K_0)
                        if level is not None:
                            self._start_phase(level.identifier)
                    continue
                if self.menu.screen is Screen.RESULT:
                    if event.key == pygame.K_RETURN:
                        self._continue_after_result()
                    elif event.key == pygame.K_r:
                        self._replay_result()
                    elif event.key == pygame.K_s:
                        self._return_to_level_select()
                    elif event.key == pygame.K_m:
                        self._return_to_main_menu()
                    continue

                if event.key == pygame.K_m:
                    self._return_to_main_menu()
                elif event.key == pygame.K_r:
                    if self.level is not None and self.level.challenge_type != "collect_and_exit":
                        self._restart_active_attempt()
                elif event.key == pygame.K_RETURN:
                    self._travel()
                elif event.key == pygame.K_e:
                    self._collect_items()
                elif event.key in (
                    pygame.K_TAB,
                    pygame.K_UP,
                    pygame.K_DOWN,
                    pygame.K_LEFT,
                    pygame.K_RIGHT,
                ):
                    reverse = event.key in (pygame.K_UP, pygame.K_LEFT)
                    if event.key == pygame.K_TAB:
                        reverse = bool(event.mod & pygame.KMOD_SHIFT)
                    self._cycle_destination(reverse)
                continue

            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self.level_select_dragging = False
                continue
            if event.type == pygame.MOUSEMOTION and self.level_select_dragging:
                if self.menu.screen is Screen.LEVEL_SELECT:
                    self._drag_level_select_thumb(event.pos[1])
                else:
                    self.level_select_dragging = False
                continue
            if (
                event.type == pygame.MOUSEWHEEL
                and self.menu.screen is Screen.LEVEL_SELECT
            ):
                self._scroll_level_select(-event.y)
                continue

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.menu.screen is Screen.MAIN_MENU:
                    if self.main_continue_rect.collidepoint(event.pos):
                        self._continue_game()
                    elif self.main_select_rect.collidepoint(event.pos):
                        self.menu.show_level_select()
                    elif self.main_editor_rect.collidepoint(event.pos):
                        self.menu.show_level_editor()
                    elif self.main_exit_rect.collidepoint(event.pos):
                        self._request_quit()
                    continue
                if self.menu.screen is Screen.LEVEL_SELECT:
                    if self.level_back_rect.collidepoint(event.pos):
                        self.menu.show_main_menu()
                        continue
                    if len(self.phase_levels) > 6:
                        track, thumb = self._level_select_scroll_metrics()
                        if track.collidepoint(event.pos):
                            if thumb.collidepoint(event.pos):
                                self.level_select_dragging = True
                                self.level_select_drag_offset = event.pos[1] - thumb.y
                            else:
                                self._scroll_level_select(
                                    -6 if event.pos[1] < thumb.top else 6
                                )
                            continue
                    for phase, rect in self.level_rects.items():
                        if rect.collidepoint(event.pos):
                            self._start_phase(phase)
                            break
                    continue
                if self.menu.screen is Screen.RESULT:
                    if (
                        self.progress_manager.recommended_level is not None
                        and self.result_continue_rect.collidepoint(event.pos)
                    ):
                        self._continue_after_result()
                    elif self.result_replay_rect.collidepoint(event.pos):
                        self._replay_result()
                    elif self.result_select_rect.collidepoint(event.pos):
                        self._return_to_level_select()
                    elif self.result_menu_rect.collidepoint(event.pos):
                        self._return_to_main_menu()
                    continue
                if self.menu.screen is not Screen.GAME:
                    continue
                if self.hint_rect.collidepoint(event.pos):
                    self.hint_open = True
                    continue
                if self.game_menu_rect.collidepoint(event.pos):
                    self._return_to_main_menu()
                    continue
                previous_page = self.destination_page_rects.get("previous")
                next_page = self.destination_page_rects.get("next")
                if previous_page is not None and previous_page.collidepoint(event.pos):
                    self.destination_page = max(0, self.destination_page - 1)
                    continue
                if next_page is not None and next_page.collidepoint(event.pos):
                    self.destination_page = min(
                        self.destination_page + 1,
                        max(
                            0,
                            (
                                len(self.active_graph.neighbors(self.current_floor))
                                + self.destination_page_size
                                - 1
                            )
                            // self.destination_page_size
                            - 1,
                        ),
                    )
                    continue
                if self.collect_rect.collidepoint(event.pos):
                    self._collect_items()
                    continue
                if self.travel_rect.collidepoint(event.pos):
                    self._travel()
                    continue
                for floor, rect in self.destination_rects.items():
                    if rect.collidepoint(event.pos):
                        self._select_floor(floor)
                        break

    def _resize_window(self, width: int, height: int) -> None:
        self.window = pygame.display.set_mode(
            (max(WIDTH, int(width)), max(HEIGHT, int(height))),
            pygame.RESIZABLE,
        )

    def _content_viewport(self) -> tuple[pygame.Rect, float]:
        window_width, window_height = self.window.get_size()
        scale = min(window_width / WIDTH, window_height / HEIGHT)
        content_width = round(WIDTH * scale)
        content_height = round(HEIGHT * scale)
        return (
            pygame.Rect(
                (window_width - content_width) // 2,
                (window_height - content_height) // 2,
                content_width,
                content_height,
            ),
            scale,
        )

    def _to_logical_event(self, event: pygame.event.Event) -> pygame.event.Event:
        if not self._running or not hasattr(event, "pos"):
            return event
        viewport, scale = self._content_viewport()
        position = event.pos
        if not viewport.collidepoint(position):
            logical_position = (-1, -1)
        else:
            logical_position = (
                round((position[0] - viewport.x) / scale),
                round((position[1] - viewport.y) / scale),
            )
        attributes = dict(event.dict)
        attributes["pos"] = logical_position
        if hasattr(event, "rel"):
            attributes["rel"] = (
                round(event.rel[0] / scale),
                round(event.rel[1] / scale),
            )
        return pygame.event.Event(event.type, attributes)

    def _load_menu_background(self) -> pygame.Surface | None:
        try:
            return pygame.image.load(self.menu_background_path).convert()
        except (OSError, pygame.error) as error:
            if self.menu_background_path.exists():
                print(
                    "Aviso: nao foi possivel carregar o fundo do menu "
                    f"{self.menu_background_path}: {error}"
                )
            return None

    def _continue_game(self) -> None:
        recommended = self.progress_manager.recommended_level
        if recommended is None:
            self.menu.show_level_select()
            self.message = (
                "Todo o conteudo disponivel foi concluido. "
                "Escolha uma fase para rejogar."
            )
            return
        self._start_phase(recommended)

    def _start_phase(self, phase: int | str) -> None:
        level = (
            self.levels_by_id.get(phase)
            if isinstance(phase, str)
            else self.levels_by_number.get(phase)
        )
        if level is None:
            self.message = f"A fase {phase} nao esta disponivel."
            return
        if not self.menu.start_level(level.identifier, self.progress_manager):
            self.message = f"A fase {level.number} esta bloqueada."
            return
        self.level = level
        self.active_level_id = level.identifier
        self.active_phase = level.number
        self.hint_open = False
        self.active_state = ChallengeRegistry.create_state(level)
        challenge_type = level.challenge_type
        self.game = (
            self.active_state
            if isinstance(self.active_state, GameState)
            else None
        )
        self.hamilton_game = self.active_state if challenge_type == "hamilton" else None
        self.economic_game = self.active_state if challenge_type == "economic" else None
        self.euler_game = self.active_state if challenge_type == "euler" else None
        self.final_game = self.active_state if challenge_type == "final" else None
        self.hamilton_challenge = (
            getattr(self.active_state, "challenge", None)
            if challenge_type == "hamilton"
            else None
        )
        self.economic_challenge = (
            getattr(self.active_state, "challenge", None)
            if challenge_type == "economic"
            else None
        )
        self.euler_challenge = (
            getattr(self.active_state, "challenge", None)
            if challenge_type == "euler"
            else None
        )
        self.final_challenge = (
            getattr(self.active_state, "challenge", None)
            if challenge_type == "final"
            else None
        )
        self.item_progress = ItemProgress(level)
        self.attempt_result = None
        self.attempt_id = str(uuid4())
        self.score_manager.begin_attempt(self.attempt_id)
        self.attempt_started_at = time.monotonic()
        self.attempt_movements = 0
        self.selected_floor = None
        self.destination_page = 0
        self.destination_page_rects.clear()
        self.destination_rects.clear()
        self.message = f"Fase ativa: {level.name}."
        if challenge_type == "economic":
            self.message += (
                f" Custo minimo: {self.economic_game.optimal_cost:g}."
            )
        elif challenge_type == "final":
            self.message += " Alcance a saida e retorne ao inicio."

    def _continue_after_result(self) -> None:
        recommended = self.progress_manager.recommended_level
        if recommended is None:
            self._discard_active_phase()
            self.menu.show_level_select()
            self.message = (
                "Todo o conteudo disponivel foi concluido. "
                "Escolha uma fase para rejogar."
            )
            return
        self._start_phase(recommended)

    def _discard_active_phase(self) -> None:
        self.score_manager.cancel_attempt(self.attempt_id)
        self.level = None
        self.active_state = None
        self.game = None
        self.hamilton_challenge = None
        self.hamilton_game = None
        self.economic_challenge = None
        self.economic_game = None
        self.euler_challenge = None
        self.euler_game = None
        self.final_challenge = None
        self.final_game = None
        self.active_phase = None
        self.active_level_id = None
        self.hint_open = False
        self.item_progress = None
        self.attempt_result = None
        self.selected_floor = None
        self.destination_page = 0
        self.destination_page_rects.clear()
        self.destination_rects.clear()

    def _return_to_main_menu(self) -> None:
        self._discard_active_phase()
        self.menu.show_main_menu()

    def _return_to_level_select(self) -> None:
        self._discard_active_phase()
        self.menu.show_level_select()

    def _refresh_levels(self, exported_path: Path) -> None:
        if exported_path.parent.resolve() != self.levels_dir.resolve():
            return
        discovery = LevelManager.discover_levels(self.levels_dir)
        levels = discovery.levels
        self.phase_levels = levels
        self.phase_diagnostics = discovery.diagnostics
        self.levels_by_id = {level.identifier: level for level in levels}
        self.levels_by_number = {level.number: level for level in levels}
        self.save_manager.level_numbers = {
            level.identifier: level.number for level in levels
        }
        self.save_manager.number_ids = {
            level.number: level.identifier for level in levels
        }
        level_ids = tuple(level.identifier for level in levels)
        self.progress_manager.update_levels(level_ids)
        scores = self.saved_progress.setdefault("level_scores", {})
        for identifier in level_ids:
            scores.setdefault(identifier, 0)
        self.saved_progress.update(self.progress_manager.to_dict())
        self.level_select_offset = min(
            self.level_select_offset, max(0, len(levels) - 6)
        )

    def _scroll_level_select(self, amount: int) -> None:
        self.level_select_offset = min(
            max(0, self.level_select_offset + amount),
            max(0, len(self.phase_levels) - 6),
        )

    def _level_select_scroll_metrics(self) -> tuple[pygame.Rect, pygame.Rect]:
        track = pygame.Rect(822, 150, 24, 378)
        total = len(self.phase_levels)
        if total <= 6:
            return track, pygame.Rect(track.x, track.y, track.width, track.height)
        thumb_height = min(
            track.height,
            max(36, round(track.height * 6 / total)),
        )
        max_offset = total - 6
        thumb_top = track.top + round(
            (track.height - thumb_height)
            * min(max(self.level_select_offset, 0), max_offset)
            / max_offset
        )
        return track, pygame.Rect(track.x, thumb_top, track.width, thumb_height)

    def _drag_level_select_thumb(self, mouse_y: int) -> None:
        track, thumb = self._level_select_scroll_metrics()
        max_offset = max(0, len(self.phase_levels) - 6)
        available = track.height - thumb.height
        if max_offset == 0 or available <= 0:
            self.level_select_offset = 0
            return
        thumb_top = min(
            max(mouse_y - self.level_select_drag_offset, track.top),
            track.bottom - thumb.height,
        )
        self.level_select_offset = round(
            (thumb_top - track.top) * max_offset / available
        )

    def _replay_result(self) -> None:
        if self.menu.result_level is not None:
            self._start_phase(self.menu.result_level)

    def _request_quit(self) -> None:
        self.quit_confirmation_open = True

    def _handle_quit_confirmation(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_n):
                self.quit_confirmation_open = False
            elif event.key in (pygame.K_RETURN, pygame.K_y):
                self._exit_game()
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.quit_confirm_rect.collidepoint(event.pos):
                self._exit_game()
            if self.quit_cancel_rect.collidepoint(event.pos):
                self.quit_confirmation_open = False

    def _exit_game(self) -> None:
        self.quit_confirmation_open = False
        pygame.quit()
        sys.exit()

    def _current_objectives(self) -> tuple[OptionalObjective, ...]:
        if self.level is None or self.active_state is None:
            return ()
        level = self.level
        if level.challenge_type == "collect_and_exit":
            visited_floors = self.game.visited_floors
            collected_bonus = self.game.collected_bonus
            returned_to_start = self.game.returned_to_start
        else:
            visited_floors = self.item_progress.visited_floors
            collected_bonus = self.item_progress.collected_bonus
            returned_to_start = self.item_progress.returned_to_start
        return tuple(
            objective
            for objective in level.optional_objectives
            if (
                objective.kind == "visit_floor"
                and objective.floor in visited_floors
            )
            or (
                objective.kind == "collect_all_bonus"
                and {
                    item.identifier
                    for item in level.items
                    if item.kind is ItemKind.BONUS
                }.issubset(collected_bonus)
            )
            or (
                objective.kind == "return_to_start"
                and returned_to_start
            )
        )

    def _sync_objective_score(self) -> None:
        self.score_manager.record_objectives(
            self.attempt_id, self._current_objectives()
        )

    def _complete_phase(self) -> None:
        if self.attempt_result is not None or self.level is None:
            return
        level = self.level
        if level.challenge_type == "collect_and_exit":
            collected_ids = self.game.collected_required | self.game.collected_bonus
        else:
            collected_ids = self.item_progress.collected_item_ids
        collected_items = tuple(
            item for item in level.items if item.identifier in collected_ids
        )
        completed_objectives = self._current_objectives()
        self.score_manager.record_items(self.attempt_id, collected_items)
        self.score_manager.record_objectives(
            self.attempt_id, completed_objectives
        )
        challenge_ids = level.required_challenges or (
            ChallengeRegistry.completion_id(level.challenge_type),
        )
        self.attempt_result = self.score_manager.finalize_attempt(
            self.attempt_id,
            level.number,
            items=collected_items,
            objectives=completed_objectives,
            completed_challenges=challenge_ids,
            movements=self.attempt_movements,
            elapsed_seconds=time.monotonic() - self.attempt_started_at,
            completion_score=level.completion_score,
        )
        self.progress_manager.complete_level(level.identifier)
        persisted = self.progress_manager.to_dict()
        self.saved_progress.update(persisted)
        try:
            self.saved_progress = self.save_manager.record_result(
                self.saved_progress,
                level.identifier,
                self.attempt_result.to_dict(),
            )
        except SaveError as error:
            self.message = f"Fase concluida, mas o progresso nao foi salvo: {error}"
        self.menu.show_result(level.identifier)

    def _select_floor(self, floor: int) -> None:
        if self.level is None or self.active_state is None:
            return
        challenge_type = self.level.challenge_type
        missing_keys = self._missing_connection_keys(floor)
        if missing_keys:
            self.selected_floor = None
            self.message = f"Elevador bloqueado. Falta a chave: {', '.join(missing_keys)}."
            return
        if challenge_type == "collect_and_exit":
            if self.game.is_complete:
                return
            if self.level.graph.has_edge(self.current_floor, floor):
                self.selected_floor = floor
                self.message = f"Destino selecionado: andar {floor:02d}."
            else:
                self.selected_floor = None
                self.message = f"Nao ha elevador do andar {self.current_floor:02d} para {floor:02d}."
            return

        if challenge_type == "economic":
            if self.economic_game.is_finished:
                self.selected_floor = None
                self.message = (
                    "Tentativa encerrada. Pressione R para reiniciar."
                    if not self.economic_game.is_complete
                    else "Desafio concluido. Pressione R para tentar novamente."
                )
            elif not self.economic_challenge.graph.has_edge(
                self.current_floor, floor
            ):
                self.selected_floor = None
                self.message = (
                    f"Nao ha conexao entre os andares {self.current_floor:02d} "
                    f"e {floor:02d}."
                )
            else:
                self.selected_floor = floor
                edge_cost = self.economic_challenge.graph.weight(
                    self.current_floor, floor
                )
                self.message = (
                    f"Destino selecionado: andar {floor:02d} "
                    f"(custo {edge_cost:g})."
                )
            return

        if challenge_type == "euler":
            edge = (
                (self.current_floor, floor)
                if self.current_floor < floor
                else (floor, self.current_floor)
            )
            if not self.euler_challenge.graph.has_edge(self.current_floor, floor):
                self.selected_floor = None
                self.message = (
                    f"Nao ha conexao entre os andares {self.current_floor:02d} "
                    f"e {floor:02d}."
                )
            elif edge in self.euler_game.used_edges:
                self.selected_floor = None
                self.message = (
                    f"A conexao {edge[0]:02d}-{edge[1]:02d} ja foi percorrida."
                )
            elif self.euler_game.is_complete:
                self.selected_floor = None
                self.message = "Inspecao concluida. Pressione R para reiniciar."
            else:
                self.selected_floor = floor
                self.message = f"Conexao {edge[0]:02d}-{edge[1]:02d} selecionada."
            return

        if challenge_type == "final":
            if self.final_game.is_finished:
                self.selected_floor = None
                self.message = (
                    "Tentativa encerrada. Pressione R para reiniciar."
                    if not self.final_game.is_complete
                    else "Desafio concluido. Pressione R para tentar novamente."
                )
            elif not self.final_challenge.graph.has_edge(
                self.current_floor, floor
            ):
                self.selected_floor = None
                self.message = (
                    f"Nao ha conexao entre os andares {self.current_floor:02d} "
                    f"e {floor:02d}."
                )
            else:
                self.selected_floor = floor
                edge_cost = self.final_challenge.graph.weight(
                    self.current_floor, floor
                )
                self.message = (
                    f"Destino selecionado: andar {floor:02d} "
                    f"(custo {edge_cost:g})."
                )
            return

        if challenge_type == "hamilton":
            if not self.hamilton_challenge.graph.has_edge(self.current_floor, floor):
                self.selected_floor = None
                self.message = (
                    f"Nao ha conexao entre os andares {self.current_floor:02d} "
                    f"e {floor:02d}."
                )
            elif self.hamilton_game.is_complete:
                self.selected_floor = None
                self.message = "Desafio concluido. Pressione R para tentar novamente."
            elif floor in self.hamilton_game.visited_floors:
                self.selected_floor = None
                self.message = (
                    f"Andar {floor:02d} ja visitado. Nao e permitido voltar."
                )
            elif (
                floor == self.hamilton_challenge.end_floor
                and len(self.hamilton_game.visited_sequence)
                != len(self.hamilton_challenge.graph.vertices) - 1
            ):
                self.selected_floor = None
                self.message = (
                    f"O andar final {floor:02d} so pode ser visitado "
                    "depois dos demais."
                )
            else:
                self.selected_floor = floor
                self.message = f"Destino selecionado: andar {floor:02d}."
            return

        if self.active_state.is_complete:
            self.selected_floor = None
            self.message = "Desafio concluido. Pressione R para reiniciar."
        elif not self.active_graph.has_edge(self.current_floor, floor):
            self.selected_floor = None
            self.message = (
                f"Nao ha conexao entre os andares {self.current_floor:02d} "
                f"e {floor:02d}."
            )
        else:
            self.selected_floor = floor
            self.message = f"Destino selecionado: andar {floor:02d}."

    def _cycle_destination(self, reverse: bool = False) -> None:
        if self.level is None or self.active_state is None:
            return
        challenge_type = self.level.challenge_type
        if challenge_type in ("hamilton", "euler"):
            candidates = list(self.active_state.valid_destinations)
        elif (
            challenge_type == "economic"
            and self.economic_game.is_finished
            or challenge_type == "final"
            and self.final_game.is_finished
            or challenge_type == "collect_and_exit"
            and self.game.is_complete
        ):
            candidates = []
        else:
            candidates = [
                floor
                for floor, _ in self.active_graph.neighbors(self.current_floor)
            ]
        candidates = [
            floor
            for floor in candidates
            if not self._missing_connection_keys(floor)
        ]
        if not candidates:
            self.selected_floor = None
            self.message = "Nao ha destinos disponiveis para selecionar."
            return

        if self.selected_floor in candidates:
            offset = candidates.index(self.selected_floor)
            index = (offset + (-1 if reverse else 1)) % len(candidates)
        else:
            index = len(candidates) - 1 if reverse else 0
        destination = candidates[index]
        all_neighbors = [
            floor
            for floor, _ in self.active_graph.neighbors(self.current_floor)
        ]
        self.destination_page = all_neighbors.index(destination) // self.destination_page_size
        self._select_floor(destination)

    def _travel(self) -> None:
        if self.selected_floor is None or self.active_state is None or self.level is None:
            self.message = "Selecione primeiro um dos destinos disponiveis."
            return
        missing_keys = self._missing_connection_keys(self.selected_floor)
        if missing_keys:
            self.selected_floor = None
            self.message = f"Elevador bloqueado. Falta a chave: {', '.join(missing_keys)}."
            return
        previous_move_count = self._successful_move_count()
        self.message = self.active_state.move_to(self.selected_floor)
        self.selected_floor = None
        current_move_count = self._successful_move_count()
        if current_move_count > previous_move_count:
            self.destination_page = 0
            self.attempt_movements += 1
            if self.level.challenge_type != "collect_and_exit":
                self.item_progress.record_movement(self.current_floor)
            self._sync_objective_score()
            discovered = (
                self.game.items_on_current_floor
                if self.level.challenge_type == "collect_and_exit"
                else self.item_progress.items_on_floor(self.current_floor)
            )
            if discovered:
                names = ", ".join(item.name for item in discovered)
                self.message += f" Item encontrado: {names}. Pressione E para coletar."
        if self.active_state.is_complete:
            self._complete_phase()

    def _successful_move_count(self) -> int:
        if self.level is not None and self.level.challenge_type == "collect_and_exit":
            return self.game.movement_count
        if self.active_state is None:
            return 0
        return len(self.active_state.visited_sequence) - 1

    def _missing_connection_keys(self, destination: int) -> tuple[str, ...]:
        if self.level is None:
            return ()
        level = self.level
        collected_keys = (
            self.game.collected_keys
            if self.level.challenge_type == "collect_and_exit"
            else self.item_progress.collected_keys
        )
        required_ids = {
            key_id
            for requirement in level.connection_requirements
            if {requirement.first_floor, requirement.second_floor}
            == {self.current_floor, destination}
            for key_id in requirement.key_ids
        }
        return tuple(
            item.name
            for item in level.items
            if item.identifier in required_ids
            and item.identifier not in collected_keys
        )

    def _collect_items(self) -> None:
        if (
            self.menu.screen is not Screen.GAME
            or self.level is None
            or self.item_progress is None
        ):
            return
        if self.level.challenge_type == "collect_and_exit":
            items = self.game.collect_items_here()
        else:
            items = self.item_progress.collect(self.current_floor)
        if not items:
            self.message = "Nao ha itens para coletar neste andar."
            return
        self.score_manager.record_items(self.attempt_id, items)
        self._sync_objective_score()
        names = ", ".join(item.name for item in items)
        if any(item.is_key for item in items):
            self.message = f"Chave coletada: {names}."
        elif all(item.kind is ItemKind.REQUIRED for item in items):
            self.message = f"Item obrigatorio coletado: {names}."
        elif all(item.kind is ItemKind.BONUS for item in items):
            self.message = f"Bonus coletado: {names}."
        else:
            self.message = f"Itens coletados: {names}."

    def _switch_phase(self, phase: int) -> None:
        self._start_phase(phase)

    def _reset_attempt_tracking(self) -> None:
        if self.level is None:
            return
        self.item_progress = ItemProgress(self.level)
        self.attempt_id = str(uuid4())
        self.score_manager.begin_attempt(self.attempt_id)
        self.attempt_started_at = time.monotonic()
        self.attempt_movements = 0
        self.attempt_result = None
        self.selected_floor = None

    def _restart_active_attempt(self) -> None:
        if self.active_state is None:
            return
        self.active_state.reset()
        self._reset_attempt_tracking()
        self.message = "Tentativa reiniciada no andar inicial."

    def _draw(self) -> None:
        main_menu = self.menu.screen is Screen.MAIN_MENU
        self.screen.fill((0, 0, 0, 0) if main_menu else BACKGROUND)
        self.window.fill(BACKGROUND)
        if main_menu:
            self._draw_menu_background()
        if self.menu.screen is Screen.MAIN_MENU:
            self._draw_main_menu()
        elif self.menu.screen is Screen.LEVEL_SELECT:
            self._draw_level_select()
        elif self.menu.screen is Screen.RESULT:
            self._draw_result()
        elif self.menu.screen is Screen.LEVEL_EDITOR:
            self.level_editor.draw(self.screen)
        else:
            self._draw_header()
            self._draw_floor_panel()
            self._draw_destination_panel()
            self._draw_footer()
            if self.hint_open:
                self._draw_graph_hint()
        if self.quit_confirmation_open:
            self._draw_quit_confirmation()
        viewport, _ = self._content_viewport()
        self.window.blit(
            pygame.transform.smoothscale(self.screen, viewport.size),
            viewport.topleft,
        )
        pygame.display.flip()

    def _draw_quit_confirmation(self) -> None:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 185))
        self.screen.blit(overlay, (0, 0))
        dialog = pygame.Rect(220, 230, 520, 200)
        pygame.draw.rect(self.screen, PANEL, dialog, border_radius=12)
        pygame.draw.rect(self.screen, ACCENT, dialog, width=2, border_radius=12)
        prompt = self.body_font.render(
            "Tem certeza de que deseja sair do Floor 13?", True, TEXT
        )
        self.screen.blit(prompt, prompt.get_rect(center=(dialog.centerx, 285)))
        for rect, label in (
            (self.quit_confirm_rect, "SIM, SAIR"),
            (self.quit_cancel_rect, "CANCELAR"),
        ):
            pygame.draw.rect(self.screen, PANEL_LIGHT, rect, border_radius=8)
            pygame.draw.rect(self.screen, ACCENT_DARK, rect, width=2, border_radius=8)
            text = self.small_font.render(label, True, TEXT)
            self.screen.blit(text, text.get_rect(center=rect.center))

    def _draw_main_menu(self) -> None:
        title = self.menu_title_font.render("FLOOR 13", True, TEXT)
        subtitle = self.body_font.render(
            "Explore os andares. Descubra a saida.", True, MUTED
        )
        self.screen.blit(title, (64, 82))
        self.screen.blit(subtitle, (68, 160))
        labels = (
            (
                self.main_continue_rect,
                "JOGAR NOVAMENTE"
                if self.progress_manager.all_levels_complete
                else (
                    "CONTINUAR"
                    if self.progress_manager.completed_levels
                    else "JOGAR"
                ),
            ),
            (self.main_select_rect, "SELECIONAR FASES"),
            (self.main_editor_rect, "EDITOR DE FASES"),
            (self.main_exit_rect, "SAIR"),
        )
        for rect, label in labels:
            pygame.draw.rect(self.screen, PANEL, rect, border_radius=12)
            pygame.draw.rect(self.screen, ACCENT_DARK, rect, width=2, border_radius=12)
            text = self.body_font.render(label, True, TEXT)
            self.screen.blit(text, text.get_rect(center=rect.center))
        self._text(
            f"Pontuacao acumulada: {self.saved_progress['total_score']}",
            self.small_font,
            ACCENT,
            (68, 548),
        )

    def _draw_menu_background(self) -> None:
        if self.menu_background is None:
            return
        window_size = self.window.get_size()
        scaled_background = self._scaled_menu_background
        if (
            scaled_background is None
            or self._scaled_menu_background_size != window_size
        ):
            scaled_background = self._cover_image(self.menu_background, window_size)
            self._scaled_menu_background = scaled_background
            self._scaled_menu_background_size = window_size
        overlay = self._menu_background_overlay
        if (
            overlay is None
            or self._menu_background_overlay_size != window_size
        ):
            overlay = pygame.Surface(window_size, pygame.SRCALPHA)
            overlay.fill((8, 11, 18, 145))
            self._menu_background_overlay = overlay
            self._menu_background_overlay_size = window_size
        self.window.blit(scaled_background, (0, 0))
        self.window.blit(overlay, (0, 0))

    @staticmethod
    def _cover_image(
        image: pygame.Surface, target_size: tuple[int, int]
    ) -> pygame.Surface:
        target_width, target_height = target_size
        scale = max(
            target_width / image.get_width(),
            target_height / image.get_height(),
        )
        scaled_size = (
            max(target_width, round(image.get_width() * scale)),
            max(target_height, round(image.get_height() * scale)),
        )
        scaled = pygame.transform.smoothscale(image, scaled_size)
        crop = pygame.Rect(
            (scaled_size[0] - target_width) // 2,
            (scaled_size[1] - target_height) // 2,
            target_width,
            target_height,
        )
        return scaled.subsurface(crop).copy()

    def _draw_level_select(self) -> None:
        self._text("SELECIONE UMA FASE", self.title_font, TEXT, (64, 54))
        total = len(self.phase_levels)
        range_label = self._level_select_range_label()
        self._text(
            range_label,
            self.small_font,
            ACCENT if total > 6 else MUTED,
            (66, 104),
        )
        self.level_rects.clear()
        visible_levels = self.phase_levels[
            self.level_select_offset : self.level_select_offset + 6
        ]
        if not visible_levels:
            self._text(
                "Nenhuma fase valida foi encontrada em levels/.",
                self.body_font,
                WARNING,
                (66, 170),
            )
        for index, level in enumerate(visible_levels):
            rect = pygame.Rect(150, 150 + index * 63, 660, 54)
            self.level_rects[level.identifier] = rect
            unlocked = self.progress_manager.can_start(level.identifier)
            completed = level.identifier in self.progress_manager.completed_levels
            background = (
                ACCENT_DARK if completed else PANEL_LIGHT if unlocked else (39, 43, 55)
            )
            border = ACCENT if unlocked else (70, 75, 88)
            pygame.draw.rect(self.screen, background, rect, border_radius=11)
            pygame.draw.rect(self.screen, border, rect, width=2, border_radius=11)
            status = (
                f"CONCLUIDA  •  MELHOR {self.saved_progress['level_scores'].get(level.identifier, 0)}"
                if completed
                else "DESBLOQUEADA"
                if unlocked
                else "BLOQUEADA"
            )
            self._text(
                f"{level.number}. {level.name}",
                self.body_font,
                TEXT if unlocked else MUTED,
                (rect.x + 18, rect.y + 8),
            )
            self._text(
                status,
                self.small_font,
                ACCENT if completed or unlocked else MUTED,
                (rect.x + 18, rect.y + 36),
            )
        if total > 6:
            track, thumb = self._level_select_scroll_metrics()
            visible_track = pygame.Rect(track.centerx - 4, track.y, 8, track.height)
            visible_thumb = pygame.Rect(
                thumb.centerx - 4, thumb.y, 8, thumb.height
            )
            pygame.draw.rect(self.screen, PANEL_LIGHT, visible_track, border_radius=4)
            pygame.draw.rect(self.screen, ACCENT, visible_thumb, border_radius=4)
        if self.phase_diagnostics:
            error_count = sum(
                diagnostic.severity == "error"
                for diagnostic in self.phase_diagnostics
            )
            warning_count = len(self.phase_diagnostics) - error_count
            first_error = next(
                (
                    diagnostic
                    for diagnostic in self.phase_diagnostics
                    if diagnostic.severity == "error"
                ),
                self.phase_diagnostics[0],
            )
            self._text(
                f"{error_count} erro(s), {warning_count} aviso(s): "
                f"{first_error.path.name}: {first_error.message[:68]}",
                self.small_font,
                WARNING,
                (270, 575),
            )
        pygame.draw.rect(
            self.screen, PANEL, self.level_back_rect, border_radius=10
        )
        self._text("VOLTAR", self.body_font, TEXT, (self.level_back_rect.x + 48, 582))

    def _level_select_range_label(self) -> str:
        total = len(self.phase_levels)
        first = self.level_select_offset + 1 if total else 0
        last = min(self.level_select_offset + 6, total)
        label = f"Fases {first}-{last} de {total}"
        if total > 6:
            label += "  |  Role para baixo para ver mais fases"
        return label

    def _draw_result(self) -> None:
        level_id = self.menu.result_level
        if level_id is None or self.attempt_result is None:
            self.menu.show_main_menu()
            return
        level = self.levels_by_id.get(level_id)
        if level is None:
            self.menu.show_main_menu()
            return
        result = self.attempt_result
        self._text("FASE CONCLUIDA", self.title_font, ACCENT, (64, 48))
        self._text(level.name, self.heading_font, TEXT, (66, 100))
        self._text(f"Pontuacao obtida: {result.score}", self.body_font, TEXT, (66, 150))
        names = {item.identifier: item.name for item in level.items}
        essential_names = ", ".join(
            names.get(item_id, item_id) for item_id in result.essential_items
        ) or "Nenhum"
        bonus_names = ", ".join(
            names.get(item_id, item_id) for item_id in result.bonus_items
        ) or "Nenhum"
        self._text(
            f"Itens essenciais: {essential_names}",
            self.small_font,
            ACCENT,
            (66, 194),
        )
        self._text(
            f"Itens bonus: {bonus_names}",
            self.small_font,
            WARNING,
            (66, 224),
        )
        challenge_labels = {
            "collect_and_exit": "Coleta e saida",
            "hamilton": "Caminho hamiltoniano",
            "economic_optimal_route": "Rota de custo minimo",
            "euler_trail": "Percurso de Euler",
            "minimum_round_trip": "Ida e retorno pelo menor custo",
        }
        challenges = ", ".join(
            challenge_labels.get(challenge, challenge)
            for challenge in result.completed_challenges
        )
        objectives = ", ".join(
            objective.name
            for objective in level.optional_objectives
            if objective.identifier in result.completed_objectives
        ) or "Nenhum"
        self._text(
            f"Desafios cumpridos: {challenges}",
            self.small_font,
            TEXT,
            (66, 264),
        )
        self._text(
            f"Objetivos opcionais: {objectives}",
            self.small_font,
            TEXT,
            (66, 294),
        )
        elapsed = (
            f"{result.elapsed_seconds:.1f} s"
            if result.elapsed_seconds is not None
            else "Indisponivel"
        )
        self._text(
            f"Deslocamentos: {result.movements}    Tempo: {elapsed}",
            self.small_font,
            MUTED,
            (66, 330),
        )
        recommended = self.progress_manager.recommended_level
        if recommended is not None:
            next_level = self.levels_by_id[recommended]
            next_text = (
                f"Proxima fase desbloqueada: {next_level.number}. "
                f"{next_level.name}"
            )
        else:
            next_text = "Todo o conteudo disponivel foi finalizado."
        self._text(next_text, self.body_font, ACCENT, (66, 386))

        buttons = [(self.result_replay_rect, "JOGAR NOVAMENTE")]
        if recommended is not None:
            buttons.append((self.result_continue_rect, "PROXIMA FASE"))
        buttons.extend(
            (
                (self.result_select_rect, "SELECIONAR FASES"),
                (self.result_menu_rect, "MENU PRINCIPAL"),
            )
        )
        for rect, label in buttons:
            pygame.draw.rect(self.screen, PANEL, rect, border_radius=10)
            pygame.draw.rect(self.screen, ACCENT_DARK, rect, width=2, border_radius=10)
            text = self.small_font.render(label, True, TEXT)
            self.screen.blit(text, text.get_rect(center=rect.center))

    def _draw_header(self) -> None:
        if self.level is None:
            return
        if self.level is None:
            return
        self._text("FLOOR 13", self.title_font, TEXT, (64, 48))
        phase_label = f"FASE {self.level.number} • {self.level.name.upper()}"
        self._text(phase_label, self.small_font, ACCENT, (66, 91))
        pygame.draw.rect(self.screen, PANEL, self.game_menu_rect, border_radius=8)
        pygame.draw.rect(
            self.screen, ACCENT_DARK, self.game_menu_rect, width=2, border_radius=8
        )
        menu_label = self.small_font.render("MENU", True, TEXT)
        self.screen.blit(menu_label, menu_label.get_rect(center=self.game_menu_rect.center))
        pygame.draw.rect(self.screen, PANEL, self.hint_rect, border_radius=8)
        pygame.draw.rect(
            self.screen, ACCENT_DARK, self.hint_rect, width=2, border_radius=8
        )
        bulb_center = (self.hint_rect.x + 19, self.hint_rect.centery - 2)
        pygame.draw.circle(self.screen, WARNING, bulb_center, 7, width=2)
        pygame.draw.line(
            self.screen,
            WARNING,
            (bulb_center[0] - 3, bulb_center[1] + 7),
            (bulb_center[0] + 3, bulb_center[1] + 7),
            2,
        )
        pygame.draw.line(
            self.screen,
            WARNING,
            (bulb_center[0] - 2, bulb_center[1] + 10),
            (bulb_center[0] + 2, bulb_center[1] + 10),
            2,
        )
        hint_label = self.small_font.render("Dica", True, TEXT)
        self.screen.blit(
            hint_label,
            hint_label.get_rect(midleft=(self.hint_rect.x + 34, self.hint_rect.centery)),
        )
        pygame.draw.line(self.screen, PANEL_LIGHT, (64, 126), (896, 126), 2)

    def _draw_graph_hint(self) -> None:
        if self.level is None:
            return
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 190))
        self.screen.blit(overlay, (0, 0))

        dialog = pygame.Rect(75, 65, 810, 510)
        pygame.draw.rect(self.screen, PANEL, dialog, border_radius=18)
        pygame.draw.rect(self.screen, ACCENT, dialog, width=2, border_radius=18)
        self._text("DICA — GRAFO DA FASE", self.heading_font, TEXT, (110, 88))
        self._text(
            f"{len(self.active_graph.vertices)} vertices  •  "
            f"{self.active_graph.edge_count} arestas",
            self.small_font,
            MUTED,
            (112, 121),
        )

        graph_area = pygame.Rect(130, 155, 700, 320)
        vertices = self.active_graph.vertices
        positions: dict[int, tuple[int, int]] = {}
        count = len(vertices)
        if count == 1:
            positions[vertices[0]] = graph_area.center
        else:
            radius_x = graph_area.width * 0.43
            radius_y = graph_area.height * 0.40
            for index, vertex in enumerate(vertices):
                angle = -pi / 2 + 2 * pi * index / count
                positions[vertex] = (
                    round(graph_area.centerx + radius_x * cos(angle)),
                    round(graph_area.centery + radius_y * sin(angle)),
                )

        vertex_indexes = {vertex: index for index, vertex in enumerate(vertices)}
        node_radius = max(
            3,
            min(23, round(min(graph_area.width, graph_area.height) * 0.40 / count)),
        )
        label_font = pygame.font.Font(
            None, max(12, min(22, round(node_radius * 1.35)))
        )
        weight_font = pygame.font.Font(None, 18)
        for first in vertices:
            for second, weight in self.active_graph.neighbors(first):
                if vertex_indexes[first] > vertex_indexes[second]:
                    continue
                start = positions[first]
                end = positions[second]
                if first == second:
                    loop = pygame.Rect(
                        start[0] - node_radius,
                        start[1] - node_radius * 2,
                        node_radius * 2,
                        node_radius * 2,
                    )
                    pygame.draw.arc(self.screen, MUTED, loop, 0, 2 * pi, 2)
                    label_position = (start[0], start[1] - node_radius * 2 - 8)
                else:
                    pygame.draw.line(self.screen, MUTED, start, end, 2)
                    midpoint = ((start[0] + end[0]) // 2, (start[1] + end[1]) // 2)
                    dx = end[0] - start[0]
                    dy = end[1] - start[1]
                    length = max(1, (dx * dx + dy * dy) ** 0.5)
                    label_position = (
                        round(midpoint[0] - dy / length * 10),
                        round(midpoint[1] + dx / length * 10),
                    )
                weight_label = weight_font.render(f"{weight:g}", True, WARNING)
                weight_rect = weight_label.get_rect(center=label_position)
                pygame.draw.rect(
                    self.screen, PANEL, weight_rect.inflate(6, 4), border_radius=4
                )
                self.screen.blit(weight_label, weight_rect)

        for vertex in vertices:
            position = positions[vertex]
            pygame.draw.circle(self.screen, ACCENT_DARK, position, node_radius)
            pygame.draw.circle(self.screen, ACCENT, position, node_radius, width=2)
            vertex_label = label_font.render(str(vertex), True, TEXT)
            self.screen.blit(vertex_label, vertex_label.get_rect(center=position))

        pygame.draw.rect(
            self.screen, PANEL_LIGHT, self.hint_close_rect, border_radius=9
        )
        pygame.draw.rect(
            self.screen, ACCENT_DARK, self.hint_close_rect, width=2, border_radius=9
        )
        close_label = self.body_font.render("Fechar", True, TEXT)
        self.screen.blit(
            close_label, close_label.get_rect(center=self.hint_close_rect.center)
        )

    def _draw_floor_panel(self) -> None:
        if self.level is None:
            return
        rect = pygame.Rect(64, 145, 480, 439)
        pygame.draw.rect(self.screen, PANEL, rect, border_radius=18)
        pygame.draw.rect(self.screen, PANEL_LIGHT, rect, width=1, border_radius=18)
        self._text("ANDAR ATUAL", self.small_font, MUTED, (94, 171))

        floor_card = pygame.Rect(94, 204, 420, 154)
        pygame.draw.rect(self.screen, (25, 30, 43), floor_card, border_radius=16)
        pygame.draw.rect(self.screen, ACCENT_DARK, floor_card, width=2, border_radius=16)
        self._text(
            f"{self.current_floor:02d}",
            self.floor_font,
            TEXT,
            (124, 225),
        )
        self._text("PAVIMENTO", self.small_font, MUTED, (130, 315))
        self._draw_elevator_icon(390, 215)
        self._text("ELEVADOR", self.small_font, ACCENT, (369, 334))

        if self.level.challenge_type == "collect_and_exit":
            self._draw_item_progress()
        elif self.level.challenge_type == "hamilton":
            self._draw_hamilton_progress()
        elif self.level.challenge_type == "economic":
            self._draw_economic_progress()
        elif self.level.challenge_type == "euler":
            self._draw_euler_progress()
        elif self.level.challenge_type == "final":
            self._draw_final_progress()
        else:
            self._draw_custom_progress()

    def _draw_custom_progress(self) -> None:
        if self.level is None or self.item_progress is None:
            return
        self._text(
            f"DESAFIO: {self.level.challenge_type}",
            self.small_font,
            MUTED,
            (94, 378),
        )
        self._text(
            f"Andares visitados: {len(self.item_progress.visited_floors)}"
            f"/{len(self.level.graph.vertices)}",
            self.small_font,
            ACCENT,
            (94, 410),
        )
        visited = "  ".join(
            f"{floor:02d}"
            if floor in self.item_progress.visited_floors
            else "??"
            for floor in self.level.graph.vertices
        )
        self._text(visited, self.small_font, TEXT, (94, 442))

    def _draw_item_progress(self) -> None:
        if self.level is None or self.game is None:
            return
        self._text("ITENS NESTE ANDAR", self.small_font, MUTED, (94, 378))
        current_items = self.game.items_on_current_floor
        if current_items:
            for index, item in enumerate(current_items[:3]):
                color = ACCENT if item.kind is ItemKind.REQUIRED else WARNING
                self._text(
                    f"{item.kind.value}: {item.name}",
                    self.small_font,
                    color,
                    (94, 402 + index * 21),
                )
        elif self.game.all_items_on_current_floor:
            self._text(
                "Itens deste andar ja coletados.",
                self.small_font,
                MUTED,
                (94, 404),
            )
        else:
            self._text(
                "Este andar nao possui itens.",
                self.small_font,
                MUTED,
                (94, 404),
            )

        required_count = sum(
            item.kind is ItemKind.REQUIRED for item in self.level.items
        )
        bonus_count = sum(item.kind is ItemKind.BONUS for item in self.level.items)
        self._text(
            f"Obrigatorios: {len(self.game.collected_required)}/{required_count}"
            f"   Bonus: {len(self.game.collected_bonus)}/{bonus_count}",
            self.small_font,
            TEXT,
            (94, 488),
        )
        visited = "  ".join(
            f"{floor:02d}" if floor in self.game.visited_floors else "??"
            for floor in self.level.graph.vertices
        )
        self._text("Exploracao:", self.small_font, MUTED, (94, 518))
        self._text(visited, self.small_font, ACCENT, (190, 518))

    def _draw_hamilton_progress(self) -> None:
        route = " > ".join(
            f"{floor:02d}" for floor in self.hamilton_game.visited_sequence
        )
        self._text("CAMINHO HAMILTONIANO", self.small_font, MUTED, (94, 378))
        self._text(
            f"Visite cada andar uma vez e termine no {self.hamilton_challenge.end_floor:02d}.",
            self.small_font,
            TEXT,
            (94, 404),
        )
        self._text(
            f"Progresso: {len(self.hamilton_game.visited_sequence)}"
            f"/{len(self.hamilton_challenge.graph.vertices)} andares",
            self.small_font,
            ACCENT,
            (94, 435),
        )
        self._text("Rota:", self.small_font, MUTED, (94, 466))
        self._text(route, self.small_font, TEXT, (150, 466))
        if self.hamilton_game.is_complete:
            status = "Todos visitados. Desafio concluido!"
            status_color = ACCENT
        elif self.hamilton_game.is_blocked:
            status = "Sem movimentos. Pressione R para reiniciar."
            status_color = WARNING
        else:
            status = f"Andar final obrigatorio: {self.hamilton_challenge.end_floor:02d}"
            status_color = MUTED
        self._text(status, self.small_font, status_color, (94, 500))

    def _draw_economic_progress(self) -> None:
        route = " > ".join(
            f"{floor:02d}" for floor in self.economic_game.visited_sequence
        )
        self._text("ROTA ECONÔMICA", self.small_font, MUTED, (94, 378))
        self._text(
            f"Destino: andar {self.economic_challenge.destination_floor:02d}",
            self.small_font,
            TEXT,
            (94, 404),
        )
        self._text(
            f"Custo acumulado: {self.economic_game.total_cost:g}",
            self.small_font,
            ACCENT,
            (94, 435),
        )
        self._text(
            f"Custo minimo (Dijkstra): {self.economic_game.optimal_cost:g}",
            self.small_font,
            TEXT,
            (94, 466),
        )
        self._text("Rota:", self.small_font, MUTED, (94, 497))
        self._text(route, self.small_font, TEXT, (150, 497))
        if self.economic_game.is_complete:
            status = "Rota otima! Desafio concluido."
            color = ACCENT
        elif self.economic_game.is_finished:
            status = "Rota mais cara. Pressione R para reiniciar."
            color = WARNING
        else:
            status = "Escolha arestas pelo menor custo total."
            color = MUTED
        self._text(status, self.small_font, color, (94, 528))

    def _draw_euler_progress(self) -> None:
        visited_route = " > ".join(
            f"{floor:02d}" for floor in self.euler_game.visited_sequence
        )
        self._text("INSPEÇÃO DE ARESTAS", self.small_font, MUTED, (94, 378))
        used, total = self.euler_game.progress
        self._text(
            f"Conexoes percorridas: {used} de {total}",
            self.small_font,
            ACCENT,
            (94, 402),
        )
        visited = "  ".join(
            f"{floor:02d}" if floor in self.euler_game.visited_vertices else "--"
            for floor in self.euler_challenge.graph.vertices
        )
        self._text("Andares visitados:", self.small_font, MUTED, (94, 427))
        self._text(visited, self.small_font, TEXT, (230, 427))
        self._text("Percurso:", self.small_font, MUTED, (94, 451))
        self._text(visited_route, self.small_font, TEXT, (165, 451))

        for index, edge in enumerate(self.euler_challenge.required_edges):
            column = index // 6
            row = index % 6
            used_edge = edge in self.euler_game.used_edges
            state = "percorrida" if used_edge else "pendente"
            color = ACCENT if used_edge else MUTED
            self._text(
                f"{edge[0]:02d}-{edge[1]:02d}: {state}",
                self.small_font,
                color,
                (94 + column * 115, 465 + row * 15),
            )

        if self.euler_game.is_complete:
            status = "Todas as conexões inspecionadas!"
            color = ACCENT
        elif self.euler_game.is_blocked:
            status = "Sem conexoes disponiveis. Pressione R para reiniciar."
            color = WARNING
        else:
            status = (
                f"Inicio {self.euler_challenge.start_floor:02d} "
                f"• fim {self.euler_challenge.end_floor:02d}"
            )
            color = MUTED
        self._text(status, self.small_font, color, (94, 560))

    def _draw_final_progress(self) -> None:
        route = " > ".join(
            f"{floor:02d}" for floor in self.final_game.visited_sequence
        )
        if len(route) > 40:
            route = f"... {route[-37:]}"

        self._text("IDA E RETORNO", self.small_font, MUTED, (94, 378))
        self._text(
            f"Saida: {self.final_challenge.destination_floor:02d}  "
            f"Retorno: {self.final_challenge.return_floor:02d}",
            self.small_font,
            TEXT,
            (94, 402),
        )
        stage = "RETORNO" if self.final_game.has_reached_destination else "IDA"
        self._text(
            f"Etapa: {stage}",
            self.small_font,
            ACCENT,
            (94, 428),
        )
        self._text(
            f"Custo ida: {self.final_game.outbound_cost:g}  "
            f"volta: {self.final_game.return_cost:g}",
            self.small_font,
            TEXT,
            (94, 454),
        )
        self._text(
            f"Custo total: {self.final_game.total_cost:g}",
            self.small_font,
            ACCENT,
            (94, 480),
        )
        self._text("Percurso:", self.small_font, MUTED, (94, 506))
        self._text(route, self.small_font, TEXT, (165, 506))

        if self.final_game.is_finished:
            status = (
                f"Minimo ida e volta: "
                f"{self.final_challenge.minimum_total_cost:g}"
            )
            color = ACCENT if self.final_game.is_complete else WARNING
        else:
            status = "Custo minimo de referencia revelado no resultado."
            color = MUTED
        self._text(status, self.small_font, color, (94, 536))

    def _draw_destination_panel(self) -> None:
        if self.level is None or self.item_progress is None:
            return
        challenge_type = self.level.challenge_type
        rect = pygame.Rect(574, 145, 322, 439)
        pygame.draw.rect(self.screen, PANEL, rect, border_radius=18)
        pygame.draw.rect(self.screen, PANEL_LIGHT, rect, width=1, border_radius=18)
        available_items = (
            self.game.items_on_current_floor
            if challenge_type == "collect_and_exit"
            else self.item_progress.items_on_floor(self.current_floor)
        )
        if challenge_type == "collect_and_exit":
            panel_title = "DESTINOS CONECTADOS"
            panel_hint = "Selecione um elevador"
        elif challenge_type == "hamilton":
            panel_title = "PROXIMOS ANDARES"
            panel_hint = "Visitados nao podem ser repetidos"
        elif challenge_type == "economic":
            panel_title = "ELEVADORES E CUSTOS"
            panel_hint = "Peso da aresta nesta conexao"
        elif challenge_type == "final":
            panel_title = "ELEVADORES E CUSTOS"
            panel_hint = "Planeje a ida e o retorno"
        else:
            panel_title = "CONEXOES DISPONIVEIS"
            panel_hint = "Arestas usadas nao podem repetir"
        if available_items:
            panel_hint = f"Item encontrado: {available_items[0].name}"
        self._text(panel_title, self.heading_font, TEXT, (600, 171))
        self._text(panel_hint, self.small_font, MUTED, (600, 201))

        self.destination_rects.clear()
        neighbors = list(self.active_graph.neighbors(self.current_floor))
        page_count = max(
            1,
            (len(neighbors) + self.destination_page_size - 1)
            // self.destination_page_size,
        )
        self.destination_page = min(self.destination_page, page_count - 1)
        first_visible = self.destination_page * self.destination_page_size
        visible_neighbors = neighbors[
            first_visible : first_visible + self.destination_page_size
        ]
        for index, (floor, _) in enumerate(visible_neighbors):
            destination = pygame.Rect(600, 230 + index * 46, 270, 40)
            self.destination_rects[floor] = destination
            selected = floor == self.selected_floor
            visited = (
                challenge_type == "hamilton"
                and floor in self.hamilton_game.visited_floors
            )
            final_too_early = (
                challenge_type == "hamilton"
                and floor == self.hamilton_challenge.end_floor
                and len(self.hamilton_game.visited_sequence)
                != len(self.hamilton_challenge.graph.vertices) - 1
            )
            euler_edge = (
                (self.current_floor, floor)
                if self.current_floor < floor
                else (floor, self.current_floor)
            )
            euler_used = (
                challenge_type == "euler" and euler_edge in self.euler_game.used_edges
            )
            final_finished = (
                challenge_type == "final" and self.final_game.is_finished
            )
            locked_connection = bool(self._missing_connection_keys(floor))
            color = (
                ACCENT_DARK
                if selected
                else (
                    WARNING
                    if (
                        visited
                        or final_too_early
                        or euler_used
                        or final_finished
                        or locked_connection
                    )
                    else PANEL_LIGHT
                )
            )
            pygame.draw.rect(self.screen, color, destination, border_radius=10)
            pygame.draw.rect(
                self.screen,
                ACCENT if selected else (70, 79, 99),
                destination,
                width=2,
                border_radius=10,
            )
            destination_label = f"ANDAR {floor:02d}"
            if locked_connection:
                destination_label += " • BLOQUEADO"
            elif visited:
                destination_label += " • VISITADO"
            elif final_too_early:
                destination_label += " • FINAL"
            elif euler_used:
                destination_label += " • USADA"
            elif final_finished:
                destination_label += " • ENCERRADO"
            self._text(
                (
                    f"{destination_label}  CUSTO "
                    f"{self.active_graph.weight(self.current_floor, floor):g}"
                    if challenge_type in ("economic", "final")
                    else (
                        f"{destination_label}  INSPECIONADA"
                        if challenge_type == "euler" and euler_used
                        else destination_label
                    )
                ),
                self.body_font,
                TEXT,
                (destination.x + 14, destination.y + 8),
            )
            if challenge_type not in ("economic", "euler", "final"):
                self._text(
                    "›",
                    self.heading_font,
                    ACCENT,
                    (destination.right - 32, destination.y + 5),
                )

        self.destination_page_rects.clear()
        if page_count > 1:
            previous_rect = pygame.Rect(600, 414, 130, 24)
            next_rect = pygame.Rect(740, 414, 130, 24)
            self.destination_page_rects = {
                "previous": previous_rect,
                "next": next_rect,
            }
            for name, rect, enabled, label in (
                ("previous", previous_rect, self.destination_page > 0, "< ANTERIORES"),
                ("next", next_rect, self.destination_page < page_count - 1, "PROXIMOS >"),
            ):
                color = PANEL_LIGHT if enabled else PANEL
                pygame.draw.rect(self.screen, color, rect, border_radius=7)
                pygame.draw.rect(
                    self.screen,
                    ACCENT_DARK if enabled else (70, 75, 88),
                    rect,
                    width=1,
                    border_radius=7,
                )
                text = self.small_font.render(label, True, TEXT if enabled else MUTED)
                self.screen.blit(text, text.get_rect(center=rect.center))
            self._text(
                f"{self.destination_page + 1}/{page_count}",
                self.small_font,
                MUTED,
                (716, 417),
            )

        self.collect_rect = pygame.Rect(600, 444, 270, 54)
        pygame.draw.rect(
            self.screen,
            WARNING if available_items else PANEL_LIGHT,
            self.collect_rect,
            border_radius=12,
        )
        self._text(
            f"COLETAR  [E]  ({len(available_items)})",
            self.body_font,
            BACKGROUND,
            (650, 460),
        )

        self.travel_rect = pygame.Rect(600, 510, 270, 58)
        pygame.draw.rect(
            self.screen,
            ACCENT_DARK if self.selected_floor is not None else PANEL_LIGHT,
            self.travel_rect,
            border_radius=12,
        )
        if challenge_type == "collect_and_exit":
            travel_label = "VIAJAR  [ENTER]"
        elif challenge_type == "hamilton":
            travel_label = "MOVER  [ENTER]"
        elif challenge_type == "economic":
            travel_label = "VIAJAR  [ENTER]"
        elif challenge_type == "euler":
            travel_label = "INSPECIONAR  [ENTER]"
        else:
            travel_label = "DESLOCAR  [ENTER]"
        self._text(travel_label, self.body_font, TEXT, (635, 528))

    def _draw_footer(self) -> None:
        self._text(
            f"Pontos da tentativa: {self.score_manager.current_attempt_score}",
            self.small_font,
            ACCENT,
            (735, 570),
        )
        self._text(self.message, self.small_font, WARNING, (66, 599))
        footer = "E coletar • "
        if self.level is not None and self.level.challenge_type != "collect_and_exit":
            footer += "R reiniciar • "
        footer += "Esc sair"
        self._text(footer, self.small_font, MUTED, (735, 599))

    def _draw_elevator_icon(self, x: int, y: int) -> None:
        lift = pygame.Rect(x, y, 92, 116)
        pygame.draw.rect(self.screen, PANEL_LIGHT, lift, border_radius=8)
        pygame.draw.rect(self.screen, ACCENT, lift, width=3, border_radius=8)
        pygame.draw.line(self.screen, ACCENT, (x + 46, y + 7), (x + 46, y + 109), 2)
        pygame.draw.polygon(self.screen, ACCENT, ((x + 25, y + 27), (x + 19, y + 37), (x + 31, y + 37)))
        pygame.draw.polygon(self.screen, ACCENT, ((x + 67, y + 88), (x + 61, y + 78), (x + 73, y + 78)))

    def _text(
        self,
        content: str,
        font: pygame.font.Font,
        color: tuple[int, int, int],
        position: tuple[int, int],
    ) -> None:
        self.screen.blit(font.render(content, True, color), position)


def main() -> None:
    ElevatorPrototype().run()


if __name__ == "__main__":
    main()

"""Interface Pygame das fases implementadas de Floor 13."""

from __future__ import annotations

import sys
import time
from uuid import uuid4

import pygame

from economic_challenge import EconomicChallengeManager
from economic_game_state import EconomicGameState
from euler_challenge import EulerChallengeManager
from euler_game_state import EulerGameState
from final_challenge import FinalChallengeManager
from final_game_state import FinalGameState
from game_state import GameState
from hamilton_challenge import HamiltonChallengeManager
from hamilton_game_state import HamiltonGameState
from graph import Graph
from level import ItemKind, OptionalObjective
from level_manager import LevelManager
from systems.item_manager import ItemProgress
from systems.menu_manager import MenuManager, Screen
from systems.progress_manager import ProgressManager
from systems.save_manager import SaveError, SaveManager
from systems.score_manager import AttemptResult, ScoreManager

WIDTH = 960
HEIGHT = 640
BACKGROUND = (19, 22, 32)
PANEL = (31, 36, 50)
PANEL_LIGHT = (43, 50, 67)
TEXT = (239, 241, 247)
MUTED = (160, 170, 190)
ACCENT = (100, 208, 190)
ACCENT_DARK = (43, 125, 117)
WARNING = (244, 190, 105)


class ElevatorPrototype:
    def __init__(self, save_path: str | None = None) -> None:
        pygame.init()
        self.phase_levels = tuple(
            LevelManager.load_level(f"phase-0{number}")
            for number in range(1, 6)
        )
        self.level = self.phase_levels[0]
        self.game = GameState(self.level)
        self.hamilton_challenge = HamiltonChallengeManager.create_no_turning_back()
        self.hamilton_game = HamiltonGameState(self.hamilton_challenge)
        self.economic_challenge = EconomicChallengeManager.create_economic_elevator()
        self.economic_game = EconomicGameState(self.economic_challenge)
        self.euler_challenge = EulerChallengeManager.create_full_inspection()
        self.euler_game = EulerGameState(self.euler_challenge)
        self.final_challenge = FinalChallengeManager.create_the_exit()
        self.final_game = FinalGameState(self.final_challenge)
        self.active_phase = 1
        self.save_manager = SaveManager(save_path)
        self.saved_progress = self.save_manager.load()
        self.progress_manager = ProgressManager()
        self.progress_manager.restore(self.saved_progress)
        self.score_manager = ScoreManager()
        self.menu = MenuManager()
        self.item_progress = ItemProgress(self.level)
        self.attempt_result: AttemptResult | None = None
        self.attempt_id = str(uuid4())
        self.attempt_started_at = time.monotonic()
        self.attempt_movements = 0
        pygame.display.set_caption("Floor 13")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.title_font = pygame.font.Font(None, 42)
        self.heading_font = pygame.font.Font(None, 29)
        self.body_font = pygame.font.Font(None, 24)
        self.small_font = pygame.font.Font(None, 20)
        self.floor_font = pygame.font.Font(None, 96)
        self.selected_floor: int | None = None
        self.message = "Explore os andares e colete os itens para encontrar a saida."
        self.destination_rects: dict[int, pygame.Rect] = {}
        self.collect_rect = pygame.Rect(600, 444, 270, 54)
        self.travel_rect = pygame.Rect(600, 510, 270, 58)
        self.main_continue_rect = pygame.Rect(330, 260, 300, 58)
        self.main_select_rect = pygame.Rect(330, 335, 300, 58)
        self.main_exit_rect = pygame.Rect(330, 410, 300, 58)
        self.level_rects: dict[int, pygame.Rect] = {}
        self.level_back_rect = pygame.Rect(64, 548, 190, 48)
        self.result_continue_rect = pygame.Rect(110, 520, 230, 54)
        self.result_replay_rect = pygame.Rect(365, 520, 230, 54)
        self.result_select_rect = pygame.Rect(620, 520, 230, 54)

    @property
    def current_floor(self) -> int:
        if self.active_phase == 1:
            return self.game.current_floor
        if self.active_phase == 2:
            return self.hamilton_game.current_floor
        if self.active_phase == 3:
            return self.economic_game.current_floor
        if self.active_phase == 4:
            return self.euler_game.current_floor
        return self.final_game.current_floor

    @property
    def active_graph(self) -> Graph[int]:
        if self.active_phase == 1:
            return self.level.graph
        if self.active_phase == 2:
            return self.hamilton_challenge.graph
        if self.active_phase == 3:
            return self.economic_challenge.graph
        if self.active_phase == 4:
            return self.euler_challenge.graph
        return self.final_challenge.graph

    def run(self) -> None:
        while True:
            self._handle_events()
            self._draw()
            self.clock.tick(60)

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
                if self.menu.screen is Screen.MAIN_MENU:
                    if event.key == pygame.K_RETURN:
                        self._continue_game()
                    elif event.key == pygame.K_s:
                        self.menu.show_level_select()
                    continue
                if self.menu.screen is Screen.LEVEL_SELECT:
                    if event.key == pygame.K_BACKSPACE:
                        self.menu.show_main_menu()
                    elif pygame.K_1 <= event.key <= pygame.K_5:
                        self._start_phase(event.key - pygame.K_0)
                    continue
                if self.menu.screen is Screen.RESULT:
                    if event.key == pygame.K_RETURN:
                        self._continue_after_result()
                    elif event.key == pygame.K_r:
                        self._replay_result()
                    elif event.key == pygame.K_s:
                        self.menu.show_level_select()
                    continue

                if event.key == pygame.K_r:
                    if self.active_phase == 2:
                        self._restart_hamilton_attempt()
                    elif self.active_phase == 3:
                        self._restart_economic_attempt()
                    elif self.active_phase == 4:
                        self._restart_euler_attempt()
                    elif self.active_phase == 5:
                        self._restart_final_attempt()
                elif event.key == pygame.K_RETURN:
                    self._travel()
                elif event.key == pygame.K_e:
                    self._collect_items()
                elif pygame.K_1 <= event.key <= pygame.K_6:
                    self._select_floor(event.key - pygame.K_0)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.menu.screen is Screen.MAIN_MENU:
                    if self.main_continue_rect.collidepoint(event.pos):
                        self._continue_game()
                    elif self.main_select_rect.collidepoint(event.pos):
                        self.menu.show_level_select()
                    elif self.main_exit_rect.collidepoint(event.pos):
                        pygame.quit()
                        sys.exit()
                    continue
                if self.menu.screen is Screen.LEVEL_SELECT:
                    if self.level_back_rect.collidepoint(event.pos):
                        self.menu.show_main_menu()
                        continue
                    for phase, rect in self.level_rects.items():
                        if rect.collidepoint(event.pos):
                            self._start_phase(phase)
                            break
                    continue
                if self.menu.screen is Screen.RESULT:
                    if self.result_continue_rect.collidepoint(event.pos):
                        self._continue_after_result()
                    elif self.result_replay_rect.collidepoint(event.pos):
                        self._replay_result()
                    elif self.result_select_rect.collidepoint(event.pos):
                        self.menu.show_level_select()
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

    def _start_phase(self, phase: int) -> None:
        if not self.menu.start_level(phase, self.progress_manager):
            self.message = f"A fase {phase} esta bloqueada."
            return
        self.active_phase = phase
        self.level = self.phase_levels[0]
        if phase == 1:
            self.game = GameState(self.level)
        elif phase == 2:
            self.hamilton_game.reset()
        elif phase == 3:
            self.economic_game.reset()
        elif phase == 4:
            self.euler_game.reset()
        else:
            self.final_game.reset()
        self.item_progress = ItemProgress(self.phase_levels[phase - 1])
        self.attempt_result = None
        self.attempt_id = str(uuid4())
        self.score_manager.begin_attempt(self.attempt_id)
        self.attempt_started_at = time.monotonic()
        self.attempt_movements = 0
        self.selected_floor = None
        self.message = f"Fase ativa: {self.phase_levels[phase - 1].name}."
        if phase == 3:
            self.message += (
                f" Custo minimo: {self.economic_game.optimal_cost:g}."
            )
        elif phase == 5:
            self.message += " Alcance a saida e retorne ao inicio."

    def _continue_after_result(self) -> None:
        recommended = self.progress_manager.recommended_level
        if recommended is None:
            self.menu.show_level_select()
            self.message = (
                "Todo o conteudo disponivel foi concluido. "
                "Escolha uma fase para rejogar."
            )
            return
        self._start_phase(recommended)

    def _replay_result(self) -> None:
        if self.menu.result_level is not None:
            self._start_phase(self.menu.result_level)

    def _current_objectives(self) -> tuple[OptionalObjective, ...]:
        level = self.phase_levels[self.active_phase - 1]
        if self.active_phase == 1:
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
        if self.attempt_result is not None:
            return
        level = self.phase_levels[self.active_phase - 1]
        if self.active_phase == 1:
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
        challenge_ids = level.required_challenges or ("collect_and_exit",)
        self.attempt_result = self.score_manager.finalize_attempt(
            self.attempt_id,
            self.active_phase,
            items=collected_items,
            objectives=completed_objectives,
            completed_challenges=challenge_ids,
            movements=self.attempt_movements,
            elapsed_seconds=time.monotonic() - self.attempt_started_at,
            completion_score=level.completion_score,
        )
        self.progress_manager.complete_level(self.active_phase)
        persisted = self.progress_manager.to_dict()
        self.saved_progress.update(persisted)
        try:
            self.saved_progress = self.save_manager.record_result(
                self.saved_progress,
                self.active_phase,
                self.attempt_result.to_dict(),
            )
        except SaveError as error:
            self.message = f"Fase concluida, mas o progresso nao foi salvo: {error}"
        self.menu.show_result(self.active_phase)

    def _select_floor(self, floor: int) -> None:
        missing_keys = self._missing_connection_keys(floor)
        if missing_keys:
            self.selected_floor = None
            self.message = f"Elevador bloqueado. Falta a chave: {', '.join(missing_keys)}."
            return
        if self.active_phase == 1:
            if self.game.is_complete:
                return
            if self.level.graph.has_edge(self.current_floor, floor):
                self.selected_floor = floor
                self.message = f"Destino selecionado: andar {floor:02d}."
            else:
                self.selected_floor = None
                self.message = f"Nao ha elevador do andar {self.current_floor:02d} para {floor:02d}."
            return

        if self.active_phase == 3:
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

        if self.active_phase == 4:
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

        if self.active_phase == 5:
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
            self.message = f"Andar {floor:02d} ja visitado. Nao e permitido voltar."
        elif (
            floor == self.hamilton_challenge.end_floor
            and len(self.hamilton_game.visited_sequence)
            != len(self.hamilton_challenge.graph.vertices) - 1
        ):
            self.selected_floor = None
            self.message = (
                f"O andar final {floor:02d} so pode ser visitado depois dos demais."
            )
        else:
            self.selected_floor = floor
            self.message = f"Destino selecionado: andar {floor:02d}."

    def _travel(self) -> None:
        if self.selected_floor is None:
            self.message = "Selecione primeiro um dos destinos disponiveis."
            return
        missing_keys = self._missing_connection_keys(self.selected_floor)
        if missing_keys:
            self.selected_floor = None
            self.message = f"Elevador bloqueado. Falta a chave: {', '.join(missing_keys)}."
            return
        previous_move_count = self._successful_move_count()
        if self.active_phase == 1:
            self.message = self.game.move_to(self.selected_floor)
        elif self.active_phase == 2:
            self.message = self.hamilton_game.move_to(self.selected_floor)
        elif self.active_phase == 3:
            self.message = self.economic_game.move_to(self.selected_floor)
        elif self.active_phase == 4:
            self.message = self.euler_game.move_to(self.selected_floor)
        else:
            self.message = self.final_game.move_to(self.selected_floor)
        self.selected_floor = None
        current_move_count = self._successful_move_count()
        if current_move_count > previous_move_count:
            self.attempt_movements += 1
            if self.active_phase != 1:
                self.item_progress.record_movement(self.current_floor)
            self._sync_objective_score()
            discovered = (
                self.game.items_on_current_floor
                if self.active_phase == 1
                else self.item_progress.items_on_floor(self.current_floor)
            )
            if discovered:
                names = ", ".join(item.name for item in discovered)
                self.message += f" Item encontrado: {names}. Pressione E para coletar."
        if (
            self.active_phase == 1 and self.game.is_complete
            or self.active_phase == 2 and self.hamilton_game.is_complete
            or self.active_phase == 3 and self.economic_game.is_complete
            or self.active_phase == 4 and self.euler_game.is_complete
            or self.active_phase == 5 and self.final_game.is_complete
        ):
            self._complete_phase()

    def _successful_move_count(self) -> int:
        if self.active_phase == 1:
            return self.game.movement_count
        game = {
            2: self.hamilton_game,
            3: self.economic_game,
            4: self.euler_game,
            5: self.final_game,
        }[self.active_phase]
        return len(game.visited_sequence)

    def _missing_connection_keys(self, destination: int) -> tuple[str, ...]:
        level = self.phase_levels[self.active_phase - 1]
        collected_keys = (
            self.game.collected_keys
            if self.active_phase == 1
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
        if self.menu.screen is not Screen.GAME:
            return
        if self.active_phase == 1:
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
        self.item_progress = ItemProgress(self.phase_levels[self.active_phase - 1])
        self.attempt_id = str(uuid4())
        self.score_manager.begin_attempt(self.attempt_id)
        self.attempt_started_at = time.monotonic()
        self.attempt_movements = 0
        self.attempt_result = None
        self.selected_floor = None

    def _restart_hamilton_attempt(self) -> None:
        self.hamilton_game.reset()
        self._reset_attempt_tracking()
        self.message = "Tentativa reiniciada no andar inicial."

    def _restart_economic_attempt(self) -> None:
        self.economic_game.reset()
        self._reset_attempt_tracking()
        self.message = (
            "Tentativa reiniciada no andar inicial. "
            f"Custo minimo: {self.economic_game.optimal_cost:g}."
        )

    def _restart_euler_attempt(self) -> None:
        self.euler_game.reset()
        self._reset_attempt_tracking()
        self.message = "Inspecao reiniciada no andar inicial."

    def _restart_final_attempt(self) -> None:
        self.final_game.reset()
        self._reset_attempt_tracking()
        self.message = "Tentativa reiniciada no andar inicial."

    def _draw(self) -> None:
        self.screen.fill(BACKGROUND)
        if self.menu.screen is Screen.MAIN_MENU:
            self._draw_main_menu()
        elif self.menu.screen is Screen.LEVEL_SELECT:
            self._draw_level_select()
        elif self.menu.screen is Screen.RESULT:
            self._draw_result()
        else:
            self._draw_header()
            self._draw_floor_panel()
            self._draw_destination_panel()
            self._draw_footer()
        pygame.display.flip()

    def _draw_main_menu(self) -> None:
        title = self.title_font.render("FLOOR 13", True, TEXT)
        subtitle = self.body_font.render(
            "Explore os andares. Descubra a saida.", True, MUTED
        )
        self.screen.blit(title, title.get_rect(center=(WIDTH // 2, 170)))
        self.screen.blit(subtitle, subtitle.get_rect(center=(WIDTH // 2, 215)))
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
            (WIDTH // 2 - 120, 500),
        )

    def _draw_level_select(self) -> None:
        self._text("SELECIONE UMA FASE", self.title_font, TEXT, (64, 54))
        self._text(
            "Fases bloqueadas serao liberadas ao concluir a anterior.",
            self.small_font,
            MUTED,
            (66, 104),
        )
        self.level_rects.clear()
        for index, level in enumerate(self.phase_levels):
            phase = index + 1
            rect = pygame.Rect(150, 150 + index * 75, 660, 62)
            self.level_rects[phase] = rect
            unlocked = self.progress_manager.can_start(phase)
            completed = phase in self.progress_manager.completed_levels
            background = (
                ACCENT_DARK if completed else PANEL_LIGHT if unlocked else (39, 43, 55)
            )
            border = ACCENT if unlocked else (70, 75, 88)
            pygame.draw.rect(self.screen, background, rect, border_radius=11)
            pygame.draw.rect(self.screen, border, rect, width=2, border_radius=11)
            status = (
                f"CONCLUIDA  •  MELHOR {self.saved_progress['level_scores'][str(phase)]}"
                if completed
                else "DESBLOQUEADA"
                if unlocked
                else "BLOQUEADA"
            )
            self._text(
                f"{phase}. {level.name}",
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
        pygame.draw.rect(
            self.screen, PANEL, self.level_back_rect, border_radius=10
        )
        self._text("VOLTAR", self.body_font, TEXT, (self.level_back_rect.x + 48, 560))

    def _draw_result(self) -> None:
        level_number = self.menu.result_level
        if level_number is None or self.attempt_result is None:
            self.menu.show_main_menu()
            return
        level = self.phase_levels[level_number - 1]
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
            next_text = f"Proxima fase desbloqueada: {recommended}. {self.phase_levels[recommended - 1].name}"
        else:
            next_text = "Todo o conteudo disponivel foi finalizado."
        self._text(next_text, self.body_font, ACCENT, (66, 386))

        buttons = (
            (
                self.result_continue_rect,
                "CONTINUAR" if recommended is not None else "SELECIONAR FASES",
            ),
            (self.result_replay_rect, "REJOGAR"),
            (self.result_select_rect, "SELECAO DE FASES"),
        )
        for rect, label in buttons:
            pygame.draw.rect(self.screen, PANEL, rect, border_radius=10)
            pygame.draw.rect(self.screen, ACCENT_DARK, rect, width=2, border_radius=10)
            text = self.small_font.render(label, True, TEXT)
            self.screen.blit(text, text.get_rect(center=rect.center))

    def _draw_header(self) -> None:
        self._text("FLOOR 13", self.title_font, TEXT, (64, 48))
        phase_label = (
            f"FASE {self.active_phase} • "
            f"{self.phase_levels[self.active_phase - 1].name.upper()}"
        )
        self._text(phase_label, self.small_font, ACCENT, (66, 91))
        pygame.draw.line(self.screen, PANEL_LIGHT, (64, 126), (896, 126), 2)

    def _draw_floor_panel(self) -> None:
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

        if self.active_phase == 1:
            self._draw_item_progress()
        elif self.active_phase == 2:
            self._draw_hamilton_progress()
        elif self.active_phase == 3:
            self._draw_economic_progress()
        elif self.active_phase == 4:
            self._draw_euler_progress()
        else:
            self._draw_final_progress()

    def _draw_item_progress(self) -> None:
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
            "Visite cada andar uma vez e termine no 06.",
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
            column = index // 4
            row = index % 4
            used_edge = edge in self.euler_game.used_edges
            state = "percorrida" if used_edge else "pendente"
            color = ACCENT if used_edge else MUTED
            self._text(
                f"{edge[0]:02d}-{edge[1]:02d}: {state}",
                self.small_font,
                color,
                (94 + column * 215, 477 + row * 20),
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
        rect = pygame.Rect(574, 145, 322, 439)
        pygame.draw.rect(self.screen, PANEL, rect, border_radius=18)
        pygame.draw.rect(self.screen, PANEL_LIGHT, rect, width=1, border_radius=18)
        available_items = (
            self.game.items_on_current_floor
            if self.active_phase == 1
            else self.item_progress.items_on_floor(self.current_floor)
        )
        if self.active_phase == 1:
            panel_title = "DESTINOS CONECTADOS"
            panel_hint = "Selecione um elevador"
        elif self.active_phase == 2:
            panel_title = "PROXIMOS ANDARES"
            panel_hint = "Visitados nao podem ser repetidos"
        elif self.active_phase == 3:
            panel_title = "ELEVADORES E CUSTOS"
            panel_hint = "Peso da aresta nesta conexao"
        elif self.active_phase == 5:
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
        for index, (floor, _) in enumerate(
            self.active_graph.neighbors(self.current_floor)
        ):
            destination = pygame.Rect(600, 230 + index * 48, 270, 40)
            self.destination_rects[floor] = destination
            selected = floor == self.selected_floor
            visited = (
                self.active_phase == 2
                and floor in self.hamilton_game.visited_floors
            )
            final_too_early = (
                self.active_phase == 2
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
                self.active_phase == 4 and euler_edge in self.euler_game.used_edges
            )
            final_finished = (
                self.active_phase == 5 and self.final_game.is_finished
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
                    if self.active_phase in (3, 5)
                    else (
                        f"{destination_label}  INSPECIONADA"
                        if self.active_phase == 4 and euler_used
                        else destination_label
                    )
                ),
                self.body_font,
                TEXT,
                (destination.x + 14, destination.y + 8),
            )
            if self.active_phase not in (3, 4, 5):
                self._text(
                    "›",
                    self.heading_font,
                    ACCENT,
                    (destination.right - 32, destination.y + 5),
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
        if self.active_phase == 1:
            travel_label = "VIAJAR  [ENTER]"
        elif self.active_phase == 2:
            travel_label = "MOVER  [ENTER]"
        elif self.active_phase == 3:
            travel_label = "VIAJAR  [ENTER]"
        elif self.active_phase == 4:
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
        if self.active_phase in (2, 3, 4, 5):
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

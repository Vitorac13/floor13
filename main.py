"""Interface Pygame das fases implementadas de Floor 13."""

from __future__ import annotations

import sys

import pygame

from economic_challenge import EconomicChallengeManager
from economic_game_state import EconomicGameState
from game_state import GameState
from hamilton_challenge import HamiltonChallengeManager
from hamilton_game_state import HamiltonGameState
from graph import Graph
from level import ItemKind
from level_manager import LevelManager

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
    def __init__(self) -> None:
        pygame.init()
        self.level = LevelManager.create_first_contact()
        self.game = GameState(self.level)
        self.hamilton_challenge = HamiltonChallengeManager.create_no_turning_back()
        self.hamilton_game = HamiltonGameState(self.hamilton_challenge)
        self.economic_challenge = EconomicChallengeManager.create_economic_elevator()
        self.economic_game = EconomicGameState(self.economic_challenge)
        self.active_phase = 1
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

    @property
    def current_floor(self) -> int:
        if self.active_phase == 1:
            return self.game.current_floor
        if self.active_phase == 2:
            return self.hamilton_game.current_floor
        return self.economic_game.current_floor

    @property
    def active_graph(self) -> Graph[int]:
        if self.active_phase == 1:
            return self.level.graph
        if self.active_phase == 2:
            return self.hamilton_challenge.graph
        return self.economic_challenge.graph

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
                if event.key == pygame.K_F1:
                    self._switch_phase(1)
                if event.key == pygame.K_F2:
                    self._switch_phase(2)
                if event.key == pygame.K_F3:
                    self._switch_phase(3)
                if event.key == pygame.K_r:
                    if self.active_phase == 2:
                        self._restart_hamilton_attempt()
                    elif self.active_phase == 3:
                        self._restart_economic_attempt()
                if event.key == pygame.K_RETURN:
                    self._travel()
                if event.key == pygame.K_e and self.active_phase == 1:
                    self._collect_items()
                if pygame.K_1 <= event.key <= pygame.K_6:
                    self._select_floor(event.key - pygame.K_0)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.collect_rect.collidepoint(event.pos):
                    if self.active_phase == 1:
                        self._collect_items()
                    elif self.active_phase == 2:
                        self._restart_hamilton_attempt()
                    else:
                        self._restart_economic_attempt()
                    continue
                if self.travel_rect.collidepoint(event.pos):
                    self._travel()
                    continue
                for floor, rect in self.destination_rects.items():
                    if rect.collidepoint(event.pos):
                        self._select_floor(floor)
                        break

    def _select_floor(self, floor: int) -> None:
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
        if self.active_phase == 1:
            self.message = self.game.move_to(self.selected_floor)
        elif self.active_phase == 2:
            self.message = self.hamilton_game.move_to(self.selected_floor)
        else:
            self.message = self.economic_game.move_to(self.selected_floor)
        self.selected_floor = None

    def _collect_items(self) -> None:
        if self.game.is_complete:
            return
        items = self.game.collect_items_here()
        if not items:
            self.message = "Nao ha itens para coletar neste andar."
            return
        names = ", ".join(item.name for item in items)
        if all(item.kind is ItemKind.REQUIRED for item in items):
            self.message = f"Item obrigatorio coletado: {names}."
        elif all(item.kind is ItemKind.BONUS for item in items):
            self.message = f"Bonus coletado: {names}."
        else:
            self.message = f"Itens coletados: {names}."

    def _switch_phase(self, phase: int) -> None:
        if phase not in (1, 2, 3):
            return
        self.active_phase = phase
        self.selected_floor = None
        if phase == 1:
            self.message = f"Fase ativa: {self.level.name}."
        elif phase == 2:
            self.message = f"Fase ativa: {self.hamilton_challenge.name}."
        else:
            self.message = (
                f"Fase ativa: {self.economic_challenge.name}. "
                f"Custo minimo: {self.economic_game.optimal_cost:g}."
            )

    def _restart_hamilton_attempt(self) -> None:
        self.hamilton_game.reset()
        self.selected_floor = None
        self.message = "Tentativa reiniciada no andar inicial."

    def _restart_economic_attempt(self) -> None:
        self.economic_game.reset()
        self.selected_floor = None
        self.message = (
            "Tentativa reiniciada no andar inicial. "
            f"Custo minimo: {self.economic_game.optimal_cost:g}."
        )

    def _draw(self) -> None:
        self.screen.fill(BACKGROUND)
        self._draw_header()
        self._draw_floor_panel()
        self._draw_destination_panel()
        self._draw_footer()
        pygame.display.flip()

    def _draw_header(self) -> None:
        self._text("FLOOR 13", self.title_font, TEXT, (64, 48))
        if self.active_phase == 1:
            phase_label = f"FASE 1 • {self.level.name.upper()}   F1-F3: TROCAR"
        elif self.active_phase == 2:
            phase_label = f"FASE 2 • {self.hamilton_challenge.name.upper()}   F1-F3: TROCAR"
        else:
            phase_label = f"FASE 3 • {self.economic_challenge.name.upper()}   F1-F3: TROCAR"
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
        else:
            self._draw_economic_progress()

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

    def _draw_destination_panel(self) -> None:
        rect = pygame.Rect(574, 145, 322, 439)
        pygame.draw.rect(self.screen, PANEL, rect, border_radius=18)
        pygame.draw.rect(self.screen, PANEL_LIGHT, rect, width=1, border_radius=18)
        if self.active_phase == 1:
            panel_title = "DESTINOS CONECTADOS"
            panel_hint = "Selecione um elevador"
        elif self.active_phase == 2:
            panel_title = "PROXIMOS ANDARES"
            panel_hint = "Visitados nao podem ser repetidos"
        else:
            panel_title = "ELEVADORES E CUSTOS"
            panel_hint = "Peso da aresta nesta conexao"
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
            color = (
                ACCENT_DARK
                if selected
                else (WARNING if visited or final_too_early else PANEL_LIGHT)
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
            if visited:
                destination_label += " • VISITADO"
            elif final_too_early:
                destination_label += " • FINAL"
            self._text(
                (
                    f"{destination_label}  CUSTO "
                    f"{self.active_graph.weight(self.current_floor, floor):g}"
                    if self.active_phase == 3
                    else destination_label
                ),
                self.body_font,
                TEXT,
                (destination.x + 14, destination.y + 8),
            )
            if self.active_phase != 3:
                self._text(
                    "›",
                    self.heading_font,
                    ACCENT,
                    (destination.right - 32, destination.y + 5),
                )

        self.collect_rect = pygame.Rect(600, 444, 270, 54)
        if self.active_phase == 1:
            pygame.draw.rect(
                self.screen,
                WARNING if self.game.items_on_current_floor else PANEL_LIGHT,
                self.collect_rect,
                border_radius=12,
            )
            self._text("COLETAR  [E]", self.body_font, BACKGROUND, (670, 460))
        elif self.active_phase == 2:
            pygame.draw.rect(
                self.screen, WARNING, self.collect_rect, border_radius=12
            )
            self._text("REINICIAR  [R]", self.body_font, BACKGROUND, (656, 460))
        else:
            pygame.draw.rect(
                self.screen, WARNING, self.collect_rect, border_radius=12
            )
            self._text("REINICIAR  [R]", self.body_font, BACKGROUND, (656, 460))

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
        else:
            travel_label = "VIAJAR  [ENTER]"
        self._text(travel_label, self.body_font, TEXT, (635, 528))

    def _draw_footer(self) -> None:
        self._text(self.message, self.small_font, WARNING, (66, 599))
        if self.active_phase in (2, 3):
            self._text(
                "R reiniciar • Esc sair",
                self.small_font,
                MUTED,
                (735, 599),
            )
        else:
            self._text("ESC • sair", self.small_font, MUTED, (820, 599))

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

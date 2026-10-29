"""Prototipo Pygame da fase Primeiro contato."""

from __future__ import annotations

import sys

import pygame

from game_state import GameState
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
        pygame.display.set_caption("Floor 13 — Primeiro contato")
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
        return self.game.current_floor

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
                if event.key == pygame.K_RETURN:
                    self._travel()
                if event.key == pygame.K_e:
                    self._collect_items()
                if pygame.K_1 <= event.key <= pygame.K_6:
                    self._select_floor(event.key - pygame.K_0)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
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

    def _select_floor(self, floor: int) -> None:
        if self.game.is_complete:
            return
        if self.level.graph.has_edge(self.current_floor, floor):
            self.selected_floor = floor
            self.message = f"Destino selecionado: andar {floor:02d}."
        else:
            self.selected_floor = None
            self.message = f"Nao ha elevador do andar {self.current_floor:02d} para {floor:02d}."

    def _travel(self) -> None:
        if self.game.is_complete:
            return
        if self.selected_floor is None:
            self.message = "Selecione primeiro um dos destinos disponiveis."
            return
        self.message = self.game.move_to(self.selected_floor)
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

    def _draw(self) -> None:
        self.screen.fill(BACKGROUND)
        self._draw_header()
        self._draw_floor_panel()
        self._draw_destination_panel()
        self._draw_footer()
        pygame.display.flip()

    def _draw_header(self) -> None:
        self._text("FLOOR 13", self.title_font, TEXT, (64, 48))
        self._text(
            f"FASE 1 • {self.level.name.upper()}",
            self.small_font,
            ACCENT,
            (66, 91),
        )
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

        self._text("ITENS NESTE ANDAR", self.small_font, MUTED, (94, 378))
        current_items = self.game.items_on_current_floor
        if current_items:
            visible_items = current_items[:3]
            for index, item in enumerate(visible_items):
                color = ACCENT if item.kind is ItemKind.REQUIRED else WARNING
                self._text(
                    f"{item.kind.value}: {item.name}",
                    self.small_font,
                    color,
                    (94, 402 + index * 21),
                )
            remaining_items = len(current_items) - len(visible_items)
            if remaining_items:
                self._text(
                    f"+{remaining_items} outro(s) item(ns)",
                    self.small_font,
                    MUTED,
                    (94, 465),
                )
        elif self.game.all_items_on_current_floor:
            self._text("Itens deste andar ja coletados.", self.small_font, MUTED, (94, 404))
        else:
            self._text("Este andar nao possui itens.", self.small_font, MUTED, (94, 404))

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

    def _draw_destination_panel(self) -> None:
        rect = pygame.Rect(574, 145, 322, 439)
        pygame.draw.rect(self.screen, PANEL, rect, border_radius=18)
        pygame.draw.rect(self.screen, PANEL_LIGHT, rect, width=1, border_radius=18)
        self._text("DESTINOS CONECTADOS", self.heading_font, TEXT, (600, 171))
        self._text("Selecione um elevador", self.small_font, MUTED, (600, 201))

        self.destination_rects.clear()
        for index, (floor, _) in enumerate(
            self.level.graph.neighbors(self.current_floor)
        ):
            destination = pygame.Rect(600, 236 + index * 62, 270, 48)
            self.destination_rects[floor] = destination
            selected = floor == self.selected_floor
            color = ACCENT_DARK if selected else PANEL_LIGHT
            pygame.draw.rect(self.screen, color, destination, border_radius=10)
            pygame.draw.rect(
                self.screen,
                ACCENT if selected else (70, 79, 99),
                destination,
                width=2,
                border_radius=10,
            )
            self._text(
                f"ANDAR {floor:02d}",
                self.body_font,
                TEXT,
                (destination.x + 17, destination.y + 12),
            )
            self._text(
                "›",
                self.heading_font,
                ACCENT,
                (destination.right - 32, destination.y + 9),
            )

        self.collect_rect = pygame.Rect(600, 444, 270, 54)
        pygame.draw.rect(
            self.screen,
            WARNING if self.game.items_on_current_floor else PANEL_LIGHT,
            self.collect_rect,
            border_radius=12,
        )
        self._text("COLETAR  [E]", self.body_font, BACKGROUND, (670, 460))

        self.travel_rect = pygame.Rect(600, 510, 270, 58)
        pygame.draw.rect(
            self.screen,
            ACCENT_DARK if self.selected_floor is not None else PANEL_LIGHT,
            self.travel_rect,
            border_radius=12,
        )
        self._text("VIAJAR  [ENTER]", self.body_font, TEXT, (635, 528))

    def _draw_footer(self) -> None:
        self._text(self.message, self.small_font, WARNING, (66, 599))
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

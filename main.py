"""Prototipo Pygame da etapa 2: navegar pelos elevadores disponiveis."""

from __future__ import annotations

import sys

import pygame

from graph import Graph

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


def create_demo_building() -> Graph[int]:
    """Cria o pequeno grafo fixo utilizado no prototipo inicial."""
    building = Graph[int](range(1, 9))
    for first, second in (
        (1, 2),
        (1, 4),
        (2, 3),
        (2, 5),
        (3, 6),
        (4, 5),
        (4, 7),
        (5, 6),
        (5, 8),
        (7, 8),
    ):
        building.add_edge(first, second)
    return building


class ElevatorPrototype:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("Floor 13 — prototipo")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.title_font = pygame.font.Font(None, 42)
        self.heading_font = pygame.font.Font(None, 29)
        self.body_font = pygame.font.Font(None, 24)
        self.small_font = pygame.font.Font(None, 20)
        self.graph = create_demo_building()
        self.current_floor = 1
        self.selected_floor: int | None = None
        self.message = "Escolha um destino conectado pelo elevador."
        self.destination_rects: dict[int, pygame.Rect] = {}
        self.travel_rect = pygame.Rect(610, 525, 285, 58)

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
                if pygame.K_1 <= event.key <= pygame.K_8:
                    self._select_floor(event.key - pygame.K_0)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for floor, rect in self.destination_rects.items():
                    if rect.collidepoint(event.pos):
                        self._select_floor(floor)
                        break
                else:
                    if self.travel_rect.collidepoint(event.pos):
                        self._travel()

    def _select_floor(self, floor: int) -> None:
        if self.graph.has_edge(self.current_floor, floor):
            self.selected_floor = floor
            self.message = f"Destino selecionado: andar {floor:02d}."
        else:
            self.selected_floor = None
            self.message = f"Nao ha elevador do andar {self.current_floor:02d} para {floor:02d}."

    def _travel(self) -> None:
        if self.selected_floor is None:
            self.message = "Selecione primeiro um dos destinos disponiveis."
            return
        self.current_floor = self.selected_floor
        self.selected_floor = None
        self.message = f"Voce chegou ao andar {self.current_floor:02d}."

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
            "PROTOTIPO • ETAPA 2: ELEVADORES",
            self.small_font,
            ACCENT,
            (66, 91),
        )
        pygame.draw.line(self.screen, PANEL_LIGHT, (64, 126), (896, 126), 2)

    def _draw_floor_panel(self) -> None:
        rect = pygame.Rect(64, 158, 480, 410)
        pygame.draw.rect(self.screen, PANEL, rect, border_radius=18)
        pygame.draw.rect(self.screen, PANEL_LIGHT, rect, width=1, border_radius=18)
        self._text("ANDAR ATUAL", self.small_font, MUTED, (94, 188))

        floor_card = pygame.Rect(94, 226, 420, 230)
        pygame.draw.rect(self.screen, (25, 30, 43), floor_card, border_radius=16)
        pygame.draw.rect(self.screen, ACCENT_DARK, floor_card, width=2, border_radius=16)
        self._text(
            f"{self.current_floor:02d}",
            pygame.font.Font(None, 116),
            TEXT,
            (124, 258),
        )
        self._text("PAVIMENTO", self.small_font, MUTED, (130, 365))
        self._draw_elevator_icon(390, 277)
        self._text("ELEVADOR", self.small_font, ACCENT, (369, 382))
        self._text("O que existe neste andar?", self.body_font, TEXT, (94, 489))
        self._text(
            f"{len(self.graph.neighbors(self.current_floor))} destinos conectados",
            self.small_font,
            MUTED,
            (94, 522),
        )

    def _draw_destination_panel(self) -> None:
        rect = pygame.Rect(574, 158, 322, 346)
        pygame.draw.rect(self.screen, PANEL, rect, border_radius=18)
        pygame.draw.rect(self.screen, PANEL_LIGHT, rect, width=1, border_radius=18)
        self._text("ELEVADORES DISPONIVEIS", self.heading_font, TEXT, (600, 188))
        self._text("Selecione um destino", self.small_font, MUTED, (600, 220))

        self.destination_rects.clear()
        for index, (floor, _) in enumerate(self.graph.neighbors(self.current_floor)):
            destination = pygame.Rect(600, 260 + index * 64, 270, 50)
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
                (destination.x + 17, destination.y + 14),
            )
            self._text("›", self.heading_font, ACCENT, (destination.right - 32, destination.y + 11))

        self.travel_rect = pygame.Rect(600, 525, 270, 58)
        pygame.draw.rect(
            self.screen,
            ACCENT_DARK if self.selected_floor is not None else PANEL_LIGHT,
            self.travel_rect,
            border_radius=12,
        )
        self._text("VIAJAR  [ENTER]", self.body_font, TEXT, (635, 543))

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

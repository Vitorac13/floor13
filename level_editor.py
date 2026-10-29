"""Editor visual de fases compativeis com o formato JSON do jogo."""

from __future__ import annotations

import copy
import json
import math
from pathlib import Path
from typing import Any

import pygame

from challenge_registry import ChallengeRegistry
from level_manager import DEFAULT_LEVELS_DIR, LevelManager


BACKGROUND = (19, 22, 32)
PANEL = (31, 36, 50)
PANEL_LIGHT = (43, 50, 67)
TEXT = (239, 241, 247)
MUTED = (160, 170, 190)
ACCENT = (100, 208, 190)
ACCENT_DARK = (43, 125, 117)
WARNING = (244, 190, 105)
ERROR = (240, 118, 118)


def new_level_config() -> dict[str, Any]:
    existing_levels = LevelManager.discover_levels().levels
    number = max((level.number for level in existing_levels), default=0) + 1
    existing_ids = {level.identifier for level in existing_levels}
    identifier = f"phase-{number:02d}"
    while identifier in existing_ids:
        number += 1
        identifier = f"phase-{number:02d}"
    return {
        "id": identifier,
        "number": number,
        "name": "Nova fase",
        "graph": {"vertices": [1], "edges": []},
        "start_floor": 1,
        "exit_floor": 1,
        "items": [],
        "exit_requirements": {"keys": [], "challenges": []},
        "connection_requirements": [],
        "challenge": {"type": "collect_and_exit"},
        "optional_objectives": [],
        "rewards": {"completion": 300},
    }


class LevelEditor:
    """Estado e interface do editor; usa o mesmo validador/carregador do jogo."""

    def __init__(self) -> None:
        if not pygame.font.get_init():
            pygame.font.init()
        self._fonts = {
            size: pygame.font.Font(None, size)
            for size in (16, 18, 19, 20, 21, 22, 23, 24, 25)
        }
        self.config = new_level_config()
        self.positions: dict[int, tuple[int, int]] = {}
        self.active_path: Path | None = None
        self.selected_vertex: int | None = 1
        self.selected_item: int | None = None
        self.item_list_offset = 0
        self.selected_objective: int | None = None
        self.objective_list_offset = 0
        self.tab = "phase"
        self.mode = "select"
        self.edge_origin: int | None = None
        self.dragging = False
        self.status = "Clique em um andar para seleciona-lo; arraste para mover."
        self.status_error = False
        self.focused_field: str | None = None
        self.field_buffer = ""
        self.path_dialog: str | None = None
        self.path_buffer = ""
        self.pending_overwrite: Path | None = None
        self._back_requested = False
        self._buttons: dict[str, pygame.Rect] = {}
        self._field_rects: dict[str, pygame.Rect] = {}
        self._item_rects: list[tuple[int, pygame.Rect]] = []
        self._objective_rects: list[tuple[int, pygame.Rect]] = []
        self.canvas_rect = pygame.Rect(20, 112, 600, 450)
        self._layout_positions()

    def _font(self, size: int) -> pygame.font.Font:
        return self._fonts[size]

    @property
    def vertices(self) -> list[int]:
        return self.config["graph"]["vertices"]

    @property
    def edges(self) -> list[list[int]]:
        return self.config["graph"]["edges"]

    @property
    def items(self) -> list[dict[str, Any]]:
        return self.config["items"]

    @property
    def objectives(self) -> list[dict[str, Any]]:
        return self.config.get("optional_objectives", [])

    def _layout_positions(self) -> None:
        self.positions = {}
        vertices = self.vertices
        if not vertices:
            return
        center = (self.canvas_rect.centerx, self.canvas_rect.centery)
        radius_x = max(55, self.canvas_rect.width * 0.39)
        radius_y = max(45, self.canvas_rect.height * 0.37)
        for index, vertex in enumerate(vertices):
            angle = -math.pi / 2 + 2 * math.pi * index / len(vertices)
            self.positions[vertex] = (
                round(center[0] + radius_x * math.cos(angle)),
                round(center[1] + radius_y * math.sin(angle)),
            )

    def new_level(self) -> None:
        self.config = new_level_config()
        self.active_path = None
        self.selected_vertex = 1
        self.selected_item = None
        self.item_list_offset = 0
        self.selected_objective = None
        self.objective_list_offset = 0
        self.tab = "phase"
        self.edge_origin = None
        self.mode = "select"
        self.focused_field = None
        self.path_dialog = None
        self.pending_overwrite = None
        self._layout_positions()
        self._set_status("Nova fase pronta para edicao.")

    def load_config(self, config: dict[str, Any], source: Path | None = None) -> None:
        if not isinstance(config, dict):
            raise ValueError("A configuracao importada deve ser um objeto JSON.")
        self.config = copy.deepcopy(config)
        graph = self.config.get("graph")
        vertices = graph.get("vertices", []) if isinstance(graph, dict) else []
        self.selected_vertex = vertices[0] if vertices else None
        self.selected_item = None
        self.item_list_offset = 0
        self.selected_objective = None
        self.objective_list_offset = 0
        self.active_path = source
        self.edge_origin = None
        self.mode = "select"
        self.focused_field = None
        self.path_dialog = None
        self.pending_overwrite = None
        self._layout_positions()
        self._set_status(
            f"Fase importada: {source.name if source else self.config.get('id', 'sem ID')}."
        )

    def import_file(self, path: str | Path) -> None:
        source = Path(path).expanduser()
        try:
            with source.open(encoding="utf-8") as file:
                config = json.load(file)
        except FileNotFoundError as error:
            raise ValueError(f"Arquivo nao encontrado: {source}") from error
        except json.JSONDecodeError as error:
            raise ValueError(
                f"JSON invalido na linha {error.lineno}, coluna {error.colno}: "
                f"{error.msg}"
            ) from error
        self.load_config(config, source)

    def validate(self) -> None:
        try:
            level = LevelManager.from_config(copy.deepcopy(self.config))
            LevelManager.validate(level)
        except (TypeError, ValueError, KeyError) as error:
            self._set_status(f"Fase invalida: {error}", error=True)
            raise ValueError(str(error)) from error
        self._set_status("Fase valida e carregavel pelo jogo.")

    def export_file(self, path: str | Path, overwrite: bool = False) -> Path:
        self.validate()
        destination = Path(path).expanduser()
        if destination.parent.resolve() == DEFAULT_LEVELS_DIR.resolve():
            for existing in LevelManager.discover_levels().levels:
                if (
                    self.active_path is not None
                    and self.active_path.resolve() == destination.resolve()
                    and existing.identifier == self.config.get("id")
                ):
                    continue
                if existing.identifier == self.config.get("id"):
                    raise ValueError(
                        f"O identificador {existing.identifier!r} ja pertence a uma fase."
                    )
                if existing.number == self.config.get("number"):
                    raise ValueError(
                        f"O numero de fase {existing.number} ja esta em uso."
                    )
        if destination.exists() and not overwrite:
            raise FileExistsError(destination)
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("w", encoding="utf-8", newline="\n") as file:
                json.dump(self.config, file, ensure_ascii=False, indent=2)
                file.write("\n")
        except OSError as error:
            raise ValueError(f"Nao foi possivel exportar a fase: {error}") from error
        self.active_path = destination
        self._set_status(f"Fase exportada para {destination}.")
        return destination

    def add_vertex(self, position: tuple[int, int] | None = None) -> int:
        vertex = max(self.vertices, default=0) + 1
        self.vertices.append(vertex)
        if position is None:
            position = self.canvas_rect.center
        self.positions[vertex] = self._clamp_position(position)
        self.selected_vertex = vertex
        self.mode = "select"
        self._set_status(f"Andar {vertex} adicionado.")
        return vertex

    def move_vertex(self, vertex: int, position: tuple[int, int]) -> None:
        if vertex not in self.positions:
            raise ValueError(f"Andar inexistente: {vertex}.")
        self.positions[vertex] = self._clamp_position(position)

    def add_edge(self, first: int, second: int) -> None:
        if first not in self.vertices or second not in self.vertices:
            raise ValueError("A conexao deve usar andares existentes.")
        if first == second:
            raise ValueError("Um andar nao pode se conectar a si mesmo.")
        if any(set(edge[:2]) == {first, second} for edge in self.edges):
            raise ValueError(f"A conexao entre {first} e {second} ja existe.")
        self.edges.append([first, second])
        self._set_status(f"Conexao criada: {first} - {second}.")

    def remove_edge(self, first: int, second: int) -> None:
        for index, edge in enumerate(self.edges):
            if set(edge[:2]) == {first, second}:
                del self.edges[index]
                self._set_status(f"Conexao removida: {first} - {second}.")
                return
        raise ValueError("A conexao selecionada nao existe.")

    def remove_vertex(self, vertex: int) -> None:
        if vertex not in self.vertices:
            raise ValueError(f"Andar inexistente: {vertex}.")
        self.vertices.remove(vertex)
        self.config["graph"]["edges"] = [
            edge for edge in self.edges if vertex not in edge[:2]
        ]
        removed_items = [
            item for item in self.items if item.get("floor") == vertex
        ]
        self._remove_item_references(
            {item.get("id") for item in removed_items}, removed_floor=vertex
        )
        self.config["items"] = [
            item for item in self.items if item.get("floor") != vertex
        ]
        self.positions.pop(vertex, None)
        if self.selected_vertex == vertex:
            self.selected_vertex = self.vertices[0] if self.vertices else None
        self.selected_item = None
        suffix = f" {len(removed_items)} item(ns) do andar tambem removido(s)." if removed_items else ""
        self._set_status(f"Andar {vertex} e suas conexoes foram removidos.{suffix}")

    def add_item(self) -> int:
        if not self.vertices:
            raise ValueError("Adicione um andar antes de criar um item.")
        existing_ids = {item.get("id") for item in self.items}
        index = 1
        while f"item-{index}" in existing_ids:
            index += 1
        floor = self.selected_vertex or self.vertices[0]
        self.items.append(
            {
                "id": f"item-{index}",
                "name": f"Item {index}",
                "floor": floor,
                "type": "essential",
                "score": 100,
                "key": False,
            }
        )
        self.selected_item = len(self.items) - 1
        self.item_list_offset = max(0, len(self.items) - 6)
        self.tab = "items"
        self._set_status(f"Item item-{index} criado no andar {floor}.")
        return self.selected_item

    def update_item(self, index: int, **changes: Any) -> None:
        if not 0 <= index < len(self.items):
            raise ValueError("O item selecionado nao existe.")
        self.items[index].update(changes)

    def remove_item(self, index: int) -> None:
        if not 0 <= index < len(self.items):
            raise ValueError("O item selecionado nao existe.")
        identifier = self.items[index].get("id", "item")
        self._remove_item_references({identifier})
        del self.items[index]
        self.selected_item = None
        self._set_status(f"Item {identifier} removido.")

    def _remove_item_references(
        self, item_ids: set[Any], removed_floor: int | None = None
    ) -> None:
        requirements = self.config.get("exit_requirements")
        if isinstance(requirements, dict) and isinstance(requirements.get("keys"), list):
            requirements["keys"] = [
                key_id for key_id in requirements["keys"] if key_id not in item_ids
            ]
        connections = self.config.get("connection_requirements")
        if not isinstance(connections, list):
            return
        retained = []
        for requirement in connections:
            if not isinstance(requirement, dict):
                retained.append(requirement)
                continue
            if removed_floor in (requirement.get("from"), requirement.get("to")):
                continue
            keys = requirement.get("keys")
            if isinstance(keys, list):
                requirement["keys"] = [
                    key_id for key_id in keys if key_id not in item_ids
                ]
                if not requirement["keys"]:
                    continue
            retained.append(requirement)
        self.config["connection_requirements"] = retained

    def _replace_item_reference(self, old_id: str, new_id: str) -> None:
        requirements = self.config.get("exit_requirements")
        if isinstance(requirements, dict) and isinstance(requirements.get("keys"), list):
            requirements["keys"] = [
                new_id if key_id == old_id else key_id
                for key_id in requirements["keys"]
            ]
        connections = self.config.get("connection_requirements")
        if isinstance(connections, list):
            for requirement in connections:
                if isinstance(requirement, dict) and isinstance(requirement.get("keys"), list):
                    requirement["keys"] = [
                        new_id if key_id == old_id else key_id
                        for key_id in requirement["keys"]
                    ]

    def add_objective(self) -> int:
        existing_ids = {objective.get("id") for objective in self.objectives}
        index = 1
        while f"objective-{index}" in existing_ids:
            index += 1
        floor = self.selected_vertex or self.config.get("start_floor", 1)
        objective = {
            "id": f"objective-{index}",
            "name": f"Objetivo {index}",
            "description": "Visite o andar indicado.",
            "type": "visit_floor",
            "floor": floor,
            "reward": 100,
        }
        self.config.setdefault("optional_objectives", []).append(objective)
        self.selected_objective = len(self.objectives) - 1
        self.objective_list_offset = max(0, len(self.objectives) - 5)
        self.tab = "objectives"
        self._set_status(f"Objetivo objective-{index} criado.")
        return self.selected_objective

    def remove_objective(self, index: int) -> None:
        if not 0 <= index < len(self.objectives):
            raise ValueError("O objetivo selecionado nao existe.")
        identifier = self.objectives[index].get("id", "objetivo")
        del self.objectives[index]
        self.selected_objective = None
        self._set_status(f"Objetivo {identifier} removido.")

    def _clamp_position(self, position: tuple[int, int]) -> tuple[int, int]:
        return (
            min(max(position[0], self.canvas_rect.left + 28), self.canvas_rect.right - 28),
            min(max(position[1], self.canvas_rect.top + 28), self.canvas_rect.bottom - 28),
        )

    def _set_status(self, message: str, error: bool = False) -> None:
        self.status = message
        self.status_error = error

    def draw(self, screen: pygame.Surface) -> None:
        screen.fill(BACKGROUND)
        self._buttons = {}
        self._field_rects = {}
        self._item_rects = []
        self._objective_rects = []
        self._draw_header(screen)
        self._draw_canvas(screen)
        self._draw_tools(screen)
        self._draw_sidebar(screen)
        color = ERROR if self.status_error else ACCENT
        status = self._font(20).render(self.status, True, color)
        screen.blit(status, (20, 615))
        if self.path_dialog is not None:
            self._draw_path_dialog(screen)
        if self.pending_overwrite is not None:
            self._draw_overwrite_dialog(screen)
        elif self.focused_field is not None and self.focused_field.startswith("json:"):
            self._draw_json_dialog(screen)

    def _draw_header(self, screen: pygame.Surface) -> None:
        font = self._font(23)
        self._button(screen, "new", "Nova", pygame.Rect(20, 18, 82, 38), font)
        self._button(screen, "open", "Abrir", pygame.Rect(108, 18, 82, 38), font)
        self._button(screen, "save", "Salvar", pygame.Rect(196, 18, 82, 38), font)
        self._button(screen, "export", "Exportar", pygame.Rect(284, 18, 94, 38), font)
        self._button(screen, "validate", "Validar", pygame.Rect(384, 18, 82, 38), font)
        self._button(screen, "back", "Menu", pygame.Rect(856, 18, 84, 38), font)
        title = self._font(25).render(
            str(self.config.get("name", "Editor")), True, TEXT
        )
        screen.blit(title, (490, 26))

    def _draw_canvas(self, screen: pygame.Surface) -> None:
        pygame.draw.rect(screen, PANEL, self.canvas_rect, border_radius=8)
        pygame.draw.rect(screen, PANEL_LIGHT, self.canvas_rect, width=2, border_radius=8)
        font = self._font(21)
        graph = self.config.get("graph", {})
        edges = graph.get("edges", []) if isinstance(graph, dict) else []
        for edge in edges:
            if not isinstance(edge, list) or len(edge) < 2:
                continue
            first, second = edge[:2]
            if first not in self.positions or second not in self.positions:
                continue
            pygame.draw.line(
                screen,
                MUTED,
                self.positions[first],
                self.positions[second],
                3,
            )
        for vertex in self.vertices:
            position = self.positions.get(vertex)
            if position is None:
                continue
            is_start = vertex == self.config.get("start_floor")
            is_exit = vertex == self.config.get("exit_floor")
            fill = ACCENT_DARK if is_start else (130, 77, 89) if is_exit else PANEL_LIGHT
            if vertex == self.selected_vertex:
                fill = ACCENT
            pygame.draw.circle(screen, fill, position, 23)
            pygame.draw.circle(screen, TEXT, position, 23, 2)
            label = font.render(str(vertex), True, BACKGROUND if vertex == self.selected_vertex else TEXT)
            screen.blit(label, label.get_rect(center=position))
            if any(item.get("floor") == vertex for item in self.items):
                pygame.draw.circle(screen, WARNING, (position[0] + 17, position[1] - 17), 5)
        hint = "Inicio (verde)   Saida (vermelho)   Item (ponto amarelo)"
        screen.blit(font.render(hint, True, MUTED), (self.canvas_rect.x + 12, self.canvas_rect.bottom - 24))
        if self.edge_origin is not None:
            note = font.render(f"Selecione o segundo andar (origem {self.edge_origin}).", True, WARNING)
            screen.blit(note, (self.canvas_rect.x + 12, self.canvas_rect.y + 10))

    def _draw_tools(self, screen: pygame.Surface) -> None:
        font = self._font(20)
        labels = (
            ("add_vertex", "Adicionar andar", "add_vertex"),
            ("add_edge", "Criar conexao", "add_edge"),
            ("delete_edge", "Apagar conexao", "delete_edge"),
            ("delete_vertex", "Apagar andar", "delete_vertex"),
        )
        for index, (key, label, mode) in enumerate(labels):
            rect = pygame.Rect(20 + index * 151, 572, 144, 34)
            active = self.mode == mode and mode != "delete_vertex"
            self._button(screen, key, label, rect, font, active=active)

    def _draw_sidebar(self, screen: pygame.Surface) -> None:
        font = self._font(20)
        tab_names = (
            ("phase", "Fase"),
            ("floor", "Andar"),
            ("items", "Itens"),
            ("exit", "Saida"),
            ("objectives", "Objet."),
        )
        for index, (key, label) in enumerate(tab_names):
            rect = pygame.Rect(640 + index * 60, 80, 59, 26)
            self._button(screen, f"tab:{key}", label, rect, self._font(18), active=self.tab == key)
        pygame.draw.rect(screen, PANEL, pygame.Rect(640, 112, 300, 490), border_radius=8)
        pygame.draw.rect(screen, PANEL_LIGHT, pygame.Rect(640, 112, 300, 490), width=2, border_radius=8)
        if self.tab == "phase":
            self._draw_phase_tab(screen)
        elif self.tab == "floor":
            self._draw_floor_tab(screen)
        elif self.tab == "items":
            self._draw_items_tab(screen)
        elif self.tab == "exit":
            self._draw_exit_tab(screen)
        else:
            self._draw_objectives_tab(screen)

    def _draw_phase_tab(self, screen: pygame.Surface) -> None:
        fields = (
            ("id", "ID"),
            ("number", "Numero"),
            ("name", "Nome"),
            ("challenge_type", "Desafio"),
            ("completion", "Pontos conclusao"),
        )
        for index, (key, label) in enumerate(fields):
            self._draw_field(screen, key, label, pygame.Rect(652, 128 + index * 52, 276, 42))
        self._draw_json_button(
            screen,
            "challenge_parameters",
            "Parametros do desafio",
            pygame.Rect(652, 394, 276, 60),
        )
        known = ", ".join(sorted(ChallengeRegistry.types()))
        note = self._font(18).render(f"Tipos: {known}", True, MUTED)
        screen.blit(note, (652, 470))

    def _draw_floor_tab(self, screen: pygame.Surface) -> None:
        font = self._font(22)
        selected = self.selected_vertex
        text = f"Andar selecionado: {selected if selected is not None else 'nenhum'}"
        screen.blit(font.render(text, True, TEXT), (654, 136))
        if selected is None:
            screen.blit(font.render("Adicione um andar no grafo.", True, MUTED), (654, 174))
            return
        is_start = selected == self.config.get("start_floor")
        is_exit = selected == self.config.get("exit_floor")
        self._button(screen, "set_start", "Definir como inicio" if not is_start else "Inicio definido", pygame.Rect(652, 182, 276, 38), font, active=is_start)
        self._button(screen, "set_exit", "Definir como saida" if not is_exit else "Saida definida", pygame.Rect(652, 230, 276, 38), font, active=is_exit)
        items_here = [item.get("name", item.get("id", "item")) for item in self.items if item.get("floor") == selected]
        screen.blit(font.render("Itens neste andar:", True, TEXT), (654, 298))
        for index, name in enumerate(items_here[:8]):
            screen.blit(self._font(19).render(f"- {name}", True, MUTED), (660, 326 + index * 23))
        if not items_here:
            screen.blit(self._font(19).render("Nenhum item (permitido).", True, MUTED), (660, 326))

    def _draw_items_tab(self, screen: pygame.Surface) -> None:
        font = self._font(19)
        self._button(screen, "add_item", "Adicionar item", pygame.Rect(652, 122, 132, 32), font)
        self._button(screen, "remove_item", "Remover", pygame.Rect(792, 122, 136, 32), font)
        visible_items = self.items[self.item_list_offset : self.item_list_offset + 6]
        for offset, item in enumerate(visible_items):
            index = self.item_list_offset + offset
            rect = pygame.Rect(652, 160 + offset * 29, 276, 26)
            self._item_rects.append((index, rect))
            selected = index == self.selected_item
            pygame.draw.rect(screen, ACCENT_DARK if selected else PANEL_LIGHT, rect, border_radius=4)
            label = f"{item.get('id', '?')}  / andar {item.get('floor', '?')}  / {item.get('type', '?')}"
            screen.blit(font.render(label[:35], True, TEXT), (rect.x + 6, rect.y + 5))
        if len(self.items) > 6:
            screen.blit(font.render("Use a roda do mouse para percorrer itens.", True, MUTED), (652, 340))
        if self.selected_item is None or self.selected_item >= len(self.items):
            screen.blit(font.render("Selecione ou adicione um item.", True, MUTED), (652, 368))
            return
        item = self.items[self.selected_item]
        for index, (key, label) in enumerate(
            (("item_id", "ID"), ("item_name", "Nome"), ("item_floor", "Andar"), ("item_type", "Tipo"), ("item_score", "Pontos"))
        ):
            self._draw_field(screen, key, label, pygame.Rect(652, 366 + index * 43, 276, 36), item=item)
        is_key = bool(item.get("key", item.get("type") == "key"))
        self._button(screen, "toggle_key", f"Chave: {'sim' if is_key else 'nao'}", pygame.Rect(652, 588, 276, 28), font, active=is_key)

    def _draw_exit_tab(self, screen: pygame.Surface) -> None:
        font = self._font(19)
        screen.blit(font.render("Chaves exigidas na saida:", True, TEXT), (652, 126))
        requirements = self.config.get("exit_requirements", {})
        required_keys = requirements.get("keys", []) if isinstance(requirements, dict) else []
        key_items = [
            item
            for item in self.items
            if bool(item.get("key", item.get("type") == "key"))
        ]
        if not key_items:
            screen.blit(font.render("Marque um item como chave na aba Itens.", True, MUTED), (652, 154))
        for index, item in enumerate(key_items[:6]):
            item_id = item.get("id", "")
            checked = item_id in required_keys
            rect = pygame.Rect(652, 156 + index * 30, 276, 27)
            self._button(
                screen,
                f"exit_key:{item_id}",
                f"{'[x]' if checked else '[ ]'} {item.get('name', item_id)}",
                rect,
                self._font(18),
                active=checked,
            )
        challenge = self.config.get("challenge", {})
        challenge_type = challenge.get("type") if isinstance(challenge, dict) else None
        challenge_id = None
        if challenge_type in ChallengeRegistry.types():
            challenge_id = ChallengeRegistry.completion_id(challenge_type)
        required_challenges = (
            requirements.get("challenges", [])
            if isinstance(requirements, dict)
            else []
        )
        if challenge_id is not None:
            self._button(
                screen,
                "toggle_required_challenge",
                f"Exigir desafio: {'sim' if challenge_id in required_challenges else 'nao'}",
                pygame.Rect(652, 352, 276, 34),
                font,
                active=challenge_id in required_challenges,
            )
        self._draw_json_button(
            screen,
            "connection_requirements",
            "Bloqueios de conexao (JSON)",
            pygame.Rect(652, 408, 276, 78),
        )
        screen.blit(font.render("Valide as regras antes de exportar.", True, MUTED), (652, 510))

    def _draw_objectives_tab(self, screen: pygame.Surface) -> None:
        font = self._font(18)
        self._button(screen, "add_objective", "Adicionar objetivo", pygame.Rect(652, 122, 160, 32), font)
        self._button(screen, "remove_objective", "Remover", pygame.Rect(820, 122, 108, 32), font)
        visible = self.objectives[self.objective_list_offset : self.objective_list_offset + 5]
        for offset, objective in enumerate(visible):
            index = self.objective_list_offset + offset
            rect = pygame.Rect(652, 160 + offset * 27, 276, 24)
            self._objective_rects.append((index, rect))
            selected = index == self.selected_objective
            pygame.draw.rect(screen, ACCENT_DARK if selected else PANEL_LIGHT, rect, border_radius=4)
            label = f"{objective.get('id', '?')} / {objective.get('type', '?')}"
            screen.blit(font.render(label[:38], True, TEXT), (rect.x + 6, rect.y + 4))
        if not self.objectives:
            screen.blit(font.render("Nenhum objetivo opcional.", True, MUTED), (652, 168))
        screen.blit(self._font(16).render("Roda: percorrer objetivos.", True, MUTED), (652, 298))
        screen.blit(self._font(16).render("Tipos: visit_floor, collect_all_bonus,", True, MUTED), (652, 313))
        screen.blit(self._font(16).render("return_to_start", True, MUTED), (652, 328))
        objective = self._selected_objective_config()
        if objective is None:
            screen.blit(font.render("Objetivos nao sao obrigatorios.", True, MUTED), (652, 326))
            return
        fields = (
            ("objective_id", "ID"),
            ("objective_name", "Nome"),
            ("objective_description", "Descricao"),
            ("objective_type", "Tipo"),
            ("objective_floor", "Andar (visit_floor)"),
            ("objective_reward", "Recompensa"),
        )
        for index, (key, label) in enumerate(fields):
            self._draw_field(
                screen,
                key,
                label,
                pygame.Rect(652, 346 + index * 40, 276, 38),
                objective=objective,
            )

    def _draw_field(
        self,
        screen: pygame.Surface,
        key: str,
        label: str,
        rect: pygame.Rect,
        item: dict[str, Any] | None = None,
        objective: dict[str, Any] | None = None,
    ) -> None:
        font = self._font(18)
        value = self._field_value(key, item, objective)
        screen.blit(font.render(label, True, MUTED), (rect.x, rect.y))
        box = pygame.Rect(rect.x, rect.y + 17, rect.width, rect.height - 17)
        self._field_rects[key] = box
        pygame.draw.rect(screen, PANEL_LIGHT, box, border_radius=4)
        if self.focused_field == key:
            pygame.draw.rect(screen, ACCENT, box, width=2, border_radius=4)
            shown = self.field_buffer
        else:
            shown = str(value)
        screen.blit(font.render(shown[:34], True, TEXT), (box.x + 6, box.y + 4))

    def _field_value(
        self,
        key: str,
        item: dict[str, Any] | None,
        objective: dict[str, Any] | None = None,
    ) -> str:
        if key == "id":
            return str(self.config.get("id", ""))
        if key == "number":
            return str(self.config.get("number", ""))
        if key == "name":
            return str(self.config.get("name", ""))
        if key == "challenge_type":
            challenge = self.config.get("challenge", {})
            return str(challenge.get("type", "")) if isinstance(challenge, dict) else ""
        if key == "completion":
            rewards = self.config.get("rewards", {})
            return str(rewards.get("completion", 300)) if isinstance(rewards, dict) else "300"
        item_fields = {
            "item_id": "id",
            "item_name": "name",
            "item_floor": "floor",
            "item_type": "type",
            "item_score": "score",
        }
        if key in item_fields and item is not None:
            return str(item.get(item_fields[key], ""))
        objective_fields = {
            "objective_id": "id",
            "objective_name": "name",
            "objective_description": "description",
            "objective_type": "type",
            "objective_floor": "floor",
            "objective_reward": "reward",
        }
        if key in objective_fields and objective is not None:
            value = objective.get(objective_fields[key], "")
            return "" if value is None else str(value)
        return ""

    def _draw_json_button(
        self, screen: pygame.Surface, key: str, label: str, rect: pygame.Rect
    ) -> None:
        font = self._font(19)
        pygame.draw.rect(screen, PANEL_LIGHT, rect, border_radius=5)
        pygame.draw.rect(screen, ACCENT_DARK, rect, width=1, border_radius=5)
        screen.blit(font.render(label, True, TEXT), (rect.x + 8, rect.y + 7))
        value = self._json_field_value(key)
        summary = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        screen.blit(font.render(summary[:34], True, MUTED), (rect.x + 8, rect.y + 34))
        self._buttons[f"json:{key}"] = rect

    def _json_field_value(self, key: str) -> Any:
        if key == "challenge_parameters":
            challenge = self.config.get("challenge", {})
            return {k: v for k, v in challenge.items() if k != "type"} if isinstance(challenge, dict) else {}
        return self.config.get(key, {} if key == "exit_requirements" else [])

    def _button(
        self,
        screen: pygame.Surface,
        key: str,
        label: str,
        rect: pygame.Rect,
        font: pygame.font.Font,
        active: bool = False,
    ) -> None:
        self._buttons[key] = rect
        fill = ACCENT_DARK if active else PANEL
        pygame.draw.rect(screen, fill, rect, border_radius=6)
        pygame.draw.rect(screen, ACCENT_DARK, rect, width=1, border_radius=6)
        text = font.render(label, True, TEXT)
        screen.blit(text, text.get_rect(center=rect.center))

    def _draw_path_dialog(self, screen: pygame.Surface) -> None:
        rect = pygame.Rect(145, 245, 670, 150)
        pygame.draw.rect(screen, PANEL, rect, border_radius=10)
        pygame.draw.rect(screen, ACCENT, rect, width=2, border_radius=10)
        font = self._font(24)
        label = "Caminho do arquivo (Enter confirma, Esc cancela):"
        screen.blit(font.render(label, True, TEXT), (rect.x + 18, rect.y + 18))
        field = pygame.Rect(rect.x + 18, rect.y + 62, rect.width - 36, 40)
        pygame.draw.rect(screen, PANEL_LIGHT, field, border_radius=5)
        shown = self.path_buffer
        max_chars = 74
        screen.blit(font.render(shown[-max_chars:], True, TEXT), (field.x + 8, field.y + 9))

    def _draw_json_dialog(self, screen: pygame.Surface) -> None:
        rect = pygame.Rect(100, 245, 760, 150)
        pygame.draw.rect(screen, PANEL, rect, border_radius=10)
        pygame.draw.rect(screen, ACCENT, rect, width=2, border_radius=10)
        font = self._font(24)
        field = self.focused_field.split(":", 1)[1]
        screen.blit(
            font.render(f"JSON: {field} (Ctrl+A limpa, Enter aplica, Esc cancela)", True, TEXT),
            (rect.x + 18, rect.y + 18),
        )
        input_rect = pygame.Rect(rect.x + 18, rect.y + 62, rect.width - 36, 40)
        pygame.draw.rect(screen, PANEL_LIGHT, input_rect, border_radius=5)
        screen.blit(font.render(self.field_buffer[-96:], True, TEXT), (input_rect.x + 8, input_rect.y + 9))

    def _draw_overwrite_dialog(self, screen: pygame.Surface) -> None:
        rect = pygame.Rect(245, 245, 470, 150)
        pygame.draw.rect(screen, PANEL, rect, border_radius=10)
        pygame.draw.rect(screen, WARNING, rect, width=2, border_radius=10)
        font = self._font(24)
        screen.blit(font.render("O arquivo ja existe. Sobrescrever?", True, TEXT), (rect.x + 20, rect.y + 24))
        screen.blit(font.render(str(self.pending_overwrite)[-55:], True, MUTED), (rect.x + 20, rect.y + 55))
        self._button(screen, "overwrite_yes", "Sobrescrever", pygame.Rect(rect.x + 48, rect.y + 94, 160, 38), font)
        self._button(screen, "overwrite_no", "Cancelar", pygame.Rect(rect.x + 256, rect.y + 94, 160, 38), font)

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.KEYDOWN:
            if self.path_dialog is not None:
                self._handle_path_key(event)
                return False
            if self.focused_field is not None:
                if event.key == pygame.K_ESCAPE:
                    self.focused_field = None
                    return False
                if event.key == pygame.K_a and getattr(event, "mod", 0) & pygame.KMOD_CTRL:
                    self.field_buffer = ""
                    return False
                if event.key == pygame.K_RETURN:
                    self._commit_field()
                    return False
                if event.key == pygame.K_BACKSPACE:
                    self.field_buffer = self.field_buffer[:-1]
                elif getattr(event, "unicode", "") and event.unicode.isprintable():
                    self.field_buffer += event.unicode
                return False
            if event.key == pygame.K_ESCAPE:
                return True
            return False
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
            return False
        if event.type == pygame.MOUSEMOTION and self.dragging and self.selected_vertex is not None:
            if self.canvas_rect.collidepoint(event.pos):
                self.move_vertex(self.selected_vertex, event.pos)
            return False
        if event.type == pygame.MOUSEWHEEL and self.tab in ("items", "objectives"):
            collection = self.items if self.tab == "items" else self.objectives
            page_size = 6 if self.tab == "items" else 5
            max_offset = max(0, len(collection) - page_size)
            if self.tab == "items":
                self.item_list_offset = min(
                    max(0, self.item_list_offset - event.y), max_offset
                )
            else:
                self.objective_list_offset = min(
                    max(0, self.objective_list_offset - event.y), max_offset
                )
            return False
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return False
        if self.pending_overwrite is not None:
            if self._buttons.get("overwrite_yes", pygame.Rect(0, 0, 0, 0)).collidepoint(event.pos):
                self._confirm_overwrite()
            elif self._buttons.get("overwrite_no", pygame.Rect(0, 0, 0, 0)).collidepoint(event.pos):
                self.pending_overwrite = None
                self._set_status("Exportacao cancelada.")
            return False
        if self.path_dialog is not None:
            return False
        if self.focused_field is not None and not self._commit_field():
            return False
        for key, rect in self._field_rects.items():
            if rect.collidepoint(event.pos):
                self._begin_edit(key)
                return False
        for key, rect in self._buttons.items():
            if rect.collidepoint(event.pos):
                self._activate_button(key)
                if getattr(self, "_back_requested", False):
                    self._back_requested = False
                    return True
                return False
        for index, rect in self._item_rects:
            if rect.collidepoint(event.pos):
                self.selected_item = index
                return False
        for index, rect in self._objective_rects:
            if rect.collidepoint(event.pos):
                self.selected_objective = index
                return False
        if self.canvas_rect.collidepoint(event.pos):
            self._canvas_click(event.pos)
        else:
            self.edge_origin = None
        return False

    def _canvas_click(self, position: tuple[int, int]) -> None:
        if self.mode == "add_vertex":
            self.add_vertex(position)
            return
        vertex = self._vertex_at(position)
        if self.mode == "add_edge":
            if vertex is None:
                self._set_status("Selecione um andar para criar a conexao.", error=True)
            elif self.edge_origin is None:
                self.edge_origin = vertex
                self.selected_vertex = vertex
                self._set_status(f"Andar {vertex} selecionado; selecione o outro extremo.")
            else:
                first = self.edge_origin
                self.edge_origin = None
                self.selected_vertex = vertex
                try:
                    self.add_edge(first, vertex)
                except ValueError as error:
                    self._set_status(str(error), error=True)
            return
        if self.mode == "delete_edge":
            edge = self._edge_at(position)
            if edge is None:
                self._set_status("Clique sobre uma conexao para remove-la.", error=True)
            else:
                self.remove_edge(*edge)
            return
        self.selected_vertex = vertex
        if vertex is not None:
            self.dragging = True
            self.tab = "floor"
            self._set_status(f"Andar {vertex} selecionado.")

    def _vertex_at(self, position: tuple[int, int]) -> int | None:
        return next(
            (
                vertex
                for vertex, point in self.positions.items()
                if math.dist(position, point) <= 25
            ),
            None,
        )

    def _edge_at(self, position: tuple[int, int]) -> tuple[int, int] | None:
        for edge in self.edges:
            if len(edge) < 2 or edge[0] not in self.positions or edge[1] not in self.positions:
                continue
            start = self.positions[edge[0]]
            end = self.positions[edge[1]]
            if self._distance_to_segment(position, start, end) <= 9:
                return edge[0], edge[1]
        return None

    @staticmethod
    def _distance_to_segment(
        point: tuple[int, int], start: tuple[int, int], end: tuple[int, int]
    ) -> float:
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        if dx == 0 and dy == 0:
            return math.dist(point, start)
        fraction = max(
            0.0,
            min(
                1.0,
                ((point[0] - start[0]) * dx + (point[1] - start[1]) * dy)
                / (dx * dx + dy * dy),
            ),
        )
        projection = (start[0] + fraction * dx, start[1] + fraction * dy)
        return math.dist(point, projection)

    def _begin_edit(self, key: str) -> None:
        self.focused_field = key
        item = self._selected_item_config()
        objective = self._selected_objective_config()
        self.field_buffer = self._field_value(key, item, objective)

    def _commit_field(self) -> bool:
        key = self.focused_field
        if key is None:
            return True
        value = self.field_buffer.strip()
        try:
            if key.startswith("json:"):
                field = key.split(":", 1)[1]
                parsed = json.loads(value)
                if field == "challenge_parameters":
                    if not isinstance(parsed, dict):
                        raise ValueError("Os parametros do desafio devem ser um objeto.")
                    challenge = self.config.get("challenge", {})
                    if not isinstance(challenge, dict):
                        raise ValueError("A configuracao do desafio deve ser um objeto.")
                    challenge_type = challenge.get("type")
                    self.config["challenge"] = {
                        "type": challenge_type,
                        **parsed,
                    }
                else:
                    expected = dict if field == "exit_requirements" else list
                    if not isinstance(parsed, expected):
                        raise ValueError(
                            "O campo deve conter um objeto JSON."
                            if expected is dict
                            else "O campo deve conter uma lista JSON."
                        )
                    self.config[field] = parsed
            elif key == "id":
                self.config["id"] = value
            elif key == "number":
                self.config["number"] = int(value)
            elif key == "name":
                self.config["name"] = value
            elif key == "challenge_type":
                challenge = self.config.setdefault("challenge", {})
                if not isinstance(challenge, dict):
                    raise ValueError("A configuracao do desafio deve ser um objeto.")
                old_type = challenge.get("type")
                old_completion_id = (
                    ChallengeRegistry.completion_id(old_type)
                    if old_type in ChallengeRegistry.types()
                    else None
                )
                challenge["type"] = value
                if old_completion_id is not None:
                    requirements = self.config.get("exit_requirements")
                    if (
                        isinstance(requirements, dict)
                        and isinstance(requirements.get("challenges"), list)
                        and old_completion_id in requirements["challenges"]
                    ):
                        requirements["challenges"].remove(old_completion_id)
                        if value in ChallengeRegistry.types():
                            requirements["challenges"].append(
                                ChallengeRegistry.completion_id(value)
                            )
            elif key == "completion":
                rewards = self.config.setdefault("rewards", {})
                if not isinstance(rewards, dict):
                    raise ValueError("A configuracao de recompensas deve ser um objeto.")
                rewards["completion"] = int(value)
            elif key.startswith("objective_"):
                objective_fields = {
                    "objective_id": ("id", str),
                    "objective_name": ("name", str),
                    "objective_description": ("description", str),
                    "objective_type": ("type", str),
                    "objective_floor": ("floor", int),
                    "objective_reward": ("reward", int),
                }
                if key not in objective_fields or self.selected_objective is None:
                    raise ValueError("O objetivo selecionado nao pode ser editado.")
                field, converter = objective_fields[key]
                converted: Any = (
                    None if key == "objective_floor" and not value else converter(value)
                )
                self.objectives[self.selected_objective][field] = converted
            else:
                item_fields = {
                    "item_id": ("id", str),
                    "item_name": ("name", str),
                    "item_floor": ("floor", int),
                    "item_type": ("type", str),
                    "item_score": ("score", int),
                }
                if key not in item_fields or self.selected_item is None:
                    raise ValueError("O campo selecionado nao pode ser editado.")
                field, converter = item_fields[key]
                item = self.items[self.selected_item]
                previous_id = item.get("id")
                self.update_item(self.selected_item, **{field: converter(value)})
                if key == "item_id" and isinstance(previous_id, str):
                    self._replace_item_reference(previous_id, value)
            self.focused_field = None
            self._set_status("Alteracao aplicada.")
            return True
        except (TypeError, ValueError) as error:
            self._set_status(f"Valor invalido: {error}", error=True)
            return False

    def _selected_item_config(self) -> dict[str, Any] | None:
        if self.selected_item is None or self.selected_item >= len(self.items):
            return None
        return self.items[self.selected_item]

    def _selected_objective_config(self) -> dict[str, Any] | None:
        if (
            self.selected_objective is None
            or self.selected_objective >= len(self.objectives)
        ):
            return None
        return self.objectives[self.selected_objective]

    def _activate_button(self, key: str) -> None:
        if key.startswith("tab:"):
            self.tab = key.split(":", 1)[1]
        elif key.startswith("json:"):
            field = key.split(":", 1)[1]
            self.focused_field = f"json:{field}"
            self.field_buffer = json.dumps(
                self._json_field_value(field), ensure_ascii=False, separators=(",", ":")
            )
        elif key == "new":
            self.new_level()
        elif key == "open":
            self._open_path_dialog()
        elif key in ("save", "export"):
            default_path = (
                self.active_path
                if key == "save" and self.active_path is not None
                else DEFAULT_LEVELS_DIR / f"{self.config.get('id', 'nova-fase')}.json"
            )
            self.path_dialog = key
            self.path_buffer = str(default_path)
        elif key == "validate":
            try:
                self.validate()
            except ValueError:
                pass
        elif key == "back":
            self._set_status("Retornando ao menu.")
            self._back_requested = True
        elif key == "add_vertex":
            self.mode = "add_vertex"
            self._set_status("Clique na area do grafo para posicionar o novo andar.")
        elif key == "add_edge":
            self.mode = "add_edge"
            self.edge_origin = None
            self._set_status("Selecione dois andares para criar uma conexao.")
        elif key == "delete_edge":
            self.mode = "delete_edge"
            self._set_status("Clique sobre uma conexao para remove-la.")
        elif key == "delete_vertex":
            if self.selected_vertex is None:
                self._set_status("Selecione um andar antes de remove-lo.", error=True)
            else:
                self.remove_vertex(self.selected_vertex)
        elif key == "set_start" and self.selected_vertex is not None:
            self.config["start_floor"] = self.selected_vertex
            self._set_status(f"Andar {self.selected_vertex} definido como inicio.")
        elif key == "set_exit" and self.selected_vertex is not None:
            self.config["exit_floor"] = self.selected_vertex
            self._set_status(f"Andar {self.selected_vertex} definido como saida.")
        elif key == "add_item":
            try:
                self.add_item()
            except ValueError as error:
                self._set_status(str(error), error=True)
        elif key == "remove_item":
            if self.selected_item is None:
                self._set_status("Selecione um item para remove-lo.", error=True)
            else:
                self.remove_item(self.selected_item)
        elif key == "toggle_key":
            item = self._selected_item_config()
            if item is not None:
                item["key"] = not bool(item.get("key", item.get("type") == "key"))
                if not item["key"] and isinstance(item.get("id"), str):
                    self._remove_item_references({item["id"]})
                self._set_status(f"Chave definida como {'sim' if item['key'] else 'nao'}.")
        elif key.startswith("exit_key:"):
            self._toggle_exit_key(key.split(":", 1)[1])
        elif key == "toggle_required_challenge":
            self._toggle_required_challenge()
        elif key == "add_objective":
            self.add_objective()
        elif key == "remove_objective":
            if self.selected_objective is None:
                self._set_status("Selecione um objetivo para remove-lo.", error=True)
            else:
                self.remove_objective(self.selected_objective)

    def _toggle_exit_key(self, item_id: str) -> None:
        requirements = self.config.setdefault("exit_requirements", {})
        if not isinstance(requirements, dict):
            self._set_status("Requisitos da saida devem ser um objeto.", error=True)
            return
        keys = requirements.setdefault("keys", [])
        if not isinstance(keys, list):
            self._set_status("As chaves exigidas devem ser uma lista.", error=True)
            return
        if item_id in keys:
            keys.remove(item_id)
        else:
            keys.append(item_id)
        self._set_status(f"Requisito de chave atualizado: {item_id}.")

    def _toggle_required_challenge(self) -> None:
        challenge = self.config.get("challenge", {})
        challenge_type = challenge.get("type") if isinstance(challenge, dict) else None
        if challenge_type not in ChallengeRegistry.types():
            self._set_status("Selecione um tipo de desafio valido.", error=True)
            return
        challenge_id = ChallengeRegistry.completion_id(challenge_type)
        requirements = self.config.setdefault("exit_requirements", {})
        if not isinstance(requirements, dict):
            self._set_status("Requisitos da saida devem ser um objeto.", error=True)
            return
        challenges = requirements.setdefault("challenges", [])
        if not isinstance(challenges, list):
            self._set_status("Os desafios exigidos devem ser uma lista.", error=True)
            return
        if challenge_id in challenges:
            challenges.remove(challenge_id)
        else:
            challenges.append(challenge_id)
        self._set_status(f"Requisito de desafio atualizado: {challenge_id}.")

    def _open_path_dialog(self) -> None:
        self.path_dialog = "open"
        self.path_buffer = str(self.active_path) if self.active_path is not None else ""

    def _handle_path_key(self, event: pygame.event.Event) -> None:
        if event.key == pygame.K_ESCAPE:
            self.path_dialog = None
            self._set_status("Operacao cancelada.")
        elif event.key == pygame.K_a and getattr(event, "mod", 0) & pygame.KMOD_CTRL:
            self.path_buffer = ""
        elif event.key == pygame.K_BACKSPACE:
            self.path_buffer = self.path_buffer[:-1]
        elif event.key == pygame.K_RETURN:
            mode = self.path_dialog
            target = self.path_buffer.strip().strip('"')
            self.path_dialog = None
            if not target:
                self._set_status("Informe o caminho do arquivo.", error=True)
                return
            if mode == "open":
                try:
                    self.import_file(target)
                except (OSError, ValueError) as error:
                    self._set_status(str(error), error=True)
            else:
                try:
                    self.export_file(target)
                except FileExistsError as error:
                    self.pending_overwrite = Path(error.args[0])
                except ValueError as error:
                    self._set_status(str(error), error=True)
        elif getattr(event, "unicode", "") and event.unicode.isprintable():
            self.path_buffer += event.unicode

    def _confirm_overwrite(self) -> None:
        destination = self.pending_overwrite
        self.pending_overwrite = None
        if destination is None:
            return
        try:
            self.export_file(destination, overwrite=True)
        except ValueError as error:
            self._set_status(str(error), error=True)

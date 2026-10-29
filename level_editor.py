"""Editor visual de fases compativeis com o formato JSON do jogo."""

from __future__ import annotations

import copy
import json
import math
from pathlib import Path
from typing import Any, Callable

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
CHALLENGE_LABELS = {
    "collect_and_exit": "Coleta e saida",
    "hamilton": "Hamilton",
    "economic": "Economic",
    "euler": "Euler",
    "final": "Desafio final",
}


def new_level_config(levels_dir: str | Path | None = None) -> dict[str, Any]:
    existing_levels = LevelManager.discover_levels(levels_dir).levels
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

    def __init__(
        self,
        levels_dir: str | Path | None = None,
        on_export: Callable[[Path], None] | None = None,
    ) -> None:
        if not pygame.font.get_init():
            pygame.font.init()
        self._fonts = {
            size: pygame.font.Font(None, size)
            for size in (16, 18, 19, 20, 21, 22, 23, 24, 25)
        }
        self.levels_dir = Path(levels_dir) if levels_dir is not None else DEFAULT_LEVELS_DIR
        self.config = new_level_config(self.levels_dir)
        self.on_export = on_export
        self.positions: dict[int, tuple[int, int]] = {}
        self.active_path: Path | None = None
        self.active_identifier: str | None = None
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
        self.cursor_index = 0
        self.selection_anchor: int | None = None
        self.text_scroll_px = 0
        self.dropdown_open = False
        self.challenge_parameter_cache: dict[str, dict[str, Any]] = {}
        self.selected_edge: tuple[int, int] | None = None
        self._edge_rects: list[tuple[tuple[int, int], pygame.Rect]] = []
        self.path_dialog: str | None = None
        self.path_buffer = ""
        self.path_cursor = 0
        self.pending_overwrite: Path | None = None
        self._back_requested = False
        self._buttons: dict[str, pygame.Rect] = {}
        self._field_rects: dict[str, pygame.Rect] = {}
        self._item_rects: list[tuple[int, pygame.Rect]] = []
        self._objective_rects: list[tuple[int, pygame.Rect]] = []
        self.canvas_rect = pygame.Rect(20, 112, 600, 450)
        self._layout_positions()
        self._cache_current_challenge_parameters()

    def _font(self, size: int) -> pygame.font.Font:
        return self._fonts[size]

    def _cache_current_challenge_parameters(self) -> None:
        challenge = self.config.get("challenge")
        if isinstance(challenge, dict) and isinstance(challenge.get("type"), str):
            self.challenge_parameter_cache[challenge["type"]] = {
                key: copy.deepcopy(value)
                for key, value in challenge.items()
                if key != "type"
            }

    @property
    def vertices(self) -> list[int]:
        return self.config["graph"]["vertices"]

    @property
    def edges(self) -> list[list[Any]]:
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
        self.config = new_level_config(self.levels_dir)
        self.active_path = None
        self.active_identifier = None
        self.selected_vertex = 1
        self.selected_item = None
        self.item_list_offset = 0
        self.selected_objective = None
        self.objective_list_offset = 0
        self.tab = "phase"
        self.edge_origin = None
        self.mode = "select"
        self.focused_field = None
        self.dropdown_open = False
        self.selected_edge = None
        self.challenge_parameter_cache = {}
        self._cache_current_challenge_parameters()
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
        identifier = self.config.get("id")
        self.active_identifier = identifier if isinstance(identifier, str) else None
        self.edge_origin = None
        self.mode = "select"
        self.focused_field = None
        self.dropdown_open = False
        self.selected_edge = None
        self.challenge_parameter_cache = {}
        self._cache_current_challenge_parameters()
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
        if destination.parent.resolve() == self.levels_dir.resolve():
            for existing in LevelManager.discover_levels(self.levels_dir).levels:
                if (
                    self.active_path is not None
                    and self.active_path.resolve() == destination.resolve()
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
        identifier = self.config.get("id")
        self.active_identifier = identifier if isinstance(identifier, str) else None
        if self.on_export is not None:
            self.on_export(destination)
        self._set_status(f"Fase exportada para {destination}.")
        return destination

    def add_vertex(self, position: tuple[int, int] | None = None) -> int:
        vertex = len(self.vertices) + 1
        while vertex in self.vertices:
            vertex += 1
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
        self.edges.append([first, second, 1] if self._is_economic() else [first, second])
        self._set_status(f"Conexao criada: {first} - {second}.")

    def remove_edge(self, first: int, second: int) -> None:
        for index, edge in enumerate(self.edges):
            if set(edge[:2]) == {first, second}:
                del self.edges[index]
                self.selected_edge = None
                self._set_status(f"Conexao removida: {first} - {second}.")
                return
        raise ValueError("A conexao selecionada nao existe.")

    def remove_vertex(self, vertex: int) -> None:
        if vertex not in self.vertices:
            raise ValueError(f"Andar inexistente: {vertex}.")
        if len(self.vertices) == 1:
            raise ValueError("A fase deve manter ao menos um andar.")
        previous_vertices = sorted(self.vertices)
        retained_vertices = [floor for floor in previous_vertices if floor != vertex]
        remapping = {
            old_floor: new_floor
            for new_floor, old_floor in enumerate(retained_vertices, start=1)
        }

        def remap_floor(floor: Any) -> int:
            if floor in remapping:
                return remapping[floor]
            if not remapping:
                raise ValueError("A fase deve manter ao menos um andar.")
            if type(floor) is not int:
                raise ValueError(f"Referencia de andar invalida: {floor!r}.")
            nearest_floor = min(
                retained_vertices,
                key=lambda candidate: (abs(candidate - floor), candidate),
            )
            return remapping[nearest_floor]

        new_edges = [
            [remapping[edge[0]], remapping[edge[1]], *edge[2:]]
            for edge in self.edges
            if vertex not in edge[:2]
        ]
        removed_items = [
            item for item in self.items if item.get("floor") == vertex
        ]
        removed_item_ids = {item.get("id") for item in removed_items}
        new_items = [
            item for item in self.items if item.get("floor") != vertex
        ]
        new_items = copy.deepcopy(new_items)
        for item in new_items:
            item["floor"] = remap_floor(item["floor"])

        new_start = remap_floor(self.config.get("start_floor"))
        new_exit = remap_floor(self.config.get("exit_floor"))

        challenge = copy.deepcopy(self.config.get("challenge"))
        if isinstance(challenge, dict):
            for key in ("destination_floor", "end_floor", "return_floor"):
                if key in challenge:
                    challenge[key] = remap_floor(challenge[key])
            reference_trail = challenge.get("reference_trail")
            if isinstance(reference_trail, list):
                challenge["reference_trail"] = [
                    remapping[floor]
                    for floor in reference_trail
                    if floor in remapping
                ]

        requirements = self.config.get("connection_requirements", [])
        new_requirements = copy.deepcopy(requirements)
        if isinstance(requirements, list):
            new_requirements = []
            for requirement in requirements:
                if not isinstance(requirement, dict):
                    new_requirements.append(copy.deepcopy(requirement))
                    continue
                first = requirement.get("from")
                second = requirement.get("to")
                if vertex in (first, second):
                    continue
                remapped_requirement = copy.deepcopy(requirement)
                if "from" in remapped_requirement:
                    remapped_requirement["from"] = remap_floor(first)
                if "to" in remapped_requirement:
                    remapped_requirement["to"] = remap_floor(second)
                keys = remapped_requirement.get("keys")
                if isinstance(keys, list):
                    remapped_requirement["keys"] = [
                        key_id for key_id in keys if key_id not in removed_item_ids
                    ]
                new_requirements.append(remapped_requirement)

        new_objectives = copy.deepcopy(self.objectives)
        for objective in new_objectives:
            if isinstance(objective, dict) and objective.get("floor") is not None:
                objective["floor"] = remap_floor(objective["floor"])

        new_exit_requirements = copy.deepcopy(
            self.config.get("exit_requirements", {})
        )
        if (
            isinstance(new_exit_requirements, dict)
            and isinstance(new_exit_requirements.get("keys"), list)
        ):
            new_exit_requirements["keys"] = [
                key_id
                for key_id in new_exit_requirements["keys"]
                if key_id not in removed_item_ids
            ]

        graph = self.config["graph"]
        graph["vertices"] = list(remapping.values())
        graph["edges"] = new_edges
        self.config["items"] = new_items
        self.config["start_floor"] = new_start
        self.config["exit_floor"] = new_exit
        self.config["challenge"] = challenge
        self.config["connection_requirements"] = new_requirements
        self.config["optional_objectives"] = new_objectives
        self.config["exit_requirements"] = new_exit_requirements
        self._cache_current_challenge_parameters()

        old_positions = self.positions.copy()
        self.positions = {
            remapping[old_floor]: old_positions[old_floor]
            for old_floor in retained_vertices
            if old_floor in old_positions
        }
        self.vertices.sort()
        self.edges.sort(key=lambda edge: (edge[0], edge[1]))
        self.selected_vertex = (
            remapping.get(self.selected_vertex)
            if self.selected_vertex != vertex
            else (self.vertices[0] if self.vertices else None)
        )
        self.selected_edge = None
        self.edge_origin = None
        self.selected_item = None
        suffix = f" {len(removed_items)} item(ns) do andar tambem removido(s)." if removed_items else ""
        self._set_status(
            f"Andar {vertex} removido; os restantes foram renumerados.{suffix}"
        )

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
            selected = (
                self.selected_edge is not None
                and {first, second} == set(self.selected_edge)
            )
            pygame.draw.line(
                screen,
                WARNING if selected else ACCENT_DARK if self._is_economic() else MUTED,
                self.positions[first],
                self.positions[second],
                5 if selected else 3,
            )
            if self._is_economic():
                midpoint = (
                    (self.positions[first][0] + self.positions[second][0]) // 2,
                    (self.positions[first][1] + self.positions[second][1]) // 2,
                )
                cost = edge[2] if len(edge) > 2 else 1
                cost_text = f"{cost:g}" if isinstance(cost, (int, float)) else str(cost)
                label = self._font(18).render(cost_text, True, TEXT)
                background = pygame.Rect(
                    midpoint[0] - 14,
                    midpoint[1] - 11,
                    label.get_width() + 8,
                    label.get_height() + 4,
                )
                pygame.draw.rect(screen, BACKGROUND, background, border_radius=4)
                screen.blit(label, label.get_rect(center=background.center))
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
        if self._is_economic():
            hint = self._font(18).render("Clique em uma aresta para editar seu custo.", True, ACCENT)
            screen.blit(hint, (self.canvas_rect.x + 12, self.canvas_rect.y + 12))

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
        tab_names = [
            ("phase", "Fase"),
            ("floor", "Andar"),
            ("items", "Itens"),
            ("exit", "Saida"),
            ("objectives", "Objet."),
        ]
        if self._is_economic():
            tab_names.append(("edge", "Aresta"))
        tab_width = 50 if len(tab_names) == 6 else 59
        tab_step = 50 if len(tab_names) == 6 else 60
        for index, (key, label) in enumerate(tab_names):
            rect = pygame.Rect(640 + index * tab_step, 80, tab_width, 26)
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
        elif self.tab == "objectives":
            self._draw_objectives_tab(screen)
        else:
            self._draw_edge_tab(screen)

    def _draw_phase_tab(self, screen: pygame.Surface) -> None:
        fields = (
            ("id", "ID"),
            ("number", "Numero"),
            ("name", "Nome"),
            ("completion", "Pontos conclusao"),
        )
        for index, (key, label) in enumerate(fields):
            self._draw_field(screen, key, label, pygame.Rect(652, 128 + index * 48, 276, 40))
        challenge = self.config.get("challenge", {})
        current_type = challenge.get("type") if isinstance(challenge, dict) else ""
        label = CHALLENGE_LABELS.get(current_type, str(current_type))
        combo_rect = pygame.Rect(652, 326, 276, 34)
        self._button(
            screen,
            "challenge_combo",
            f"Desafio: {label}  v",
            combo_rect,
            self._font(19),
            active=self.dropdown_open,
        )
        self._draw_challenge_parameters(screen, 374)
        if self.dropdown_open:
            for index, challenge_type in enumerate(self._challenge_types()):
                rect = pygame.Rect(652, 361 + index * 30, 276, 28)
                self._button(
                    screen,
                    f"challenge:{challenge_type}",
                    CHALLENGE_LABELS.get(challenge_type, challenge_type),
                    rect,
                    self._font(18),
                    active=challenge_type == current_type,
                )

    def _draw_challenge_parameters(self, screen: pygame.Surface, top: int) -> None:
        challenge = self.config.get("challenge", {})
        challenge_type = challenge.get("type") if isinstance(challenge, dict) else None
        parameter_fields = {
            "hamilton": (("end_floor", "Andar final"),),
            "economic": (("destination_floor", "Andar destino"),),
            "euler": (("reference_trail", "Trilha de referencia"),),
            "final": (
                ("destination_floor", "Andar destino"),
                ("return_floor", "Andar de retorno"),
            ),
        }.get(challenge_type, ())
        if not parameter_fields:
            screen.blit(self._font(18).render("Sem parametros adicionais.", True, MUTED), (652, top + 8))
            return
        for index, (key, label) in enumerate(parameter_fields):
            self._draw_field(
                screen,
                f"challenge_param:{key}",
                label,
                pygame.Rect(652, top + index * 54, 276, 44),
                challenge=challenge,
            )

    def _challenge_types(self) -> tuple[str, ...]:
        preferred = ("collect_and_exit", "hamilton", "economic", "euler", "final")
        supported = ChallengeRegistry.types()
        return tuple(
            challenge_type
            for challenge_type in preferred
            if challenge_type in supported
        ) + tuple(sorted(supported - set(preferred)))

    def _is_economic(self) -> bool:
        challenge = self.config.get("challenge", {})
        return isinstance(challenge, dict) and challenge.get("type") == "economic"

    def _set_challenge_type(self, challenge_type: str) -> None:
        if challenge_type not in ChallengeRegistry.types():
            raise ValueError(f"Tipo de desafio desconhecido: {challenge_type!r}.")
        current = self.config.get("challenge", {})
        current_type = current.get("type") if isinstance(current, dict) else None
        current_parameters = (
            {key: copy.deepcopy(value) for key, value in current.items() if key != "type"}
            if isinstance(current, dict)
            else {}
        )
        if isinstance(current_type, str):
            self.challenge_parameter_cache[current_type] = current_parameters
        previous_completion_id = (
            ChallengeRegistry.completion_id(current_type)
            if isinstance(current_type, str)
            and current_type in ChallengeRegistry.types()
            else None
        )
        parameters = copy.deepcopy(
            self.challenge_parameter_cache.get(challenge_type, {})
        )
        allowed = ChallengeRegistry.allowed_fields(challenge_type) - {"type"}
        parameters = {
            key: value for key, value in parameters.items() if key in allowed
        }
        for key, value in current_parameters.items():
            if key in allowed:
                parameters[key] = value
        defaults = {
            "end_floor": self.config.get("exit_floor"),
            "destination_floor": self.config.get("exit_floor"),
            "return_floor": self.config.get("start_floor"),
            "reference_trail": [],
        }
        for key in allowed:
            if key in defaults:
                parameters.setdefault(key, defaults[key])
        self.config["challenge"] = {"type": challenge_type, **parameters}
        self.challenge_parameter_cache[challenge_type] = copy.deepcopy(parameters)
        if previous_completion_id is not None:
            requirements = self.config.get("exit_requirements")
            if (
                isinstance(requirements, dict)
                and isinstance(requirements.get("challenges"), list)
                and previous_completion_id in requirements["challenges"]
            ):
                requirements["challenges"].remove(previous_completion_id)
                new_completion_id = ChallengeRegistry.completion_id(challenge_type)
                if new_completion_id not in requirements["challenges"]:
                    requirements["challenges"].append(new_completion_id)
        if challenge_type == "economic":
            for edge in self.edges:
                if len(edge) == 2:
                    edge.append(1)
        elif self.mode == "edit_cost":
            self.mode = "select"
        self.dropdown_open = False
        self.selected_edge = None
        self._set_status(
            f"Desafio selecionado: {CHALLENGE_LABELS.get(challenge_type, challenge_type)}. "
            "Os parametros anteriores permanecem disponiveis ao voltar ao tipo."
        )

    def _edge_config(self, endpoints: tuple[int, int]) -> list[Any]:
        for edge in self.edges:
            if len(edge) >= 2 and {edge[0], edge[1]} == set(endpoints):
                return edge
        raise ValueError(f"A conexao {endpoints[0]}-{endpoints[1]} nao existe.")

    def _set_edge_cost(self, endpoints: tuple[int, int], value: str) -> None:
        try:
            cost = float(value)
        except ValueError as error:
            raise ValueError("O custo deve ser um numero valido.") from error
        if not math.isfinite(cost) or cost <= 0:
            raise ValueError("O custo da conexao deve ser finito e positivo.")
        edge = self._edge_config(endpoints)
        if len(edge) == 2:
            edge.append(cost)
        else:
            edge[2] = int(cost) if cost.is_integer() else cost
        self._set_status(f"Custo atualizado: {endpoints[0]}-{endpoints[1]} = {edge[2]}.")

    def _draw_edge_tab(self, screen: pygame.Surface) -> None:
        if not self._is_economic():
            screen.blit(self._font(19).render("Custos editaveis no desafio Economic.", True, MUTED), (652, 138))
            return
        self._button(
            screen,
            "mode:edit_cost",
            "Voltar a selecionar"
            if self.mode == "edit_cost"
            else "Editar custo das conexoes",
            pygame.Rect(652, 122, 276, 34),
            self._font(18),
            active=self.mode == "edit_cost",
        )
        if self.selected_edge is None:
            screen.blit(self._font(19).render("Selecione uma aresta no grafo.", True, MUTED), (652, 170))
            return
        first, second = self.selected_edge
        screen.blit(self._font(22).render(f"Conexao {first} - {second}", True, TEXT), (652, 170))
        edge = self._edge_config(self.selected_edge)
        cost = edge[2] if len(edge) > 2 else 1
        self._draw_field(
            screen,
            "edge_cost",
            "Custo positivo",
            pygame.Rect(652, 208, 276, 48),
            edge={"cost": cost},
        )
        screen.blit(self._font(18).render("Use um valor maior que zero.", True, MUTED), (652, 274))

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
        challenge: dict[str, Any] | None = None,
        edge: dict[str, Any] | None = None,
    ) -> None:
        font = self._font(18)
        value = self._field_value(key, item, objective, challenge, edge)
        screen.blit(font.render(label, True, MUTED), (rect.x, rect.y))
        box = pygame.Rect(rect.x, rect.y + 17, rect.width, rect.height - 17)
        self._field_rects[key] = box
        pygame.draw.rect(screen, PANEL_LIGHT, box, border_radius=4)
        if self.focused_field == key:
            pygame.draw.rect(screen, ACCENT, box, width=2, border_radius=4)
            text = self.field_buffer
            content_width = box.width - 14
            caret_x = self._font(18).size(text[: self.cursor_index])[0]
            if caret_x - self.text_scroll_px > content_width:
                self.text_scroll_px = caret_x - content_width + 2
            elif caret_x < self.text_scroll_px:
                self.text_scroll_px = caret_x
            text_surface = font.render(text, True, TEXT)
            clip = screen.get_clip()
            screen.set_clip(box.inflate(-10, -2))
            text_x = box.x + 6 - self.text_scroll_px
            if self.selection_anchor is not None and self.selection_anchor != self.cursor_index:
                selection_start, selection_end = sorted(
                    (self.selection_anchor, self.cursor_index)
                )
                left = self._font(18).size(text[:selection_start])[0]
                right = self._font(18).size(text[:selection_end])[0]
                selection_rect = pygame.Rect(
                    text_x + left,
                    box.y + 3,
                    max(1, right - left),
                    box.height - 6,
                )
                overlay = pygame.Surface(selection_rect.size, pygame.SRCALPHA)
                overlay.fill((*ACCENT_DARK, 150))
                screen.blit(overlay, selection_rect)
            screen.blit(text_surface, (text_x, box.y + 4))
            if pygame.time.get_ticks() % 1000 < 550:
                cursor_x = text_x + caret_x
                pygame.draw.line(
                    screen,
                    TEXT,
                    (cursor_x, box.y + 4),
                    (cursor_x, box.bottom - 4),
                    2,
                )
            screen.set_clip(clip)
        else:
            text = str(value)
            rendered = font.render(text, True, TEXT)
            clip = screen.get_clip()
            screen.set_clip(box.inflate(-10, -2))
            screen.blit(rendered, (box.x + 6, box.y + 4))
            screen.set_clip(clip)

    def _field_value(
        self,
        key: str,
        item: dict[str, Any] | None,
        objective: dict[str, Any] | None = None,
        challenge: dict[str, Any] | None = None,
        edge: dict[str, Any] | None = None,
    ) -> str:
        if key == "id":
            return str(self.config.get("id", ""))
        if key == "number":
            return str(self.config.get("number", ""))
        if key == "name":
            return str(self.config.get("name", ""))
        if key == "completion":
            rewards = self.config.get("rewards", {})
            return str(rewards.get("completion", 300)) if isinstance(rewards, dict) else "300"
        if key.startswith("challenge_param:") and challenge is not None:
            parameter = key.split(":", 1)[1]
            value = challenge.get(parameter, "")
            if parameter == "reference_trail" and isinstance(value, list):
                return ", ".join(str(floor) for floor in value)
            return str(value)
        if key == "edge_cost" and edge is not None:
            return str(edge.get("cost", 1))
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
        scroll = max(0, font.size(self.path_buffer[: self.path_cursor])[0] - field.width + 24)
        text_x = field.x + 8 - scroll
        screen.set_clip(field.inflate(-10, -2))
        screen.blit(font.render(self.path_buffer, True, TEXT), (text_x, field.y + 9))
        if pygame.time.get_ticks() % 1000 < 550:
            cursor_x = text_x + font.size(self.path_buffer[: self.path_cursor])[0]
            pygame.draw.line(screen, TEXT, (cursor_x, field.y + 7), (cursor_x, field.bottom - 7), 2)
        screen.set_clip(None)

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
        scroll = max(0, font.size(self.field_buffer[: self.cursor_index])[0] - input_rect.width + 24)
        text_x = input_rect.x + 8 - scroll
        screen.set_clip(input_rect.inflate(-10, -2))
        screen.blit(font.render(self.field_buffer, True, TEXT), (text_x, input_rect.y + 9))
        if pygame.time.get_ticks() % 1000 < 550:
            cursor_x = text_x + font.size(self.field_buffer[: self.cursor_index])[0]
            pygame.draw.line(screen, TEXT, (cursor_x, input_rect.y + 7), (cursor_x, input_rect.bottom - 7), 2)
        screen.set_clip(None)

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
        if event.type == pygame.TEXTINPUT:
            if self.path_dialog is not None:
                self.path_buffer = (
                    self.path_buffer[: self.path_cursor]
                    + event.text
                    + self.path_buffer[self.path_cursor :]
                )
                self.path_cursor += len(event.text)
            elif self.focused_field is not None:
                self._replace_selection(event.text)
            return False
        if event.type == pygame.KEYDOWN:
            if self.path_dialog is not None:
                self._handle_path_key(event)
                return False
            if self.focused_field is not None:
                if event.key == pygame.K_ESCAPE:
                    pygame.key.stop_text_input()
                    self.focused_field = None
                    self.selection_anchor = None
                    return False
                if event.key == pygame.K_a and getattr(event, "mod", 0) & pygame.KMOD_CTRL:
                    self.selection_anchor = 0
                    self.cursor_index = len(self.field_buffer)
                    return False
                if event.key == pygame.K_RETURN:
                    self._commit_field()
                    return False
                if event.key == pygame.K_BACKSPACE:
                    if self.selection_anchor is not None and self.cursor_index != self.selection_anchor:
                        self._replace_selection()
                    elif self.cursor_index:
                        self.selection_anchor = self.cursor_index - 1
                        self._replace_selection()
                elif event.key == pygame.K_DELETE:
                    if self.selection_anchor is not None and self.cursor_index != self.selection_anchor:
                        self._replace_selection()
                    elif self.cursor_index < len(self.field_buffer):
                        self.selection_anchor = self.cursor_index + 1
                        self._replace_selection()
                elif event.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_HOME, pygame.K_END):
                    shift = bool(getattr(event, "mod", 0) & pygame.KMOD_SHIFT)
                    if event.key == pygame.K_LEFT:
                        if not shift and self.selection_anchor is not None:
                            destination = min(self.cursor_index, self.selection_anchor)
                        else:
                            destination = self.cursor_index - 1
                    elif event.key == pygame.K_RIGHT:
                        if not shift and self.selection_anchor is not None:
                            destination = max(self.cursor_index, self.selection_anchor)
                        else:
                            destination = self.cursor_index + 1
                    elif event.key == pygame.K_HOME:
                        destination = 0
                    else:
                        destination = len(self.field_buffer)
                    self._move_cursor(destination, shift)
                return False
            if event.key == pygame.K_ESCAPE:
                if self.edge_origin is not None:
                    self.edge_origin = None
                    self.mode = "select"
                    self._set_status("Criacao da conexao cancelada.")
                    return False
                if self.mode != "select":
                    self.mode = "select"
                    self._set_status("Modo de selecao normal.")
                    return False
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
            if (
                event.type == pygame.MOUSEBUTTONDOWN
                and event.button == 1
                and pygame.Rect(163, 307, 634, 40).collidepoint(event.pos)
            ):
                font = self._font(24)
                scroll = max(
                    0,
                    font.size(self.path_buffer[: self.path_cursor])[0] - 610,
                )
                target_x = event.pos[0] - 171 + scroll
                self.path_cursor = min(
                    range(len(self.path_buffer) + 1),
                    key=lambda index: abs(
                        font.size(self.path_buffer[:index])[0] - target_x
                    ),
                )
            return False
        if self.focused_field is not None and not self._commit_field():
            return False
        if self.dropdown_open:
            for key, rect in self._buttons.items():
                if key.startswith("challenge:") and rect.collidepoint(event.pos):
                    self._activate_button(key)
                    return False
            if self._buttons.get(
                "challenge_combo", pygame.Rect(0, 0, 0, 0)
            ).collidepoint(event.pos):
                self.dropdown_open = False
                return False
            self.dropdown_open = False
        for key, rect in self._field_rects.items():
            if rect.collidepoint(event.pos):
                self._begin_edit(key, event.pos[0])
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
        if self.mode == "edit_cost":
            edge = self._edge_at(position)
            if edge is not None:
                self.selected_edge = edge
                self.tab = "edge"
                self._set_status(f"Conexao {edge[0]}-{edge[1]} selecionada.")
                return
            self._set_status("Clique sobre uma aresta para seleciona-la.", error=True)
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
        closest: tuple[int, int] | None = None
        closest_distance = 10.0
        for edge in self.edges:
            if len(edge) < 2 or edge[0] not in self.positions or edge[1] not in self.positions:
                continue
            start = self.positions[edge[0]]
            end = self.positions[edge[1]]
            distance = self._distance_to_segment(position, start, end)
            if distance <= 9 and distance < closest_distance:
                closest = (edge[0], edge[1])
                closest_distance = distance
        return closest

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

    def _begin_edit(self, key: str, mouse_x: int | None = None) -> None:
        self.focused_field = key
        item = self._selected_item_config()
        objective = self._selected_objective_config()
        challenge = self.config.get("challenge")
        edge = (
            {"cost": self._edge_config(self.selected_edge)[2] if len(self._edge_config(self.selected_edge)) > 2 else 1}
            if key == "edge_cost" and self.selected_edge is not None
            else None
        )
        self.field_buffer = self._field_value(
            key,
            item,
            objective,
            challenge if isinstance(challenge, dict) else None,
            edge,
        )
        self.cursor_index = len(self.field_buffer)
        self.selection_anchor = None
        self.text_scroll_px = 0
        if mouse_x is not None:
            self.cursor_index = self._cursor_from_mouse(key, mouse_x)
        else:
            self.text_scroll_px = max(
                0, self._font(18).size(self.field_buffer)[0] - 240
            )
        pygame.key.start_text_input()

    def _cursor_from_mouse(self, key: str, mouse_x: int) -> int:
        rect = self._field_rects.get(key)
        if rect is None:
            return len(self.field_buffer)
        target_x = mouse_x - rect.x - 6 + self.text_scroll_px
        for index in range(len(self.field_buffer) + 1):
            width = self._font(18).size(self.field_buffer[:index])[0]
            if width >= target_x:
                if index > 0:
                    previous_width = self._font(18).size(self.field_buffer[: index - 1])[0]
                    if target_x - previous_width < width - target_x:
                        return index - 1
                return index
        return len(self.field_buffer)

    def _replace_selection(self, value: str = "") -> None:
        if self.selection_anchor is None:
            start = end = self.cursor_index
        else:
            start, end = sorted((self.selection_anchor, self.cursor_index))
        self.field_buffer = self.field_buffer[:start] + value + self.field_buffer[end:]
        self.cursor_index = start + len(value)
        self.selection_anchor = None

    def _move_cursor(self, position: int, extend: bool) -> None:
        if extend:
            if self.selection_anchor is None:
                self.selection_anchor = self.cursor_index
        else:
            self.selection_anchor = None
        self.cursor_index = min(max(position, 0), len(self.field_buffer))

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
            elif key == "completion":
                rewards = self.config.setdefault("rewards", {})
                if not isinstance(rewards, dict):
                    raise ValueError("A configuracao de recompensas deve ser um objeto.")
                rewards["completion"] = int(value)
            elif key.startswith("challenge_param:"):
                challenge = self.config.get("challenge")
                if not isinstance(challenge, dict):
                    raise ValueError("A configuracao do desafio deve ser um objeto.")
                parameter = key.split(":", 1)[1]
                allowed = ChallengeRegistry.allowed_fields(challenge.get("type")) - {"type"}
                if parameter not in allowed:
                    raise ValueError("O parametro nao e valido para este desafio.")
                if parameter == "reference_trail":
                    parsed_trail = [
                        int(floor.strip())
                        for floor in value.split(",")
                        if floor.strip()
                    ]
                    if not parsed_trail:
                        raise ValueError("Informe ao menos um andar para a trilha.")
                    challenge[parameter] = parsed_trail
                else:
                    challenge[parameter] = int(value)
                self._cache_current_challenge_parameters()
            elif key == "edge_cost":
                if self.selected_edge is None or not self._is_economic():
                    raise ValueError("Selecione uma conexao de um desafio Economic.")
                self._set_edge_cost(self.selected_edge, value)
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
            pygame.key.stop_text_input()
            self.focused_field = None
            self.selection_anchor = None
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
            if self.tab != "edge" and self.mode == "edit_cost":
                self.mode = "select"
        elif key == "challenge_combo":
            self.dropdown_open = not self.dropdown_open
        elif key.startswith("challenge:"):
            self._set_challenge_type(key.split(":", 1)[1])
        elif key.startswith("json:"):
            field = key.split(":", 1)[1]
            self.focused_field = f"json:{field}"
            self.field_buffer = json.dumps(
                self._json_field_value(field), ensure_ascii=False, separators=(",", ":")
            )
            self.cursor_index = len(self.field_buffer)
            self.selection_anchor = None
            pygame.key.start_text_input()
        elif key == "new":
            self.new_level()
        elif key == "open":
            self._open_path_dialog()
        elif key in ("save", "export"):
            default_path = (
                self.active_path
                if key == "save" and self.active_path is not None
                else self.levels_dir / f"{self.config.get('id', 'nova-fase')}.json"
            )
            self.path_dialog = key
            self.path_buffer = str(default_path)
            self.path_cursor = len(self.path_buffer)
            pygame.key.start_text_input()
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
            self.edge_origin = None
            self._set_status("Clique na area do grafo para posicionar o novo andar.")
        elif key == "add_edge":
            self.mode = "add_edge"
            self.edge_origin = None
            self._set_status("Selecione dois andares para criar uma conexao.")
        elif key == "delete_edge":
            self.mode = "delete_edge"
            self.edge_origin = None
            self._set_status("Clique sobre uma conexao para remove-la.")
        elif key == "mode:edit_cost":
            self.mode = "select" if self.mode == "edit_cost" else "edit_cost"
            self.edge_origin = None
            self.selected_edge = None
            self._set_status(
                "Selecione uma aresta para editar o custo."
                if self.mode == "edit_cost"
                else "Modo de selecao normal."
            )
        elif key == "delete_vertex":
            if self.selected_vertex is None:
                self._set_status("Selecione um andar antes de remove-lo.", error=True)
            else:
                self.remove_vertex(self.selected_vertex)
                self.mode = "select"
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
        self.path_cursor = len(self.path_buffer)
        pygame.key.start_text_input()

    def _handle_path_key(self, event: pygame.event.Event) -> None:
        if event.key == pygame.K_ESCAPE:
            self.path_dialog = None
            pygame.key.stop_text_input()
            self._set_status("Operacao cancelada.")
        elif event.key == pygame.K_a and getattr(event, "mod", 0) & pygame.KMOD_CTRL:
            self.path_buffer = ""
            self.path_cursor = 0
        elif event.key == pygame.K_BACKSPACE:
            if self.path_cursor:
                self.path_buffer = (
                    self.path_buffer[: self.path_cursor - 1]
                    + self.path_buffer[self.path_cursor :]
                )
                self.path_cursor -= 1
        elif event.key == pygame.K_DELETE:
            if self.path_cursor < len(self.path_buffer):
                self.path_buffer = (
                    self.path_buffer[: self.path_cursor]
                    + self.path_buffer[self.path_cursor + 1 :]
                )
        elif event.key == pygame.K_LEFT:
            self.path_cursor = max(0, self.path_cursor - 1)
        elif event.key == pygame.K_RIGHT:
            self.path_cursor = min(len(self.path_buffer), self.path_cursor + 1)
        elif event.key == pygame.K_HOME:
            self.path_cursor = 0
        elif event.key == pygame.K_END:
            self.path_cursor = len(self.path_buffer)
        elif event.key == pygame.K_RETURN:
            mode = self.path_dialog
            target = self.path_buffer.strip().strip('"')
            self.path_dialog = None
            pygame.key.stop_text_input()
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

    def _confirm_overwrite(self) -> None:
        destination = self.pending_overwrite
        self.pending_overwrite = None
        if destination is None:
            return
        try:
            self.export_file(destination, overwrite=True)
        except ValueError as error:
            self._set_status(str(error), error=True)

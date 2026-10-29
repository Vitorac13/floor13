"""Carregamento, construcao e validacao dos dados de fases."""

from __future__ import annotations

import json
from collections import deque
from pathlib import Path
from typing import Any

from algorithms import is_connected
from graph import Graph
from level import (
    Collectible,
    ConnectionRequirement,
    ItemKind,
    Level,
    OptionalObjective,
)

DEFAULT_LEVELS_DIR = Path(__file__).resolve().parent / "levels"


class LevelManager:
    @staticmethod
    def create_first_contact() -> Level:
        """Mantem a API anterior enquanto le a configuracao atual em JSON."""
        return LevelManager.load_level("phase-01")

    @staticmethod
    def load_phase_config(
        identifier: str, levels_dir: str | Path | None = None
    ) -> dict[str, Any]:
        directory = Path(levels_dir) if levels_dir is not None else DEFAULT_LEVELS_DIR
        path = directory / f"{identifier}.json"
        try:
            with path.open(encoding="utf-8") as file:
                data = json.load(file)
        except FileNotFoundError as error:
            raise ValueError(f"Arquivo de fase nao encontrado: {path}") from error
        except json.JSONDecodeError as error:
            raise ValueError(
                f"JSON invalido em {path}, linha {error.lineno}, "
                f"coluna {error.colno}: {error.msg}"
            ) from error
        if not isinstance(data, dict):
            raise ValueError(f"A configuracao da fase em {path} deve ser um objeto.")
        return data

    @classmethod
    def load_level(
        cls, identifier: str, levels_dir: str | Path | None = None
    ) -> Level:
        config = cls.load_phase_config(identifier, levels_dir)
        level = cls.from_config(config)
        if level.identifier != identifier:
            raise ValueError(
                f"ID da fase divergente: esperado {identifier!r}, "
                f"recebido {level.identifier!r}."
            )
        cls.validate(level)
        return level

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> Level:
        """Converte uma configuracao JSON validada em estruturas do jogo."""
        identifier = cls._string(config, "id")
        name = cls._string(config, "name")
        number = cls._integer(config, "number")
        start = cls._integer(config, "start_floor")
        exit_floor = cls._integer(config, "exit_floor")

        graph_config = config.get("graph")
        if not isinstance(graph_config, dict):
            raise ValueError(f"Fase {identifier}: 'graph' deve ser um objeto.")
        vertices = graph_config.get("vertices")
        edges = graph_config.get("edges")
        if not isinstance(vertices, list) or not vertices:
            raise ValueError(f"Fase {identifier}: 'graph.vertices' nao pode ser vazio.")
        if any(type(vertex) is not int for vertex in vertices):
            raise ValueError(f"Fase {identifier}: vertices devem ser inteiros.")
        if len(vertices) != len(set(vertices)):
            raise ValueError(f"Fase {identifier}: vertices duplicados.")
        if not isinstance(edges, list):
            raise ValueError(f"Fase {identifier}: 'graph.edges' deve ser uma lista.")

        graph = Graph(vertices)
        for index, edge in enumerate(edges):
            if not isinstance(edge, list) or len(edge) not in (2, 3):
                raise ValueError(
                    f"Fase {identifier}: aresta {index + 1} deve ter "
                    "dois vertices e um peso opcional."
                )
            first, second = edge[:2]
            if (
                type(first) is not int
                or type(second) is not int
                or first not in vertices
                or second not in vertices
            ):
                raise ValueError(
                    f"Fase {identifier}: aresta {index + 1} referencia "
                    "vertice inexistente."
                )
            if graph.has_edge(first, second):
                raise ValueError(
                    f"Fase {identifier}: conexao duplicada entre "
                    f"{first} e {second}."
                )
            weight = edge[2] if len(edge) == 3 else 1
            if type(weight) not in (int, float):
                raise ValueError(
                    f"Fase {identifier}: peso invalido na aresta "
                    f"{first}-{second}; use um numero."
                )
            try:
                graph.add_edge(first, second, weight)
            except (TypeError, ValueError) as error:
                raise ValueError(
                    f"Fase {identifier}: peso invalido na aresta "
                    f"{first}-{second}: {error}"
                ) from error

        raw_items = config.get("items", [])
        if not isinstance(raw_items, list):
            raise ValueError(f"Fase {identifier}: 'items' deve ser uma lista.")
        items = tuple(cls._parse_item(identifier, entry) for entry in raw_items)

        requirements = config.get("exit_requirements", {})
        if not isinstance(requirements, dict):
            raise ValueError(
                f"Fase {identifier}: 'exit_requirements' deve ser um objeto."
            )
        key_ids = requirements.get("keys", [])
        challenge_ids = requirements.get("challenges", [])
        if not isinstance(key_ids, list) or any(
            not isinstance(value, str) for value in key_ids
        ):
            raise ValueError(f"Fase {identifier}: requisitos de chave invalidos.")
        if not isinstance(challenge_ids, list) or any(
            not isinstance(value, str) for value in challenge_ids
        ):
            raise ValueError(f"Fase {identifier}: requisitos de desafio invalidos.")
        raw_connection_requirements = config.get("connection_requirements", [])
        if not isinstance(raw_connection_requirements, list):
            raise ValueError(
                f"Fase {identifier}: 'connection_requirements' deve ser uma lista."
            )
        connection_requirements = tuple(
            cls._parse_connection_requirement(identifier, entry)
            for entry in raw_connection_requirements
        )

        objectives = cls._parse_objectives(identifier, config, set(vertices))
        challenge_config = config.get("challenge", {})
        if not isinstance(challenge_config, dict):
            raise ValueError(f"Fase {identifier}: 'challenge' deve ser um objeto.")
        challenge_type = challenge_config.get("type")
        cls._validate_challenge_config(
            identifier, challenge_type, challenge_config, graph, start, exit_floor
        )
        rewards = config.get("rewards", {})
        if not isinstance(rewards, dict):
            raise ValueError(f"Fase {identifier}: 'rewards' deve ser um objeto.")
        completion_score = rewards.get("completion", 300)
        if type(completion_score) is not int or completion_score < 0:
            raise ValueError(f"Fase {identifier}: recompensa de conclusao invalida.")

        return Level(
            name=name,
            graph=graph,
            start_floor=start,
            exit_floor=exit_floor,
            items=items,
            identifier=identifier,
            number=number,
            exit_requires_keys=tuple(key_ids),
            connection_requirements=connection_requirements,
            required_challenges=tuple(challenge_ids),
            optional_objectives=objectives,
            completion_score=completion_score,
        )

    @staticmethod
    def _parse_connection_requirement(
        identifier: str, entry: Any
    ) -> ConnectionRequirement:
        if not isinstance(entry, dict):
            raise ValueError(
                f"Fase {identifier}: requisito de conexao deve ser um objeto."
            )
        first = entry.get("from")
        second = entry.get("to")
        key_ids = entry.get("keys")
        if type(first) is not int or type(second) is not int or first == second:
            raise ValueError(
                f"Fase {identifier}: extremos invalidos no requisito de conexao."
            )
        if (
            not isinstance(key_ids, list)
            or not key_ids
            or any(not isinstance(key_id, str) or not key_id for key_id in key_ids)
        ):
            raise ValueError(
                f"Fase {identifier}: uma conexao bloqueada precisa de chaves validas."
            )
        return ConnectionRequirement(first, second, tuple(key_ids))

    @staticmethod
    def _validate_challenge_config(
        identifier: str,
        challenge_type: Any,
        config: dict[str, Any],
        graph: Graph[int],
        start: int,
        exit_floor: int,
    ) -> None:
        known_types = {
            "collect_and_exit",
            "hamilton",
            "economic",
            "euler",
            "final",
        }
        if challenge_type is None:
            return
        if not isinstance(challenge_type, str) or challenge_type not in known_types:
            raise ValueError(
                f"Fase {identifier}: tipo de desafio desconhecido: "
                f"{challenge_type!r}."
            )
        endpoint_fields = {
            "hamilton": ("end_floor", exit_floor),
            "economic": ("destination_floor", exit_floor),
            "final": ("destination_floor", exit_floor),
        }
        if challenge_type in endpoint_fields:
            field, default = endpoint_fields[challenge_type]
            floor = config.get(field, default)
            if type(floor) is not int or not graph.has_vertex(floor):
                raise ValueError(
                    f"Fase {identifier}: '{field}' deve indicar um vertice existente."
                )
        if challenge_type == "final":
            return_floor = config.get("return_floor", start)
            if type(return_floor) is not int or not graph.has_vertex(return_floor):
                raise ValueError(
                    f"Fase {identifier}: 'return_floor' deve indicar "
                    "um vertice existente."
                )
        if challenge_type == "euler":
            trail = config.get("reference_trail")
            if (
                not isinstance(trail, list)
                or len(trail) != graph.edge_count + 1
                or any(type(floor) is not int for floor in trail)
                or trail[0] != start
                or trail[-1] != exit_floor
            ):
                raise ValueError(
                    f"Fase {identifier}: percurso de Euler de referencia invalido."
                )
            traversed = list(zip(trail, trail[1:]))
            if (
                any(first == second for first, second in traversed)
                or any(
                    not graph.has_edge(first, second)
                    for first, second in traversed
                )
                or len({frozenset(edge) for edge in traversed}) != graph.edge_count
            ):
                raise ValueError(
                    f"Fase {identifier}: percurso de referencia nao cobre "
                    "cada conexao exatamente uma vez."
                )

    @staticmethod
    def _parse_item(identifier: str, entry: Any) -> Collectible:
        if not isinstance(entry, dict):
            raise ValueError(f"Fase {identifier}: cada item deve ser um objeto.")
        item_id = entry.get("id")
        name = entry.get("name")
        floor = entry.get("floor")
        kind_name = entry.get("type")
        score = entry.get("score", 100 if kind_name != "bonus" else 200)
        is_key = entry.get("key", kind_name == "key")
        if not isinstance(item_id, str) or not item_id.strip():
            raise ValueError(f"Fase {identifier}: item sem identificador valido.")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"Fase {identifier}: item {item_id} sem nome valido.")
        if type(floor) is not int:
            raise ValueError(f"Fase {identifier}: andar invalido no item {item_id}.")
        if kind_name not in ("essential", "bonus", "key"):
            raise ValueError(
                f"Fase {identifier}: tipo invalido para o item {item_id}; "
                "use essential, bonus ou key."
            )
        if type(score) is not int or score < 0:
            raise ValueError(f"Fase {identifier}: pontuacao invalida no item {item_id}.")
        if type(is_key) is not bool:
            raise ValueError(f"Fase {identifier}: indicador de chave invalido.")
        if kind_name == "bonus" and is_key:
            raise ValueError(
                f"Fase {identifier}: um item bonus nao pode ser uma chave."
            )
        kind = ItemKind.BONUS if kind_name == "bonus" else ItemKind.REQUIRED
        return Collectible(item_id, name, floor, kind, score, is_key)

    @staticmethod
    def _parse_objectives(
        identifier: str, config: dict[str, Any], vertices: set[int]
    ) -> tuple[OptionalObjective, ...]:
        raw_objectives = config.get("optional_objectives", [])
        if not isinstance(raw_objectives, list):
            raise ValueError(
                f"Fase {identifier}: 'optional_objectives' deve ser uma lista."
            )
        objectives: list[OptionalObjective] = []
        seen: set[str] = set()
        for entry in raw_objectives:
            if not isinstance(entry, dict):
                raise ValueError(
                    f"Fase {identifier}: cada objetivo opcional deve ser um objeto."
                )
            objective_id = entry.get("id")
            name = entry.get("name")
            description = entry.get("description")
            kind = entry.get("type")
            reward = entry.get("reward")
            floor = entry.get("floor")
            if (
                not isinstance(objective_id, str)
                or not objective_id.strip()
                or objective_id in seen
            ):
                raise ValueError(
                    f"Fase {identifier}: identificador de objetivo invalido ou repetido."
                )
            if not all(isinstance(value, str) and value for value in (name, description)):
                raise ValueError(
                    f"Fase {identifier}: objetivo {objective_id} sem nome/descricao."
                )
            if kind not in (
                "visit_floor",
                "collect_all_bonus",
                "return_to_start",
            ):
                raise ValueError(
                    f"Fase {identifier}: tipo de objetivo invalido: {kind!r}."
                )
            if type(reward) is not int or reward < 0:
                raise ValueError(
                    f"Fase {identifier}: recompensa invalida no objetivo {objective_id}."
                )
            if kind == "visit_floor" and (
                type(floor) is not int or floor not in vertices
            ):
                raise ValueError(
                    f"Fase {identifier}: andar invalido no objetivo {objective_id}."
                )
            if kind in ("collect_all_bonus", "return_to_start"):
                floor = None
            objectives.append(
                OptionalObjective(
                    objective_id, name, description, reward, kind, floor
                )
            )
            seen.add(objective_id)
        return tuple(objectives)

    @staticmethod
    def _string(config: dict[str, Any], key: str) -> str:
        value = config.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Configuracao de fase: '{key}' deve ser texto valido.")
        return value

    @staticmethod
    def _integer(config: dict[str, Any], key: str) -> int:
        value = config.get(key)
        if type(value) is not int:
            raise ValueError(f"Configuracao de fase: '{key}' deve ser inteiro.")
        return value

    @classmethod
    def validate(cls, level: Level) -> None:
        if not level.graph.has_vertex(level.start_floor):
            raise ValueError("O andar inicial nao existe no grafo.")
        if not level.graph.has_vertex(level.exit_floor):
            raise ValueError("O andar de saida nao existe no grafo.")
        if type(level.number) is not int or level.number < 1:
            raise ValueError("O numero da fase deve ser positivo.")
        if not is_connected(level.graph):
            raise ValueError("O grafo da fase deve ser conectado.")

        identifiers = [item.identifier for item in level.items]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("Os identificadores dos itens devem ser unicos.")
        if any(not level.graph.has_vertex(item.floor) for item in level.items):
            raise ValueError("Todos os itens devem estar em andares existentes.")
        if any(not isinstance(item.kind, ItemKind) for item in level.items):
            raise ValueError("Todos os itens devem ter uma categoria valida.")
        if any(type(item.is_key) is not bool for item in level.items):
            raise ValueError("O indicador de chave de cada item deve ser booleano.")
        if any(
            not isinstance(challenge, str) or not challenge
            for challenge in level.required_challenges
        ):
            raise ValueError("Os desafios obrigatorios devem ter identificadores.")
        required = [item for item in level.items if item.kind is ItemKind.REQUIRED]
        bonuses = [item for item in level.items if item.kind is ItemKind.BONUS]
        if any(type(item.score) is not int or item.score < 0 for item in level.items):
            raise ValueError("A pontuacao dos itens deve ser um inteiro nao negativo.")
        if any(item.is_key and item.kind is ItemKind.BONUS for item in level.items):
            raise ValueError("Uma chave nao pode ser um item bonus.")
        if any(
            item_id not in identifiers
            or not next(item for item in level.items if item.identifier == item_id).is_key
            for item_id in level.exit_requires_keys
        ):
            raise ValueError("Toda chave exigida pela saida deve existir como item chave.")
        if len(level.exit_requires_keys) != len(set(level.exit_requires_keys)):
            raise ValueError("Os identificadores de chave exigidos devem ser unicos.")
        configured_connections: set[frozenset[int]] = set()
        key_items = {
            item.identifier: item for item in level.items if item.is_key
        }
        for requirement in level.connection_requirements:
            edge = frozenset((requirement.first_floor, requirement.second_floor))
            if (
                not level.graph.has_edge(
                    requirement.first_floor, requirement.second_floor
                )
                or edge in configured_connections
            ):
                raise ValueError(
                    "Os requisitos de chave devem referenciar conexoes unicas existentes."
                )
            if any(key_id not in key_items for key_id in requirement.key_ids):
                raise ValueError(
                    "Toda chave exigida por uma conexao deve existir como item chave."
                )
            if len(requirement.key_ids) != len(set(requirement.key_ids)):
                raise ValueError(
                    "As chaves exigidas por uma conexao devem ser unicas."
                )
            configured_connections.add(edge)

        required_floors = [item.floor for item in required]
        bonus_floors = [item.floor for item in bonuses]
        if set(required_floors) & set(bonus_floors):
            raise ValueError(
                "Itens bonus nao podem compartilhar andar com obrigatorios."
            )
        if not cls.has_completion_route(level):
            raise ValueError("Nao existe rota viavel para concluir a fase.")

    @staticmethod
    def has_completion_route(level: Level) -> bool:
        """Verifica se ha rota para coletar essenciais e chegar a saida."""
        required_by_floor: dict[int, frozenset[str]] = {}
        keys_by_floor: dict[int, frozenset[str]] = {}
        for item in level.items:
            if item.kind is ItemKind.REQUIRED:
                required_by_floor.setdefault(item.floor, frozenset())
                required_by_floor[item.floor] |= frozenset((item.identifier,))
            if item.is_key:
                keys_by_floor.setdefault(item.floor, frozenset())
                keys_by_floor[item.floor] |= frozenset((item.identifier,))

        required_ids = frozenset(
            identifier
            for identifiers in required_by_floor.values()
            for identifier in identifiers
        )
        initial_items = required_by_floor.get(level.start_floor, frozenset())
        initial_keys = keys_by_floor.get(level.start_floor, frozenset())
        initial_state = (level.start_floor, initial_items, initial_keys)
        queue = deque([initial_state])
        visited = {initial_state}

        while queue:
            floor, collected, keys = queue.popleft()
            if (
                floor == level.exit_floor
                and collected == required_ids
                and set(level.exit_requires_keys).issubset(keys)
            ):
                return True

            for neighbor, _ in level.graph.neighbors(floor):
                edge_keys = {
                    key_id
                    for requirement in level.connection_requirements
                    if {requirement.first_floor, requirement.second_floor}
                    == {floor, neighbor}
                    for key_id in requirement.key_ids
                }
                if not edge_keys.issubset(keys):
                    continue
                next_collected = collected | required_by_floor.get(
                    neighbor, frozenset()
                )
                next_keys = keys | keys_by_floor.get(neighbor, frozenset())
                state = (neighbor, next_collected, next_keys)
                if state not in visited:
                    visited.add(state)
                    queue.append(state)
        return False

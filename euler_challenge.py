"""Configuracao e validacao do desafio de caminho de Euler."""

from __future__ import annotations

from dataclasses import dataclass

from algorithms import is_connected
from graph import Graph
from level import Level
from level_manager import LevelManager

Edge = tuple[int, int]


def edge_key(first: int, second: int) -> Edge:
    """Identifica uma aresta de grafo simples sem depender da direcao."""
    return (first, second) if first < second else (second, first)


@dataclass(frozen=True)
class EulerChallenge:
    name: str
    graph: Graph[int]
    start_floor: int
    end_floor: int
    required_edges: tuple[Edge, ...]
    reference_trail: tuple[int, ...]


class EulerChallengeManager:
    @staticmethod
    def create_full_inspection() -> EulerChallenge:
        return EulerChallengeManager.create_for_level(
            LevelManager.load_level("phase-04")
        )

    @staticmethod
    def create_for_level(level: Level) -> EulerChallenge:
        required_edges = tuple(
            edge_key(first, second)
            for first in level.graph.vertices
            for second, _ in level.graph.neighbors(first)
            if first < second
        )
        challenge = EulerChallenge(
            name=level.name,
            graph=level.graph,
            start_floor=level.start_floor,
            end_floor=level.exit_floor,
            required_edges=required_edges,
            reference_trail=tuple(
                level.challenge_parameters.get("reference_trail", ())
            ),
        )
        EulerChallengeManager.validate(challenge)
        return challenge

    @staticmethod
    def find_eulerian_trail(
        graph: Graph[int], start_floor: int, end_floor: int
    ) -> tuple[int, ...] | None:
        """Encontra uma trilha euleriana pelo algoritmo de Fleury."""
        if not graph.has_vertex(start_floor) or not graph.has_vertex(end_floor):
            return None
        if any(
            neighbor == floor
            for floor in graph.vertices
            for neighbor, _ in graph.neighbors(floor)
        ):
            return None

        if not is_connected(graph):
            return None
        adjacency = {
            floor: {neighbor for neighbor, _ in graph.neighbors(floor)}
            for floor in graph.vertices
        }
        odd_vertices = {floor for floor, neighbors in adjacency.items() if len(neighbors) % 2}
        if odd_vertices != {start_floor, end_floor}:
            return None

        def reachable(origin: int) -> set[int]:
            visited = {origin}
            pending = [origin]
            while pending:
                for neighbor in adjacency[pending.pop()]:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        pending.append(neighbor)
            return visited

        route = [start_floor]
        current = start_floor
        remaining = graph.edge_count
        while remaining:
            neighbors = adjacency[current]
            if not neighbors:
                return None
            before = reachable(current) if len(neighbors) > 1 else set()
            chosen = None
            for neighbor in sorted(neighbors):
                if len(neighbors) == 1:
                    chosen = neighbor
                    break
                adjacency[current].remove(neighbor)
                adjacency[neighbor].remove(current)
                is_bridge = len(reachable(current)) < len(before)
                adjacency[current].add(neighbor)
                adjacency[neighbor].add(current)
                if not is_bridge:
                    chosen = neighbor
                    break
            if chosen is None:
                return None
            adjacency[current].remove(chosen)
            adjacency[chosen].remove(current)
            current = chosen
            route.append(current)
            remaining -= 1
        return tuple(route) if current == end_floor else None

    @classmethod
    def validate(cls, challenge: EulerChallenge) -> None:
        if not challenge.graph.has_vertex(challenge.start_floor):
            raise ValueError("O andar inicial da fase de Euler nao existe.")
        if not challenge.graph.has_vertex(challenge.end_floor):
            raise ValueError("O andar final da fase de Euler nao existe.")
        if not is_connected(challenge.graph):
            raise ValueError("O grafo da fase de Euler deve ser conectado.")
        if any(
            neighbor == floor
            for floor in challenge.graph.vertices
            for neighbor, _ in challenge.graph.neighbors(floor)
        ):
            raise ValueError("A fase de Euler utiliza um grafo simples sem lacos.")

        graph_edges = {
            edge_key(first, second)
            for first in challenge.graph.vertices
            for second, _ in challenge.graph.neighbors(first)
            if first != second
        }
        configured_edges = set(challenge.required_edges)
        if (
            len(challenge.required_edges) != len(configured_edges)
            or configured_edges != graph_edges
        ):
            raise ValueError("As arestas exigidas devem corresponder ao grafo.")

        odd_vertices = {
            floor
            for floor in challenge.graph.vertices
            if sum(
                neighbor != floor
                for neighbor, _ in challenge.graph.neighbors(floor)
            )
            % 2
        }
        if odd_vertices != {challenge.start_floor, challenge.end_floor}:
            raise ValueError(
                "Inicio e fim devem ser os dois vertices de grau impar."
            )

        trail = cls.find_eulerian_trail(
            challenge.graph,
            challenge.start_floor,
            challenge.end_floor,
        )
        if trail is None:
            raise ValueError("O grafo nao possui um caminho de Euler valido.")
        trail_edges = tuple(
            edge_key(first, second) for first, second in zip(trail, trail[1:])
        )
        if (
            len(trail_edges) != len(configured_edges)
            or set(trail_edges) != configured_edges
        ):
            raise ValueError("A rota de referencia nao percorre cada aresta uma vez.")
        if challenge.reference_trail != trail:
            reference_edges = tuple(
                edge_key(first, second)
                for first, second in zip(
                    challenge.reference_trail, challenge.reference_trail[1:]
                )
            )
            if (
                not challenge.reference_trail
                or challenge.reference_trail[0] != challenge.start_floor
                or challenge.reference_trail[-1] != challenge.end_floor
                or len(reference_edges) != len(configured_edges)
                or set(reference_edges) != configured_edges
            ):
                raise ValueError("A rota de referencia nao e um caminho de Euler.")

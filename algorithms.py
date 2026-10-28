"""Algoritmos basicos para grafos usados pelo prototipo."""

from __future__ import annotations

from collections import deque
from heapq import heappop, heappush
from itertools import count
from typing import Hashable, TypeVar

from graph import Graph

Vertex = TypeVar("Vertex", bound=Hashable)


def breadth_first_search(
    graph: Graph[Vertex], start: Vertex, goal: Vertex
) -> list[Vertex] | None:
    """Encontra um caminho com o menor numero de arestas usando BFS."""
    _validate_endpoints(graph, start, goal)
    if start == goal:
        return [start]

    queue: deque[Vertex] = deque([start])
    predecessor: dict[Vertex, Vertex | None] = {start: None}

    while queue:
        current = queue.popleft()
        for neighbor, _ in graph.neighbors(current):
            if neighbor in predecessor:
                continue
            predecessor[neighbor] = current
            if neighbor == goal:
                return _build_path(predecessor, goal)
            queue.append(neighbor)
    return None


def dijkstra(
    graph: Graph[Vertex], start: Vertex, goal: Vertex
) -> tuple[float, list[Vertex]] | None:
    """Retorna o custo e um caminho de custo minimo entre dois vertices."""
    _validate_endpoints(graph, start, goal)
    sequence = count()
    distances: dict[Vertex, float] = {start: 0.0}
    predecessor: dict[Vertex, Vertex | None] = {start: None}
    queue: list[tuple[float, int, Vertex]] = [(0.0, next(sequence), start)]

    while queue:
        distance, _, current = heappop(queue)
        if distance != distances[current]:
            continue
        if current == goal:
            return distance, _build_path(predecessor, goal)

        for neighbor, weight in graph.neighbors(current):
            candidate = distance + weight
            if candidate >= distances.get(neighbor, float("inf")):
                continue
            distances[neighbor] = candidate
            predecessor[neighbor] = current
            heappush(queue, (candidate, next(sequence), neighbor))
    return None


def is_connected(graph: Graph[Vertex]) -> bool:
    """Verifica se todos os vertices pertencem a um unico componente."""
    vertices = graph.vertices
    if not vertices:
        return False

    visited = {vertices[0]}
    queue: deque[Vertex] = deque([vertices[0]])
    while queue:
        current = queue.popleft()
        for neighbor, _ in graph.neighbors(current):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)
    return len(visited) == len(vertices)


def _validate_endpoints(
    graph: Graph[Vertex], start: Vertex, goal: Vertex
) -> None:
    if not graph.has_vertex(start):
        raise KeyError(f"Vertice inicial inexistente: {start!r}")
    if not graph.has_vertex(goal):
        raise KeyError(f"Vertice de destino inexistente: {goal!r}")


def _build_path(
    predecessor: dict[Vertex, Vertex | None], goal: Vertex
) -> list[Vertex]:
    path: list[Vertex] = []
    current: Vertex | None = goal
    while current is not None:
        path.append(current)
        current = predecessor[current]
    path.reverse()
    return path

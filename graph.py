"""Representacao de um predio como grafo nao direcionado e ponderado."""

from __future__ import annotations

from math import isfinite
from typing import Generic, Hashable, Iterable, TypeVar

Vertex = TypeVar("Vertex", bound=Hashable)


class Graph(Generic[Vertex]):
    """Grafo nao direcionado com pesos nao negativos nas arestas."""

    def __init__(self, vertices: Iterable[Vertex] = ()) -> None:
        self._adjacency: dict[Vertex, dict[Vertex, float]] = {}
        for vertex in vertices:
            self.add_vertex(vertex)

    @property
    def vertices(self) -> tuple[Vertex, ...]:
        """Retorna os vertices na ordem em que foram adicionados."""
        return tuple(self._adjacency)

    @property
    def adjacency_list(self) -> dict[Vertex, dict[Vertex, float]]:
        """Retorna uma copia da lista de adjacencia para leitura."""
        return {
            vertex: neighbors.copy()
            for vertex, neighbors in self._adjacency.items()
        }

    @property
    def edge_count(self) -> int:
        adjacency_entries = sum(
            len(neighbors) for neighbors in self._adjacency.values()
        )
        self_loops = sum(
            vertex in neighbors for vertex, neighbors in self._adjacency.items()
        )
        return (adjacency_entries + self_loops) // 2

    def add_vertex(self, vertex: Vertex) -> None:
        self._adjacency.setdefault(vertex, {})

    def add_edge(
        self, first: Vertex, second: Vertex, weight: float = 1
    ) -> None:
        if not isinstance(weight, (int, float)) or not isfinite(weight):
            raise ValueError("O peso da conexao deve ser um numero finito.")
        if weight < 0:
            raise ValueError("O peso da conexao nao pode ser negativo.")

        self.add_vertex(first)
        self.add_vertex(second)
        self._adjacency[first][second] = float(weight)
        self._adjacency[second][first] = float(weight)

    def has_vertex(self, vertex: Vertex) -> bool:
        return vertex in self._adjacency

    def neighbors(self, vertex: Vertex) -> tuple[tuple[Vertex, float], ...]:
        if vertex not in self._adjacency:
            raise KeyError(f"Vertice inexistente: {vertex!r}")
        return tuple(self._adjacency[vertex].items())

    def has_edge(self, first: Vertex, second: Vertex) -> bool:
        return (
            first in self._adjacency
            and second in self._adjacency[first]
        )

    def weight(self, first: Vertex, second: Vertex) -> float:
        if not self.has_edge(first, second):
            raise KeyError(f"Nao existe conexao entre {first!r} e {second!r}.")
        return self._adjacency[first][second]

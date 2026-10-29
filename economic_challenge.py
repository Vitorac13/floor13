"""Configuracao do desafio de menor custo da fase Elevador economico."""

from __future__ import annotations

from dataclasses import dataclass
from math import isclose

from algorithms import dijkstra
from graph import Graph


@dataclass(frozen=True)
class EconomicChallenge:
    name: str
    graph: Graph[int]
    start_floor: int
    destination_floor: int
    optimal_cost: float
    optimal_route: tuple[int, ...]


class EconomicChallengeManager:
    @staticmethod
    def create_economic_elevator() -> EconomicChallenge:
        graph = Graph(range(1, 7))
        for first, second, cost in (
            (1, 2, 1),
            (2, 6, 10),
            (1, 3, 2),
            (3, 4, 2),
            (4, 5, 1),
            (5, 6, 1),
            (3, 5, 3),
            (1, 4, 5),
            (4, 6, 4),
        ):
            graph.add_edge(first, second, cost)

        solution = dijkstra(graph, 1, 6)
        if solution is None:
            raise ValueError("A fase economica nao possui rota ate o destino.")
        optimal_cost, route = solution
        challenge = EconomicChallenge(
            name="Elevador econômico",
            graph=graph,
            start_floor=1,
            destination_floor=6,
            optimal_cost=optimal_cost,
            optimal_route=tuple(route),
        )
        EconomicChallengeManager.validate(challenge)
        return challenge

    @staticmethod
    def validate(challenge: EconomicChallenge) -> None:
        if not challenge.graph.has_vertex(challenge.start_floor):
            raise ValueError("O andar inicial da fase economica nao existe.")
        if not challenge.graph.has_vertex(challenge.destination_floor):
            raise ValueError("O destino da fase economica nao existe.")
        if any(
            cost <= 0
            for floor in challenge.graph.vertices
            for _, cost in challenge.graph.neighbors(floor)
        ):
            raise ValueError("Todos os custos das conexoes devem ser positivos.")

        solution = dijkstra(
            challenge.graph,
            challenge.start_floor,
            challenge.destination_floor,
        )
        if solution is None:
            raise ValueError("O destino da fase economica nao e alcancavel.")
        expected_cost, _ = solution
        if not isclose(challenge.optimal_cost, expected_cost):
            raise ValueError("O custo minimo configurado nao corresponde a Dijkstra.")
        if (
            not challenge.optimal_route
            or challenge.optimal_route[0] != challenge.start_floor
            or challenge.optimal_route[-1] != challenge.destination_floor
            or any(
                not challenge.graph.has_edge(first, second)
                for first, second in zip(
                    challenge.optimal_route, challenge.optimal_route[1:]
                )
            )
        ):
            raise ValueError("A rota minima configurada contem conexoes invalidas.")
        route_cost = sum(
            challenge.graph.weight(first, second)
            for first, second in zip(
                challenge.optimal_route, challenge.optimal_route[1:]
            )
        )
        if not isclose(route_cost, challenge.optimal_cost):
            raise ValueError("O custo da rota configurada nao corresponde ao grafo.")

"""Configuracao e validacao do desafio final A saida."""

from __future__ import annotations

from dataclasses import dataclass
from math import isclose

from algorithms import dijkstra, is_connected
from graph import Graph
from level_manager import LevelManager


@dataclass(frozen=True)
class FinalChallenge:
    name: str
    graph: Graph[int]
    start_floor: int
    destination_floor: int
    return_floor: int
    minimum_outbound_cost: float
    minimum_return_cost: float
    minimum_total_cost: float


class FinalChallengeManager:
    @staticmethod
    def create_the_exit() -> FinalChallenge:
        level = LevelManager.load_level("phase-05")
        challenge_config = LevelManager.load_phase_config("phase-05").get(
            "challenge", {}
        )
        destination = challenge_config.get("destination_floor", level.exit_floor)
        return_floor = challenge_config.get("return_floor", level.start_floor)

        outbound = dijkstra(level.graph, level.start_floor, destination)
        returning = dijkstra(level.graph, destination, return_floor)
        if outbound is None or returning is None:
            raise ValueError("A fase final precisa permitir ida e retorno.")

        challenge = FinalChallenge(
            name=level.name,
            graph=level.graph,
            start_floor=level.start_floor,
            destination_floor=destination,
            return_floor=return_floor,
            minimum_outbound_cost=outbound[0],
            minimum_return_cost=returning[0],
            minimum_total_cost=outbound[0] + returning[0],
        )
        FinalChallengeManager.validate(challenge)
        return challenge

    @classmethod
    def validate(cls, challenge: FinalChallenge) -> None:
        endpoints = (
            challenge.start_floor,
            challenge.destination_floor,
            challenge.return_floor,
        )
        if any(not challenge.graph.has_vertex(floor) for floor in endpoints):
            raise ValueError("Os andares da fase final devem existir no grafo.")
        if (
            challenge.start_floor == challenge.destination_floor
            or challenge.destination_floor == challenge.return_floor
        ):
            raise ValueError("A saida deve ser distinta do inicio e do retorno.")
        if not is_connected(challenge.graph):
            raise ValueError("O grafo da fase final deve ser conectado.")
        if any(
            cost <= 0
            for floor in challenge.graph.vertices
            for _, cost in challenge.graph.neighbors(floor)
        ):
            raise ValueError("Todos os custos das conexoes devem ser positivos.")

        outbound = dijkstra(
            challenge.graph,
            challenge.start_floor,
            challenge.destination_floor,
        )
        returning = dijkstra(
            challenge.graph,
            challenge.destination_floor,
            challenge.return_floor,
        )
        if outbound is None or returning is None:
            raise ValueError("A fase final precisa permitir ida e retorno.")

        expected_total = outbound[0] + returning[0]
        if not (
            isclose(challenge.minimum_outbound_cost, outbound[0])
            and isclose(challenge.minimum_return_cost, returning[0])
            and isclose(challenge.minimum_total_cost, expected_total)
        ):
            raise ValueError("O custo minimo configurado nao corresponde a Dijkstra.")
        if not cls._has_different_cost_routes(
            challenge.graph,
            challenge.start_floor,
            challenge.destination_floor,
        ):
            raise ValueError(
                "A fase final deve oferecer rotas de ida com custos diferentes."
            )

    @staticmethod
    def _has_different_cost_routes(
        graph: Graph[int], start_floor: int, destination_floor: int
    ) -> bool:
        route_costs: set[float] = set()

        def search(current: int, visited: set[int], cost: float) -> None:
            if len(route_costs) > 1:
                return
            if current == destination_floor:
                route_costs.add(cost)
                return
            for neighbor, edge_cost in graph.neighbors(current):
                if neighbor not in visited:
                    search(neighbor, visited | {neighbor}, cost + edge_cost)

        search(start_floor, {start_floor}, 0.0)
        return len(route_costs) > 1

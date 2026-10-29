"""Estado de uma tentativa do desafio Elevador economico."""

from __future__ import annotations

from math import isclose

from economic_challenge import EconomicChallenge


class EconomicGameState:
    def __init__(self, challenge: EconomicChallenge) -> None:
        self.challenge = challenge
        self.optimal_cost = challenge.optimal_cost
        self.optimal_route = challenge.optimal_route
        self.reset()

    @property
    def current_floor(self) -> int:
        return self.visited_sequence[-1]

    @property
    def is_complete(self) -> bool:
        return (
            self.current_floor == self.challenge.destination_floor
            and isclose(self.total_cost, self.optimal_cost)
        )

    @property
    def is_finished(self) -> bool:
        return self.current_floor == self.challenge.destination_floor

    @property
    def valid_destinations(self) -> tuple[int, ...]:
        if self.is_finished:
            return ()
        return tuple(
            neighbor
            for neighbor, _ in self.challenge.graph.neighbors(self.current_floor)
        )

    def move_to(self, destination: int) -> str:
        if self.is_finished:
            if self.is_complete:
                return "Desafio concluido. Pressione R para tentar novamente."
            return "Tentativa encerrada. Existe uma rota mais economica; pressione R."
        if not self.challenge.graph.has_edge(self.current_floor, destination):
            return (
                f"Nao ha conexao entre os andares {self.current_floor:02d} "
                f"e {destination:02d}."
            )

        edge_cost = self.challenge.graph.weight(self.current_floor, destination)
        self.total_cost += edge_cost
        self.visited_sequence.append(destination)

        if destination == self.challenge.destination_floor:
            if self.is_complete:
                return (
                    f"Destino alcancado pelo menor custo! "
                    f"Custo total: {self.total_cost:g}."
                )
            return (
                f"Destino alcancado com custo {self.total_cost:g}; "
                f"existe uma rota mais economica (custo {self.optimal_cost:g}). "
                "Pressione R para reiniciar."
            )

        return (
            f"Deslocamento custou {edge_cost:g}. "
            f"Custo acumulado: {self.total_cost:g}."
        )

    def reset(self) -> None:
        self.visited_sequence = [self.challenge.start_floor]
        self.total_cost = 0.0

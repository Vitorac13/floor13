"""Estado e regras da tentativa da fase final A saida."""

from __future__ import annotations

from math import isclose

from final_challenge import FinalChallenge


class FinalGameState:
    def __init__(self, challenge: FinalChallenge) -> None:
        self.challenge = challenge
        self.reset()

    @property
    def current_floor(self) -> int:
        return self.visited_sequence[-1]

    @property
    def stage(self) -> str:
        return "return" if self.has_reached_destination else "outbound"

    @property
    def is_finished(self) -> bool:
        return (
            self.has_reached_destination
            and self.current_floor == self.challenge.return_floor
        )

    @property
    def is_complete(self) -> bool:
        return self.is_finished and isclose(
            self.total_cost, self.challenge.minimum_total_cost
        )

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
            return (
                f"Retorno concluido com custo {self.total_cost:g}; "
                f"o minimo possivel e {self.challenge.minimum_total_cost:g}. "
                "Pressione R para reiniciar."
            )
        if not self.challenge.graph.has_edge(self.current_floor, destination):
            return (
                f"Nao ha conexao entre os andares {self.current_floor:02d} "
                f"e {destination:02d}."
            )

        edge_cost = self.challenge.graph.weight(self.current_floor, destination)
        if self.has_reached_destination:
            self.return_cost += edge_cost
        else:
            self.outbound_cost += edge_cost
        self.total_cost += edge_cost
        self.visited_sequence.append(destination)

        if (
            not self.has_reached_destination
            and destination == self.challenge.destination_floor
        ):
            self.has_reached_destination = True
            return (
                f"Saida alcancada. Custo da ida: {self.outbound_cost:g}. "
                "Agora retorne ao andar "
                f"{self.challenge.return_floor:02d}."
            )

        if self.is_finished:
            if self.is_complete:
                return (
                    f"Desafio concluido pelo custo minimo! "
                    f"Custo total: {self.total_cost:g}."
                )
            return (
                f"Retorno concluido com custo {self.total_cost:g}; "
                f"o minimo possivel e "
                f"{self.challenge.minimum_total_cost:g}. "
                "Pressione R para reiniciar."
            )

        leg = "retorno" if self.has_reached_destination else "ida"
        leg_cost = (
            self.return_cost if self.has_reached_destination else self.outbound_cost
        )
        return (
            f"Deslocamento custou {edge_cost:g}. "
            f"Custo da {leg}: {leg_cost:g}; "
            f"total: {self.total_cost:g}."
        )

    def reset(self) -> None:
        self.visited_sequence = [self.challenge.start_floor]
        self.has_reached_destination = False
        self.outbound_cost = 0.0
        self.return_cost = 0.0
        self.total_cost = 0.0

"""Estado de uma tentativa do desafio Sem voltar atras."""

from __future__ import annotations

from hamilton_challenge import HamiltonChallenge


class HamiltonGameState:
    def __init__(self, challenge: HamiltonChallenge) -> None:
        self.challenge = challenge
        self.reset()

    @property
    def current_floor(self) -> int:
        return self.visited_sequence[-1]

    @property
    def visited_floors(self) -> frozenset[int]:
        return frozenset(self.visited_sequence)

    @property
    def is_complete(self) -> bool:
        return (
            len(self.visited_sequence) == len(self.challenge.graph.vertices)
            and (
                self.challenge.end_floor is None
                or self.current_floor == self.challenge.end_floor
            )
        )

    @property
    def valid_destinations(self) -> tuple[int, ...]:
        if self.is_complete:
            return ()

        unvisited_count = (
            len(self.challenge.graph.vertices) - len(self.visited_sequence)
        )
        return tuple(
            neighbor
            for neighbor, _ in self.challenge.graph.neighbors(self.current_floor)
            if neighbor not in self.visited_floors
            and not (
                neighbor == self.challenge.end_floor and unvisited_count != 1
            )
        )

    @property
    def is_blocked(self) -> bool:
        return not self.is_complete and not self.valid_destinations

    def move_to(self, destination: int) -> str:
        if self.is_complete:
            return "Desafio concluido. Pressione R para tentar novamente."
        if not self.challenge.graph.has_edge(self.current_floor, destination):
            return (
                f"Nao ha conexao entre os andares {self.current_floor:02d} "
                f"e {destination:02d}."
            )
        if destination in self.visited_floors:
            return f"Andar {destination:02d} ja visitado. Nao e permitido voltar."

        unvisited_count = (
            len(self.challenge.graph.vertices) - len(self.visited_sequence)
        )
        if destination == self.challenge.end_floor and unvisited_count != 1:
            return (
                f"O andar final {destination:02d} so pode ser visitado "
                "depois dos demais."
            )

        self.visited_sequence.append(destination)
        if self.is_complete:
            return f"Desafio concluido: {self.challenge.name}!"
        if self.is_blocked:
            return "Tentativa bloqueada: sem movimentos validos. Pressione R para reiniciar."
        return f"Voce avancou para o andar {destination:02d}."

    def reset(self) -> None:
        self.visited_sequence = [self.challenge.start_floor]

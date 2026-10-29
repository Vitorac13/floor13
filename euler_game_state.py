"""Estado da tentativa da fase Inspecao completa."""

from __future__ import annotations

from euler_challenge import Edge, EulerChallenge, edge_key


class EulerGameState:
    def __init__(self, challenge: EulerChallenge) -> None:
        self.challenge = challenge
        self.reset()

    @property
    def current_floor(self) -> int:
        return self.visited_sequence[-1]

    @property
    def visited_vertices(self) -> frozenset[int]:
        return frozenset(self.visited_sequence)

    @property
    def traversed_edges(self) -> tuple[Edge, ...]:
        return tuple(self.traversed_edge_sequence)

    @property
    def used_edges(self) -> frozenset[Edge]:
        return frozenset(self.traversed_edge_sequence)

    @property
    def remaining_edges(self) -> tuple[Edge, ...]:
        return tuple(
            edge for edge in self.challenge.required_edges if edge not in self.used_edges
        )

    @property
    def progress(self) -> tuple[int, int]:
        return len(self.traversed_edge_sequence), len(self.challenge.required_edges)

    @property
    def is_complete(self) -> bool:
        return (
            not self.remaining_edges
            and self.current_floor == self.challenge.end_floor
        )

    @property
    def is_blocked(self) -> bool:
        return not self.is_complete and not self.valid_destinations

    @property
    def valid_destinations(self) -> tuple[int, ...]:
        if self.is_complete:
            return ()
        return tuple(
            neighbor
            for neighbor, _ in self.challenge.graph.neighbors(self.current_floor)
            if edge_key(self.current_floor, neighbor) not in self.used_edges
        )

    def move_to(self, destination: int) -> str:
        if self.is_complete:
            return "Inspecao concluida. Pressione R para reiniciar."
        if not self.challenge.graph.has_edge(self.current_floor, destination):
            return (
                f"Nao ha conexao entre os andares {self.current_floor:02d} "
                f"e {destination:02d}."
            )

        edge = edge_key(self.current_floor, destination)
        if edge in self.used_edges:
            return (
                f"A conexao {edge[0]:02d}-{edge[1]:02d} ja foi percorrida. "
                "Escolha uma conexao ainda nao inspecionada."
            )

        self.traversed_edge_sequence.append(edge)
        self.visited_sequence.append(destination)

        if self.is_complete:
            return (
                f"Inspecao concluida: todas as {len(self.challenge.required_edges)} "
                "conexoes foram percorridas!"
            )
        if self.is_blocked:
            return (
                f"Tentativa bloqueada: {self.progress[0]} de {self.progress[1]} "
                "conexoes percorridas. Pressione R para reiniciar."
            )
        return (
            f"Conexao {edge[0]:02d}-{edge[1]:02d} percorrida. "
            f"Progresso: {self.progress[0]} de {self.progress[1]}."
        )

    def reset(self) -> None:
        self.visited_sequence = [self.challenge.start_floor]
        self.traversed_edge_sequence: list[Edge] = []

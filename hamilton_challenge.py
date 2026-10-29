"""Configuracao e validacao do desafio de caminho hamiltoniano."""

from __future__ import annotations

from dataclasses import dataclass

from graph import Graph
from level import Level
from level_manager import LevelManager


@dataclass(frozen=True)
class HamiltonChallenge:
    name: str
    graph: Graph[int]
    start_floor: int
    end_floor: int | None = None


class HamiltonChallengeManager:
    @staticmethod
    def create_no_turning_back() -> HamiltonChallenge:
        return HamiltonChallengeManager.create_for_level(
            LevelManager.load_level("phase-02")
        )

    @staticmethod
    def create_for_level(level: Level) -> HamiltonChallenge:
        challenge = HamiltonChallenge(
            name=level.name,
            graph=level.graph,
            start_floor=level.start_floor,
            end_floor=level.challenge_parameters.get(
                "end_floor", level.exit_floor
            ),
        )
        HamiltonChallengeManager.validate(challenge)
        return challenge

    @staticmethod
    def find_hamiltonian_path(
        challenge: HamiltonChallenge,
    ) -> tuple[int, ...] | None:
        """Return a valid Hamiltonian route, respecting configured endpoints."""
        path = [challenge.start_floor]
        visited = {challenge.start_floor}

        def search(current: int) -> tuple[int, ...] | None:
            if len(path) == len(challenge.graph.vertices):
                if challenge.end_floor is None or current == challenge.end_floor:
                    return tuple(path)
                return None

            for neighbor, _ in challenge.graph.neighbors(current):
                if neighbor in visited:
                    continue
                if (
                    neighbor == challenge.end_floor
                    and len(path) != len(challenge.graph.vertices) - 1
                ):
                    continue

                visited.add(neighbor)
                path.append(neighbor)
                result = search(neighbor)
                if result is not None:
                    return result
                path.pop()
                visited.remove(neighbor)
            return None

        if not challenge.graph.has_vertex(challenge.start_floor):
            return None
        if (
            challenge.end_floor is not None
            and not challenge.graph.has_vertex(challenge.end_floor)
        ):
            return None
        return search(challenge.start_floor)

    @classmethod
    def validate(cls, challenge: HamiltonChallenge) -> None:
        if not challenge.graph.has_vertex(challenge.start_floor):
            raise ValueError("O andar inicial do desafio nao existe.")
        if (
            challenge.end_floor is not None
            and not challenge.graph.has_vertex(challenge.end_floor)
        ):
            raise ValueError("O andar final do desafio nao existe.")
        if cls.find_hamiltonian_path(challenge) is None:
            raise ValueError("O desafio nao possui uma rota hamiltoniana valida.")

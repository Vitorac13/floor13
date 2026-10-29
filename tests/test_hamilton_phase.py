import unittest

from game_state import GameState
from hamilton_challenge import (
    HamiltonChallengeManager,
)
from hamilton_game_state import HamiltonGameState
from level_manager import LevelManager


class HamiltonChallengeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.challenge = HamiltonChallengeManager.create_no_turning_back()
        self.game = HamiltonGameState(self.challenge)

    def test_phase_configuration_has_expected_vertices_and_endpoints(self) -> None:
        self.assertEqual(self.challenge.name, "Sem voltar atrás")
        self.assertEqual(len(self.challenge.graph.vertices), 6)
        self.assertEqual(self.challenge.start_floor, 1)
        self.assertEqual(self.challenge.end_floor, 6)

    def test_configuration_has_a_valid_hamiltonian_route(self) -> None:
        route = HamiltonChallengeManager.find_hamiltonian_path(self.challenge)

        self.assertEqual(route, (1, 2, 3, 4, 5, 6))
        self.assertEqual(len(set(route)), len(self.challenge.graph.vertices))
        self.assertTrue(
            all(
                self.challenge.graph.has_edge(first, second)
                for first, second in zip(route, route[1:])
            )
        )

    def test_only_connected_floors_can_be_selected(self) -> None:
        message = self.game.move_to(4)

        self.assertIn("Nao ha conexao", message)
        self.assertEqual(self.game.visited_sequence, [1])
        self.assertEqual(self.game.current_floor, 1)

    def test_revisiting_a_floor_is_rejected(self) -> None:
        self.game.move_to(2)
        message = self.game.move_to(1)

        self.assertIn("ja visitado", message)
        self.assertEqual(self.game.visited_sequence, [1, 2])

    def test_sequence_tracks_each_successful_move_in_order(self) -> None:
        for floor in (3, 2, 4):
            self.game.move_to(floor)

        self.assertEqual(self.game.visited_sequence, [1, 3, 2, 4])
        self.assertEqual(self.game.visited_floors, frozenset({1, 2, 3, 4}))

    def test_challenge_completes_only_after_all_floors_once_at_the_end(self) -> None:
        for floor in (2, 3, 4, 5):
            self.game.move_to(floor)
            self.assertFalse(self.game.is_complete)

        message = self.game.move_to(6)

        self.assertTrue(self.game.is_complete)
        self.assertEqual(self.game.visited_sequence, [1, 2, 3, 4, 5, 6])
        self.assertIn("Desafio concluido", message)

    def test_required_final_floor_cannot_be_visited_early(self) -> None:
        self.game.move_to(2)
        self.game.move_to(4)
        message = self.game.move_to(6)

        self.assertIn("so pode ser visitado depois dos demais", message)
        self.assertEqual(self.game.visited_sequence, [1, 2, 4])
        self.assertNotIn(6, self.game.valid_destinations)

    def test_dead_end_blocks_attempt_until_restart(self) -> None:
        for floor in (3, 4):
            self.game.move_to(floor)
        message = self.game.move_to(2)

        self.assertTrue(self.game.is_blocked)
        self.assertFalse(self.game.is_complete)
        self.assertEqual(self.game.valid_destinations, ())
        self.assertIn("Tentativa bloqueada", message)

    def test_restart_restores_initial_state_and_valid_destinations(self) -> None:
        for floor in (3, 4, 2):
            self.game.move_to(floor)

        self.game.reset()

        self.assertEqual(self.game.current_floor, self.challenge.start_floor)
        self.assertEqual(self.game.visited_sequence, [self.challenge.start_floor])
        self.assertFalse(self.game.is_blocked)
        self.assertFalse(self.game.is_complete)
        self.assertEqual(self.game.valid_destinations, (2, 3))

    def test_first_phase_still_allows_returning_to_a_visited_floor(self) -> None:
        first_phase = GameState(LevelManager.create_first_contact())
        first_phase.move_to(2)
        first_phase.move_to(3)

        message = first_phase.move_to(2)

        self.assertEqual(first_phase.current_floor, 2)
        self.assertIn(2, first_phase.visited_floors)
        self.assertNotIn("Nao e permitido voltar", message)


if __name__ == "__main__":
    unittest.main()

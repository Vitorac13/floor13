import unittest
from dataclasses import replace

from economic_challenge import EconomicChallengeManager
from economic_game_state import EconomicGameState
from euler_challenge import EulerChallengeManager
from euler_game_state import EulerGameState
from game_state import GameState
from hamilton_challenge import HamiltonChallengeManager
from hamilton_game_state import HamiltonGameState
from level_manager import LevelManager


class EulerChallengeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.challenge = EulerChallengeManager.create_full_inspection()
        self.game = EulerGameState(self.challenge)

    def traverse(self, *floors: int) -> None:
        for floor in floors:
            self.game.move_to(floor)

    def test_graph_configuration_and_reference_euler_trail(self) -> None:
        challenge = self.challenge
        route = challenge.reference_trail

        self.assertEqual(challenge.name, "Inspeção completa")
        self.assertEqual(challenge.graph.vertices, (1, 2, 3, 4, 5))
        self.assertEqual(challenge.graph.edge_count, 7)
        self.assertEqual(challenge.start_floor, 1)
        self.assertEqual(challenge.end_floor, 4)
        self.assertEqual(len(route), challenge.graph.edge_count + 1)
        self.assertEqual(route[0], challenge.start_floor)
        self.assertEqual(route[-1], challenge.end_floor)
        self.assertEqual(
            len(
                {
                    tuple(sorted(edge))
                    for edge in zip(route, route[1:])
                }
            ),
            challenge.graph.edge_count,
        )
        self.assertTrue(
            all(
                challenge.graph.has_edge(first, second)
                for first, second in zip(route, route[1:])
            )
        )

    def test_manager_finds_a_valid_eulerian_trail(self) -> None:
        route = EulerChallengeManager.find_eulerian_trail(
            self.challenge.graph,
            self.challenge.start_floor,
            self.challenge.end_floor,
        )

        self.assertIsNotNone(route)
        traversed_edges = [
            tuple(sorted(edge)) for edge in zip(route, route[1:])
        ]
        self.assertEqual(set(traversed_edges), set(self.challenge.required_edges))
        self.assertEqual(len(traversed_edges), len(set(traversed_edges)))

    def test_movement_requires_an_existing_connection(self) -> None:
        message = self.game.move_to(5)

        self.assertIn("Nao ha conexao", message)
        self.assertEqual(self.game.current_floor, 1)
        self.assertEqual(self.game.visited_sequence, [1])
        self.assertEqual(self.game.traversed_edges, ())

    def test_player_can_revisit_vertices_using_unused_edges(self) -> None:
        self.traverse(2, 3, 1)

        self.assertEqual(self.game.visited_sequence, [1, 2, 3, 1])
        self.assertEqual(self.game.visited_vertices, frozenset({1, 2, 3}))
        self.assertEqual(self.game.progress, (3, 7))
        self.assertFalse(self.game.is_complete)

    def test_used_edge_cannot_be_traversed_again_and_invalid_move_is_unchanged(self) -> None:
        self.game.move_to(2)
        state_before_attempt = (
            self.game.current_floor,
            self.game.visited_sequence.copy(),
            self.game.traversed_edges,
        )

        message = self.game.move_to(1)

        self.assertIn("ja foi percorrida", message)
        self.assertEqual(
            (
                self.game.current_floor,
                self.game.visited_sequence,
                self.game.traversed_edges,
            ),
            state_before_attempt,
        )

    def test_traversed_and_remaining_edges_are_tracked_independently(self) -> None:
        self.traverse(2, 3, 1)

        self.assertEqual(self.game.traversed_edges, ((1, 2), (2, 3), (1, 3)))
        self.assertEqual(self.game.progress, (3, 7))
        self.assertEqual(len(self.game.remaining_edges), 4)
        self.assertEqual(
            set(self.game.traversed_edges) | set(self.game.remaining_edges),
            set(self.challenge.required_edges),
        )

    def test_visiting_all_vertices_without_inspecting_all_edges_is_not_a_win(self) -> None:
        self.traverse(2, 3, 1, 4, 5, 2)

        self.assertEqual(self.game.visited_vertices, frozenset({1, 2, 3, 4, 5}))
        self.assertEqual(self.game.progress, (6, 7))
        self.assertFalse(self.game.is_complete)
        self.assertEqual(self.game.current_floor, 2)

    def test_all_edges_must_be_used_and_attempt_must_end_at_required_vertex(self) -> None:
        for floor in self.challenge.reference_trail[1:-1]:
            self.game.move_to(floor)
            self.assertFalse(self.game.is_complete)

        message = self.game.move_to(self.challenge.end_floor)

        self.assertTrue(self.game.is_complete)
        self.assertEqual(self.game.progress, (7, 7))
        self.assertEqual(self.game.current_floor, self.challenge.end_floor)
        self.assertIn("Inspecao concluida", message)
        self.assertEqual(self.game.valid_destinations, ())

    def test_reaching_end_vertex_early_does_not_finish_inspection(self) -> None:
        message = self.game.move_to(self.challenge.end_floor)

        self.assertFalse(self.game.is_complete)
        self.assertEqual(self.game.current_floor, self.challenge.end_floor)
        self.assertEqual(self.game.progress, (1, 7))
        self.assertNotIn("concluida", message)

    def test_dead_end_before_all_edges_reports_blocked_attempt(self) -> None:
        messages = [
            self.game.move_to(floor) for floor in (4, 5, 2, 4)
        ]

        self.assertTrue(self.game.is_blocked)
        self.assertFalse(self.game.is_complete)
        self.assertEqual(self.game.progress, (4, 7))
        self.assertIn("Tentativa bloqueada", messages[-1])

    def test_reset_restores_route_and_edge_progress(self) -> None:
        self.traverse(2, 3, 1, 4)
        self.game.reset()

        self.assertEqual(self.game.current_floor, self.challenge.start_floor)
        self.assertEqual(self.game.visited_sequence, [self.challenge.start_floor])
        self.assertEqual(self.game.visited_vertices, frozenset({1}))
        self.assertEqual(self.game.traversed_edges, ())
        self.assertEqual(self.game.remaining_edges, self.challenge.required_edges)
        self.assertEqual(self.game.progress, (0, 7))
        self.assertFalse(self.game.is_complete)

    def test_previous_phases_keep_their_own_movement_rules(self) -> None:
        phase_one = GameState(LevelManager.create_first_contact())
        phase_one.move_to(2)
        phase_one.move_to(3)
        phase_one.move_to(2)
        self.assertEqual(phase_one.current_floor, 2)

        phase_two = HamiltonGameState(
            HamiltonChallengeManager.create_no_turning_back()
        )
        phase_two.move_to(2)
        self.assertIn("ja visitado", phase_two.move_to(1))
        self.assertEqual(phase_two.current_floor, 2)

        phase_three = EconomicGameState(
            EconomicChallengeManager.create_economic_elevator()
        )
        phase_three.move_to(2)
        phase_three.move_to(1)
        self.assertEqual(phase_three.total_cost, 2)
        self.assertEqual(phase_three.current_floor, 1)

    def test_final_floor_must_be_one_of_the_two_odd_degree_vertices(self) -> None:
        invalid_challenge = replace(self.challenge, end_floor=2)

        with self.assertRaisesRegex(ValueError, "vertices de grau impar"):
            EulerChallengeManager.validate(invalid_challenge)


if __name__ == "__main__":
    unittest.main()

import unittest

from algorithms import dijkstra, is_connected
from economic_challenge import EconomicChallengeManager
from economic_game_state import EconomicGameState
from euler_challenge import EulerChallengeManager
from euler_game_state import EulerGameState
from final_challenge import FinalChallengeManager
from final_game_state import FinalGameState
from game_state import GameState
from hamilton_challenge import HamiltonChallengeManager
from hamilton_game_state import HamiltonGameState
from level_manager import LevelManager


def simple_route_costs(graph, start: int, destination: int) -> set[float]:
    costs: set[float] = set()

    def search(current: int, visited: set[int], cost: float) -> None:
        if current == destination:
            costs.add(cost)
            return
        for neighbor, edge_cost in graph.neighbors(current):
            if neighbor not in visited:
                search(neighbor, visited | {neighbor}, cost + edge_cost)

    search(start, {start}, 0.0)
    return costs


class FinalChallengeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.challenge = FinalChallengeManager.create_the_exit()
        self.game = FinalGameState(self.challenge)

    def travel(self, *floors: int) -> list[str]:
        return [self.game.move_to(floor) for floor in floors]

    def test_graph_configuration_has_positive_weights_and_distinct_objectives(self) -> None:
        challenge = self.challenge

        self.assertEqual(challenge.name, "A saída")
        self.assertEqual(challenge.graph.vertices, (1, 2, 3, 4, 5, 6))
        self.assertTrue(is_connected(challenge.graph))
        self.assertEqual(challenge.start_floor, 1)
        self.assertEqual(challenge.destination_floor, 6)
        self.assertEqual(challenge.return_floor, 1)
        self.assertTrue(
            all(
                weight > 0
                for floor in challenge.graph.vertices
                for _, weight in challenge.graph.neighbors(floor)
            )
        )
        self.assertGreaterEqual(
            len(simple_route_costs(challenge.graph, 1, 6)), 2
        )

    def test_dijkstra_calculates_both_legs_and_minimum_round_trip(self) -> None:
        outbound = dijkstra(self.challenge.graph, 1, 6)
        returning = dijkstra(self.challenge.graph, 6, 1)

        self.assertIsNotNone(outbound)
        self.assertIsNotNone(returning)
        self.assertEqual(outbound[0], 4)
        self.assertEqual(returning[0], 4)
        self.assertEqual(self.challenge.minimum_total_cost, 8)

    def test_valid_reference_trip_uses_a_different_return_route(self) -> None:
        messages = self.travel(2, 6, 4, 3, 1)

        self.assertIn("Saida alcancada", messages[1])
        self.assertTrue(self.game.is_complete)
        self.assertEqual(self.game.visited_sequence, [1, 2, 6, 4, 3, 1])
        self.assertEqual(self.game.outbound_cost, 4)
        self.assertEqual(self.game.return_cost, 4)
        self.assertEqual(self.game.total_cost, 8)

    def test_valid_moves_accumulate_outbound_and_return_costs_separately(self) -> None:
        self.travel(2, 6)

        self.assertEqual(self.game.stage, "return")
        self.assertEqual(self.game.outbound_cost, 4)
        self.assertEqual(self.game.return_cost, 0)
        self.assertEqual(self.game.total_cost, 4)

        self.travel(4, 3)

        self.assertEqual(self.game.current_floor, 3)
        self.assertEqual(self.game.return_cost, 3)
        self.assertEqual(self.game.total_cost, 7)

    def test_non_connected_move_is_rejected_without_state_change(self) -> None:
        before = (
            self.game.current_floor,
            self.game.visited_sequence.copy(),
            self.game.outbound_cost,
            self.game.return_cost,
            self.game.total_cost,
            self.game.stage,
        )

        message = self.game.move_to(6)

        self.assertIn("Nao ha conexao", message)
        self.assertEqual(
            (
                self.game.current_floor,
                self.game.visited_sequence,
                self.game.outbound_cost,
                self.game.return_cost,
                self.game.total_cost,
                self.game.stage,
            ),
            before,
        )

    def test_reaching_exit_does_not_finish_before_returning(self) -> None:
        self.travel(2, 6)

        self.assertTrue(self.game.has_reached_destination)
        self.assertEqual(self.game.stage, "return")
        self.assertFalse(self.game.is_finished)
        self.assertFalse(self.game.is_complete)
        self.assertEqual(self.game.valid_destinations, (2, 4, 5))

    def test_more_expensive_round_trip_is_rejected_at_return_point(self) -> None:
        messages = self.travel(5, 6, 4, 3, 1)

        self.assertTrue(self.game.is_finished)
        self.assertFalse(self.game.is_complete)
        self.assertEqual(self.game.total_cost, 11)
        self.assertIn("minimo possivel e 8", messages[-1])
        self.assertEqual(self.game.valid_destinations, ())

    def test_different_equal_minimum_routes_are_accepted(self) -> None:
        self.travel(3, 4, 6, 2, 1)

        self.assertTrue(self.game.is_complete)
        self.assertEqual(self.game.total_cost, self.challenge.minimum_total_cost)
        self.assertNotEqual(
            self.game.visited_sequence,
            [1, 2, 6, 4, 3, 1],
        )

    def test_reset_restores_both_legs_and_progress(self) -> None:
        self.travel(3, 4, 6, 2)
        self.game.reset()

        self.assertEqual(self.game.current_floor, self.challenge.start_floor)
        self.assertEqual(self.game.visited_sequence, [self.challenge.start_floor])
        self.assertEqual(self.game.stage, "outbound")
        self.assertFalse(self.game.has_reached_destination)
        self.assertFalse(self.game.is_finished)
        self.assertFalse(self.game.is_complete)
        self.assertEqual(self.game.outbound_cost, 0)
        self.assertEqual(self.game.return_cost, 0)
        self.assertEqual(self.game.total_cost, 0)

    def test_previous_four_phases_keep_their_own_rules(self) -> None:
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

        phase_three = EconomicGameState(
            EconomicChallengeManager.create_economic_elevator()
        )
        phase_three.move_to(2)
        phase_three.move_to(1)
        self.assertEqual(phase_three.total_cost, 2)

        phase_four_challenge = EulerChallengeManager.create_full_inspection()
        phase_four = EulerGameState(phase_four_challenge)
        phase_four.move_to(2)
        phase_four.move_to(3)
        phase_four.move_to(1)
        self.assertEqual(phase_four.progress, (3, 7))


if __name__ == "__main__":
    unittest.main()

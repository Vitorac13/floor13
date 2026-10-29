import unittest

from algorithms import dijkstra
from economic_challenge import EconomicChallengeManager
from economic_game_state import EconomicGameState
from game_state import GameState
from hamilton_challenge import HamiltonChallengeManager
from hamilton_game_state import HamiltonGameState
from level_manager import LevelManager


def simple_routes(graph, start: int, destination: int) -> list[tuple[int, ...]]:
    routes: list[tuple[int, ...]] = []

    def search(current: int, path: list[int]) -> None:
        if current == destination:
            routes.append(tuple(path))
            return
        for neighbor, _ in graph.neighbors(current):
            if neighbor not in path:
                search(neighbor, path + [neighbor])

    search(start, [start])
    return routes


class EconomicChallengeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.challenge = EconomicChallengeManager.create_economic_elevator()
        self.game = EconomicGameState(self.challenge)

    def travel(self, *floors: int) -> None:
        for floor in floors:
            self.game.move_to(floor)

    def test_dijkstra_calculates_minimum_cost_and_reconstructs_route(self) -> None:
        result = dijkstra(
            self.challenge.graph,
            self.challenge.start_floor,
            self.challenge.destination_floor,
        )

        self.assertIsNotNone(result)
        cost, route = result
        self.assertEqual(cost, 6)
        self.assertEqual(tuple(route), (1, 3, 5, 6))
        self.assertEqual(self.game.optimal_cost, 6)
        self.assertEqual(
            sum(
                self.challenge.graph.weight(first, second)
                for first, second in zip(route, route[1:])
            ),
            cost,
        )

    def test_graph_has_routes_with_different_costs_and_positive_weights(self) -> None:
        routes = simple_routes(
            self.challenge.graph,
            self.challenge.start_floor,
            self.challenge.destination_floor,
        )
        costs = {
            sum(
                self.challenge.graph.weight(first, second)
                for first, second in zip(route, route[1:])
            )
            for route in routes
        }

        self.assertGreaterEqual(len(costs), 2)
        self.assertGreater(min(costs), 0)
        self.assertTrue(
            all(
                weight > 0
                for floor in self.challenge.graph.vertices
                for _, weight in self.challenge.graph.neighbors(floor)
            )
        )
        self.assertEqual(
            self.challenge.graph.weight(1, 2)
            + self.challenge.graph.weight(2, 6),
            11,
        )
        self.assertLess(
            len((1, 2, 6)),
            len(self.challenge.optimal_route),
        )

    def test_each_valid_move_adds_the_connection_cost(self) -> None:
        message = self.game.move_to(2)

        self.assertEqual(self.game.current_floor, 2)
        self.assertEqual(self.game.total_cost, 1)
        self.assertIn("custou 1", message)
        self.travel(6)
        self.assertEqual(self.game.total_cost, 11)

    def test_move_without_an_edge_is_rejected_without_changing_state(self) -> None:
        message = self.game.move_to(6)

        self.assertIn("Nao ha conexao", message)
        self.assertEqual(self.game.current_floor, 1)
        self.assertEqual(self.game.total_cost, 0)
        self.assertEqual(self.game.visited_sequence, [1])

    def test_arriving_on_a_minimum_cost_route_completes_the_challenge(self) -> None:
        self.travel(*self.challenge.optimal_route[1:])

        self.assertTrue(self.game.is_complete)
        self.assertTrue(self.game.is_finished)
        self.assertEqual(self.game.total_cost, self.game.optimal_cost)

    def test_arriving_with_a_higher_cost_does_not_complete_the_challenge(self) -> None:
        message = self.game.move_to(2)
        self.assertIn("custou 1", message)
        message = self.game.move_to(6)

        self.assertFalse(self.game.is_complete)
        self.assertTrue(self.game.is_finished)
        self.assertEqual(self.game.total_cost, 11)
        self.assertIn("existe uma rota mais economica", message)
        self.assertEqual(self.game.valid_destinations, ())

    def test_an_alternative_route_with_the_same_minimum_cost_is_accepted(self) -> None:
        self.travel(3, 4, 5, 6)

        self.assertTrue(self.game.is_complete)
        self.assertEqual(self.game.total_cost, self.challenge.optimal_cost)
        self.assertNotEqual(
            tuple(self.game.visited_sequence), self.challenge.optimal_route
        )

    def test_restart_resets_cost_route_and_completion_status(self) -> None:
        self.travel(2, 6)
        self.game.reset()

        self.assertEqual(self.game.current_floor, self.challenge.start_floor)
        self.assertEqual(self.game.visited_sequence, [self.challenge.start_floor])
        self.assertEqual(self.game.total_cost, 0)
        self.assertFalse(self.game.is_finished)
        self.assertFalse(self.game.is_complete)
        self.travel(3, 4, 5, 6)
        self.assertTrue(self.game.is_complete)

    def test_phases_one_and_two_keep_their_own_movement_rules(self) -> None:
        phase_one = GameState(LevelManager.create_first_contact())
        phase_one.move_to(2)
        phase_one.move_to(3)
        phase_one.move_to(2)
        self.assertEqual(phase_one.current_floor, 2)

        phase_two = HamiltonGameState(
            HamiltonChallengeManager.create_no_turning_back()
        )
        phase_two.move_to(2)
        message = phase_two.move_to(1)
        self.assertIn("ja visitado", message)
        self.assertEqual(phase_two.current_floor, 2)


if __name__ == "__main__":
    unittest.main()

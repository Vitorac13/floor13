import unittest

from algorithms import breadth_first_search, dijkstra, is_connected
from graph import Graph


class GraphTests(unittest.TestCase):
    def test_undirected_adjacency_and_duplicate_edge(self) -> None:
        graph = Graph([1, 2, 3])
        graph.add_edge(1, 2)
        graph.add_edge(1, 2, 4)

        self.assertEqual(graph.edge_count, 1)
        self.assertEqual(graph.weight(1, 2), 4)
        self.assertEqual(graph.weight(2, 1), 4)
        self.assertEqual(graph.neighbors(1), ((2, 4.0),))

    def test_adjacency_list_is_a_copy(self) -> None:
        graph = Graph([1, 2])
        graph.add_edge(1, 2)

        adjacency = graph.adjacency_list
        adjacency[1].clear()

        self.assertTrue(graph.has_edge(1, 2))

    def test_self_loop_is_counted_once(self) -> None:
        graph = Graph([1])
        graph.add_edge(1, 1)

        self.assertEqual(graph.edge_count, 1)
        self.assertEqual(graph.neighbors(1), ((1, 1.0),))

    def test_rejects_negative_or_non_finite_weights(self) -> None:
        graph = Graph()
        for weight in (-1, float("inf"), float("nan")):
            with self.subTest(weight=weight):
                with self.assertRaises(ValueError):
                    graph.add_edge(1, 2, weight)


class AlgorithmTests(unittest.TestCase):
    def setUp(self) -> None:
        self.graph = Graph([1, 2, 3, 4, 5])
        self.graph.add_edge(1, 2, 1)
        self.graph.add_edge(2, 3, 1)
        self.graph.add_edge(1, 4, 2)
        self.graph.add_edge(4, 3, 2)

    def test_bfs_returns_path_with_fewest_edges(self) -> None:
        self.assertEqual(breadth_first_search(self.graph, 1, 3), [1, 2, 3])

    def test_dijkstra_returns_minimum_weight_path(self) -> None:
        self.assertEqual(dijkstra(self.graph, 1, 3), (2.0, [1, 2, 3]))

    def test_algorithms_handle_same_and_unreachable_vertices(self) -> None:
        self.assertEqual(breadth_first_search(self.graph, 1, 1), [1])
        self.assertEqual(dijkstra(self.graph, 1, 1), (0.0, [1]))
        self.assertIsNone(breadth_first_search(self.graph, 1, 5))
        self.assertIsNone(dijkstra(self.graph, 1, 5))

    def test_connectivity(self) -> None:
        self.assertFalse(is_connected(self.graph))
        self.graph.add_edge(3, 5)
        self.assertTrue(is_connected(self.graph))
        self.assertTrue(is_connected(Graph([1])))
        self.assertFalse(is_connected(Graph()))

    def test_missing_endpoint_is_reported(self) -> None:
        with self.assertRaises(KeyError):
            breadth_first_search(self.graph, 0, 3)
        with self.assertRaises(KeyError):
            dijkstra(self.graph, 1, 9)


if __name__ == "__main__":
    unittest.main()

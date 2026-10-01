"""Defects 2 & 4: Graph/Tree strategies crash or emit invalid test cases.

Graph renders its own ``n m`` header, so a well-formed spec declares only the
Graph in ``spec.input(...)``; the bound variables are referenced by
``num_vertices`` / ``num_edges``.
"""

import random
import unittest

from framework import Problem, Integer, Graph, Tree
from framework import maximum, dense, disconnected, stress_case, random_case
from framework import chain, star, balanced, skewed, single_node
from framework.validators import validate_testcase


def graph_spec(testcases=4, max_vertices=10, max_edges=5):
    spec = Problem(name="graph", testcases=testcases)
    n = Integer(name="N", min_value=1, max_value=max_vertices)
    m = Integer(name="M", min_value=1, max_value=max_edges)
    g = Graph(name="G", num_vertices=n, num_edges=m)
    spec.input(g)
    return spec


class TestGraphStrategies(unittest.TestCase):
    def test_maximum_does_not_crash_on_graph(self):
        """strategies.maximum read v.max_value before the Graph type check."""
        spec = graph_spec(testcases=1)
        spec.add_testcases(maximum())
        cases = spec.generate_testcases(random.Random(5))
        self.assertEqual(len(cases), 1)
        self.assertEqual(validate_testcase(spec, cases[0]), [])

    def test_dense_respects_declared_num_edges(self):
        spec = graph_spec()
        spec.add_testcases(dense())
        case = spec.generate_testcases(random.Random(5))[0]
        self.assertLessEqual(
            len(case["G"]), case["G_m"],
            f"dense() emitted {len(case['G'])} edges but header says {case['G_m']}",
        )
        self.assertLessEqual(case["G_m"], 5, "must not exceed declared max edges")
        self.assertEqual(validate_testcase(spec, case), [])

    def test_dense_on_single_vertex(self):
        """dense() fell back to edge (1, 2) when n == 1."""
        spec = Problem(name="single", testcases=1)
        g = Graph(name="G", num_vertices=1, num_edges=0)
        spec.input(g)
        spec.add_testcases(dense())
        case = spec.generate_testcases(random.Random(5))[0]
        self.assertEqual(validate_testcase(spec, case), [])

    def test_disconnected_on_single_vertex(self):
        """disconnected() produced vertex 2 for n == 1."""
        spec = Problem(name="single-disc", testcases=1)
        g = Graph(name="G", num_vertices=1, num_edges=0)
        spec.input(g)
        spec.add_testcases(disconnected())
        case = spec.generate_testcases(random.Random(5))[0]
        self.assertEqual(validate_testcase(spec, case), [])

    def test_validator_reports_edge_count_mismatch(self):
        spec = graph_spec()
        case = {"G": [(1, 2), (2, 3)], "G_n": 5, "G_m": 3}
        errors = validate_testcase(spec, case)
        self.assertTrue(
            any("edge" in e.lower() for e in errors),
            f"expected an edge-count error, got {errors}",
        )

    def test_validator_reports_edge_count_exceeding_declaration(self):
        spec = Problem(name="declared", testcases=1)
        g = Graph(name="G", num_vertices=5, num_edges=2)
        spec.input(g)
        case = {"G": [(1, 2), (2, 3), (3, 4)], "G_n": 5, "G_m": 3}
        errors = validate_testcase(spec, case)
        self.assertTrue(
            any("num_edges" in e or "declared" in e.lower() for e in errors),
            f"expected a declared-num_edges error, got {errors}",
        )

    def test_validator_reports_vertex_out_of_range(self):
        spec = graph_spec()
        case = {"G": [(1, 9)], "G_n": 3, "G_m": 1}
        errors = validate_testcase(spec, case)
        self.assertTrue(errors, "out-of-range vertex must be reported")

    def test_stress_does_not_exceed_declared_maxima(self):
        spec = graph_spec(testcases=3, max_vertices=6, max_edges=6)
        spec.add_testcases(stress_case())
        for case in spec.generate_testcases(random.Random(5)):
            self.assertLessEqual(case["G_n"], 6, "stress must respect max vertices")
            self.assertLessEqual(case["G_m"], 6, "stress must respect max edges")
            self.assertEqual(validate_testcase(spec, case), [])

    def test_tree_strategies_produce_valid_trees(self):
        spec = Problem(name="tree", testcases=5)
        n = Integer(name="N", min_value=1, max_value=20)
        t = Tree(name="T", num_vertices=n)
        spec.input(t)
        spec.add_testcases(chain(), star(), balanced(), skewed(), single_node())
        for case in spec.generate_testcases(random.Random(5)):
            self.assertEqual(validate_testcase(spec, case), [])

    def test_random_case_strategy_runs_on_graph(self):
        spec = graph_spec()
        spec.add_testcases(random_case())
        cases = spec.generate_testcases(random.Random(5))
        self.assertEqual(validate_testcase(spec, cases[0]), [])


if __name__ == "__main__":
    unittest.main()

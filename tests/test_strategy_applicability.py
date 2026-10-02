"""Task 6: strategies declare when they cannot express their intent."""

import contextlib
import io
import random
import tempfile
import unittest
from pathlib import Path

import generate_tests
from framework import Problem, Integer, Array, String, Graph
from framework import (
    minimum, maximum, random_case, mixed_signs, duplicates, increasing,
    stress_case, palindrome, chain,
)


def pinned_size_spec(testcases=6, min_value=1):
    spec = Problem(name="pinned", testcases=testcases)
    n = Integer(name="N", min_value=1, max_value=20)
    a = Array(name="A", size=n, min_value=min_value, max_value=50)
    spec.input(n, a)
    return spec


class TestApplicabilityChecks(unittest.TestCase):
    def test_unconditional_strategies_are_always_applicable(self):
        spec = pinned_size_spec()
        self.assertIsNone(spec.strategy_applicability(minimum()))
        self.assertIsNone(spec.strategy_applicability(maximum()))
        self.assertIsNone(spec.strategy_applicability(random_case()))

    def test_mixed_signs_needs_a_negative_minimum(self):
        reason = pinned_size_spec(min_value=1).strategy_applicability(mixed_signs())
        self.assertIsNotNone(reason)
        self.assertIn("negative minimum", reason)

        negative = pinned_size_spec(min_value=-5)
        self.assertIsNone(negative.strategy_applicability(mixed_signs()))

    def test_duplicates_needs_an_array_of_three_or_more(self):
        small = Problem(name="small", testcases=3)
        small.input(Array(name="A", size=2, min_value=1, max_value=10))
        reason = small.strategy_applicability(duplicates())
        self.assertIsNotNone(reason)
        self.assertIn("size is at least 3", reason)

        large = Problem(name="large", testcases=3)
        large.input(Array(name="A", size=10, min_value=1, max_value=10))
        self.assertIsNone(large.strategy_applicability(duplicates()))

    def test_increasing_needs_an_array(self):
        scalar = Problem(name="scalar", testcases=3)
        scalar.input(Integer(name="N", min_value=1, max_value=10))
        reason = scalar.strategy_applicability(increasing())
        self.assertIsNotNone(reason)
        self.assertIn("increasing", reason)
        self.assertIn("array", reason)

        array = Problem(name="array", testcases=3)
        array.input(Array(name="A", size=5, min_value=1, max_value=10))
        self.assertIsNone(array.strategy_applicability(increasing()))

    def test_stress_case_is_flagged_when_the_size_is_pinned(self):
        reason = pinned_size_spec().strategy_applicability(stress_case())
        self.assertIsNotNone(reason)
        self.assertIn("stress_case", reason)

        free = Problem(name="free", testcases=3)
        free.input(Array(name="A", min_size=1, max_size=12, min_value=1, max_value=9))
        self.assertIsNone(free.strategy_applicability(stress_case()))

        graph = Problem(name="graph", testcases=3)
        graph.input(Graph(name="G", num_vertices=5, num_edges=4))
        self.assertIsNone(graph.strategy_applicability(stress_case()))

    def test_string_strategies_need_a_string_variable(self):
        spec = pinned_size_spec()
        reason = spec.strategy_applicability(palindrome())
        self.assertIsNotNone(reason)
        self.assertIn("palindrome", reason)
        self.assertIn("String", reason)

        strings = Problem(name="strings", testcases=3)
        strings.input(String(name="S", length=8))
        self.assertIsNone(strings.strategy_applicability(palindrome()))

    def test_graph_strategies_need_a_graph_variable(self):
        spec = pinned_size_spec()
        reason = spec.strategy_applicability(chain())
        self.assertIsNotNone(reason)
        self.assertIn("chain", reason)
        self.assertIn("Graph", reason)


class TestInapplicableStrategiesInGeneration(unittest.TestCase):
    def test_degenerate_strategy_is_skipped_and_count_stays_exact(self):
        spec = pinned_size_spec(testcases=6, min_value=1)
        spec.add_testcases(
            minimum(), maximum(), random_case(),
            mixed_signs(), random_case(), random_case(),
        )

        with self.assertLogs("framework.problem", level="WARNING") as logs:
            cases = spec.generate_testcases(random.Random(3))

        self.assertEqual(len(cases), 6, "count must stay exact after a skip")
        self.assertNotIn(
            "mixed_signs",
            {c["__strategy__"] for c in cases},
            "an inapplicable strategy must not contribute cases",
        )
        self.assertTrue(
            any("mixed_signs" in m and "negative minimum" in m for m in logs.output),
            f"warning must name the strategy and the reason: {logs.output}",
        )

    def test_applicable_strategies_are_deterministic(self):
        spec = Problem(name="free", testcases=6)
        spec.input(
            Integer(name="N", min_value=1, max_value=12),
            Array(name="A", min_size=1, max_size=12, min_value=-9, max_value=9),
        )
        spec.add_testcases(
            minimum(), maximum(), increasing(), mixed_signs(),
            duplicates(), random_case(),
        )

        first = [
            spec.render_testcase(c)
            for c in spec.generate_testcases(random.Random(11))
        ]
        second = [
            spec.render_testcase(c)
            for c in spec.generate_testcases(random.Random(11))
        ]

        self.assertEqual(len(first), 6)
        self.assertEqual(first, second)


class TestDryRunApplicability(unittest.TestCase):
    def _contest(self, tmp):
        problem = Path(tmp) / "Contest" / "P1"
        problem.mkdir(parents=True)
        (problem / "spec.py").write_text(
            "from framework import *\n"
            "spec = Problem(name='PositiveOnly', testcases=4)\n"
            "N = Integer(name='N', min_value=1, max_value=20)\n"
            "A = Array(name='A', size=N, min_value=1, max_value=50)\n"
            "spec.input(N, A)\n"
            "spec.add_testcases(minimum(), mixed_signs(), stress_case(),\n"
            "                   random_case())\n",
            encoding="utf-8",
        )
        return Path(tmp) / "Contest"

    def test_dry_run_flags_each_inapplicable_strategy(self):
        with tempfile.TemporaryDirectory() as tmp:
            contest = self._contest(tmp)
            out = io.StringIO()
            with contextlib.redirect_stdout(out), \
                    self.assertLogs(level="WARNING") as logs:
                ok = generate_tests.dry_run(
                    contest, show_applicability=True, seed=1
                )
            text = out.getvalue()

        self.assertTrue(ok)
        self.assertIn("no", text)
        self.assertIn("mixed_signs", text)
        self.assertIn("stress_case", text)
        self.assertIn("yes", text)
        self.assertIn("minimum", text)

        joined = "\n".join(logs.output)
        self.assertIn("mixed_signs: not applicable:", joined)
        self.assertIn("negative minimum", joined)
        self.assertIn("stress_case: not applicable:", joined)


if __name__ == "__main__":
    unittest.main()

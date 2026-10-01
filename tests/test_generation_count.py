"""Defect 1: generation silently returns fewer cases than spec.testcases."""

import random
import unittest

from framework import (
    Problem, Integer, Array,
    minimum, maximum, all_equal, random_case,
)


class TestGenerationCount(unittest.TestCase):
    def test_degenerate_strategies_cannot_reach_count(self):
        """A spec whose value domain is smaller than testcases must fail loudly.

        Previously ``generate_testcases`` dropped duplicates without retrying and
        returned 2 cases for a request of 10, with no error anywhere downstream.
        """
        spec = Problem(name="tiny-domain", testcases=10)
        x = Integer(name="X", min_value=1, max_value=2)
        spec.input(x)
        spec.add_testcases(minimum(), minimum(), maximum(), all_equal(), all_equal())

        with self.assertRaises(RuntimeError) as ctx:
            spec.generate_testcases(random.Random(3))

        message = str(ctx.exception)
        self.assertIn("10", message, "error must state the requested count")
        self.assertIn("2", message, "error must state how many were produced")

    def test_reachable_count_is_exactly_requested(self):
        """Distinct-value strategies must still deliver exactly testcases cases."""
        spec = Problem(name="reachable", testcases=10)
        x = Integer(name="X", min_value=1, max_value=1000)
        spec.input(x)
        spec.add_testcases(minimum(), maximum(), all_equal())

        cases = spec.generate_testcases(random.Random(3))
        self.assertEqual(len(cases), 10)

    def test_every_case_records_its_origin(self):
        """Each case must name the strategy that produced it."""
        spec = Problem(name="named", testcases=4)
        x = Integer(name="X", min_value=1, max_value=1000)
        spec.input(x)
        spec.add_testcases(minimum(), maximum())

        cases = spec.generate_testcases(random.Random(3))
        for case in cases:
            self.assertIn("__strategy__", case)

    def test_array_spec_delivers_requested_count(self):
        """Array specs with repeated random_case() must not undershoot."""
        spec = Problem(name="two-sum", testcases=15)
        n = Integer(name="N", min_value=2, max_value=20)
        target = Integer(name="Target", min_value=1, max_value=100)
        a = Array(name="A", size=n, min_value=1, max_value=50)
        spec.input(n, target, a)
        spec.add_testcases(
            minimum(), maximum(), all_equal(),
            random_case(), random_case(),
        )

        cases = spec.generate_testcases(random.Random(1))
        self.assertEqual(len(cases), 15)

    def test_custom_cases_do_not_overshoot_count(self):
        """More registered cases than spec.testcases must not add extras."""
        spec = Problem(name="overflow", testcases=2)
        x = Integer(name="X", min_value=1, max_value=1000)
        spec.input(x)
        spec.add_custom_case(lambda rng: {"X": 1})
        spec.add_custom_case(lambda rng: {"X": 2})
        spec.add_custom_case(lambda rng: {"X": 3})

        cases = spec.generate_testcases(random.Random(1))
        self.assertEqual(len(cases), 2)


if __name__ == "__main__":
    unittest.main()

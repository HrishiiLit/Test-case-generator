"""Task 7: semantic redundancy is detected, reported and hard-fails."""

import random
import unittest

import generate_tests
from framework import Problem, Integer, Array


def _spec(testcases=2, n=5, lo=1, hi=50):
    spec = Problem(name="redundant", testcases=testcases)
    spec.input(
        Integer(name="N", min_value=n, max_value=n),
        Array(name="A", size=n, min_value=lo, max_value=hi),
    )
    return spec


class TestRedundancyHardFail(unittest.TestCase):
    def test_constant_arrays_with_the_same_n_abort(self):
        spec = _spec()

        def case_ones(rng):
            return {"N": 5, "A": [1] * 5}

        def case_twos(rng):
            return {"N": 5, "A": [2] * 5}

        spec.add_custom_case(case_ones)
        spec.add_custom_case(case_twos)

        with self.assertRaises(RuntimeError) as ctx:
            spec.generate_testcases(random.Random(1))

        message = str(ctx.exception)
        self.assertIn("redundant", message)
        self.assertIn("case_ones", message)
        self.assertIn("case_twos", message)
        self.assertIn("allow_redundant", message)

    def test_identical_rendered_input_is_reported_with_both_names(self):
        spec = _spec(testcases=2)

        def case_alpha(rng):
            return {"N": 5, "A": [1] * 5}

        def case_beta(rng):
            return {"N": 5, "A": [1] * 5}

        spec.add_custom_case(case_alpha)
        spec.add_custom_case(case_beta)

        cases = spec.generate_testcases(random.Random(1))
        self.assertEqual(len(cases), 2, "the duplicate must be replaced, not kept")

        flags = spec.redundancy_flags
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0]["kind"], "duplicate")
        self.assertIn("case_alpha", flags[0]["second"])
        self.assertIn("case_beta", flags[0]["first"])
        self.assertIn("identical rendered input", flags[0]["detail"])

    def test_single_element_arrays_are_not_redundant(self):
        spec = _spec(testcases=2, n=1, lo=1, hi=10)

        def case_three(rng):
            return {"N": 1, "A": [3]}

        def case_seven(rng):
            return {"N": 1, "A": [7]}

        spec.add_custom_case(case_three)
        spec.add_custom_case(case_seven)

        cases = spec.generate_testcases(random.Random(1))
        self.assertEqual(len(cases), 2)
        self.assertEqual(spec.redundancy_flags, [])

    def test_allow_redundant_keeps_intentional_repeats(self):
        spec = _spec()
        spec.allow_redundant = True

        def case_ones(rng):
            return {"N": 5, "A": [1] * 5}

        def case_twos(rng):
            return {"N": 5, "A": [2] * 5}

        spec.add_custom_case(case_ones)
        spec.add_custom_case(case_twos)

        cases = spec.generate_testcases(random.Random(1))
        self.assertEqual(len(cases), 2)
        self.assertEqual(spec.redundancy_flags, [])

    def test_report_lists_the_colliding_strategy_names(self):
        spec = _spec(testcases=2)

        def case_alpha(rng):
            return {"N": 5, "A": [1] * 5}

        def case_beta(rng):
            return {"N": 5, "A": [1] * 5}

        spec.add_custom_case(case_alpha)
        spec.add_custom_case(case_beta)

        cases = spec.generate_testcases(random.Random(1))
        rows = generate_tests.build_report_rows(spec, [], cases)
        text = generate_tests.format_report(spec, rows)

        self.assertIn("redundancy:", text)
        self.assertIn("case_alpha", text)
        self.assertIn("case_beta", text)
        self.assertIn("identical rendered input", text)


if __name__ == "__main__":
    unittest.main()

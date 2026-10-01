"""Defects 5 & 6: sample test cases are unvalidated and failures are opaque."""

import random
import tempfile
import unittest
from pathlib import Path

from framework import Problem, Integer, Array, random_case
from framework.validators import validate_testcase

import generate_tests


VALID_SPEC = '''\
from framework import *

spec = Problem(name="TwoSum", testcases=3)
N = Integer(name="N", min_value=1, max_value=10)
Target = Integer(name="Target", min_value=1, max_value=100)
A = Array(name="A", size=N, min_value=1, max_value=50)
spec.input(N, Target, A)
spec.add_testcases(random_case())
'''

HIGH_RANGE_SPEC = '''\
from framework import *

spec = Problem(name="HighRange", testcases=3)
N = Integer(name="N", min_value=100, max_value=500)
A = Array(name="A", size=N, min_value=1000, max_value=100000)
spec.input(N, A)
spec.add_testcases(random_case())
'''

INVALID_SAMPLE_SPEC = HIGH_RANGE_SPEC + '''\
def _bad_sample(rng):
    return {"N": 999, "A": [1]}

spec._sample_minimum = _bad_sample
'''

CRASHING_SOLUTION = '''\
#include <iostream>
int main() { return 1; }
'''


def build_problem(tmp, spec_text, with_solution=False):
    prob = Path(tmp) / "P1"
    prob.mkdir()
    (prob / "spec.py").write_text(spec_text, encoding="utf-8")
    if with_solution:
        (prob / "solution.cpp").write_text(CRASHING_SOLUTION, encoding="utf-8")
    return prob


class SampleGenerationTest(unittest.TestCase):
    def test_samples_are_valid_and_complete(self):
        """Sample cases must satisfy the spec's own constraints and count."""
        spec = Problem(name="HighRange", testcases=3)
        n = Integer(name="N", min_value=100, max_value=500)
        a = Array(name="A", size=n, min_value=1000, max_value=100000)
        spec.input(n, a)
        spec.add_testcases(random_case())

        samples = spec.generate_sample_testcases(random.Random(1), count=3)

        self.assertEqual(len(samples), 3, f"got {len(samples)} samples")
        for index, values in enumerate(samples, 1):
            errors = validate_testcase(spec, values)
            self.assertEqual(
                errors, [], f"sample {index} violates the spec: {errors}"
            )

    def test_invalid_sample_aborts_generation(self):
        """process_problem must validate samples before writing them."""
        with tempfile.TemporaryDirectory() as tmp:
            prob = build_problem(tmp, INVALID_SAMPLE_SPEC)

            with self.assertRaises(RuntimeError) as ctx:
                generate_tests.process_problem(
                    prob, seed=12345, timeout=5, no_solve=True, keep=False
                )

            self.assertIn("ample", str(ctx.exception))

    def test_failed_solution_reports_the_sample(self):
        """A crashing solution must fail naming the sample, not a size check."""
        with tempfile.TemporaryDirectory() as tmp:
            prob = build_problem(tmp, VALID_SPEC, with_solution=True)

            with self.assertRaises(RuntimeError) as ctx:
                generate_tests.process_problem(
                    prob, seed=12345, timeout=5, no_solve=False, keep=False
                )

            message = str(ctx.exception)
            self.assertIn("solution failed", message)
            self.assertIn("sample", message.lower())

    def test_no_empty_output_file_is_written(self):
        """Sample failures must not leave an empty file behind for a later check."""
        with tempfile.TemporaryDirectory() as tmp:
            prob = build_problem(tmp, VALID_SPEC, with_solution=True)

            with self.assertRaises(RuntimeError):
                generate_tests.process_problem(
                    prob, seed=12345, timeout=5, no_solve=False, keep=False
                )

            outputs = list((prob / "testcases").glob("*.txt"))
            empty = [f.name for f in outputs if f.stat().st_size == 0]
            self.assertEqual(empty, [], f"empty files written: {empty}")


if __name__ == "__main__":
    unittest.main()

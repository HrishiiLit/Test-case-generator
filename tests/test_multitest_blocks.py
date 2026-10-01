"""Defect 3: multi-test expansion hardcodes the count variable name ``T``."""

import random
import unittest

from framework import Problem, Integer, Array, Blocks, Line, random_case
from framework.validators import validate_testcase


def make_spec(count_name, testcases=3):
    spec = Problem(name=f"multi-{count_name}", testcases=testcases)
    t = Integer(name=count_name, min_value=1, max_value=100)
    n = Integer(name="n", min_value=1, max_value=10)
    a = Array(name="a", size=n, min_value=1, max_value=100)
    spec.input(t, Blocks(Line(n), a))
    spec.add_testcases(random_case())
    return spec


class TestMultiTestCountVariable(unittest.TestCase):
    def assert_consistent(self, spec, cases):
        count_name = spec._variables[0].name
        for case in cases:
            blocks = case.get("__blocks__")
            self.assertIsNotNone(blocks, "multi-test case must carry blocks")
            declared = case.get(count_name)
            self.assertEqual(
                declared, len(blocks),
                f"{count_name}={declared} but {len(blocks)} blocks rendered",
            )
            rendered = spec.render_testcase(case)
            first_line = rendered.splitlines()[0].split()
            self.assertEqual(int(first_line[0]), len(blocks))

    def test_uppercase_t(self):
        spec = make_spec("T")
        cases = spec.generate_testcases(random.Random(7))
        self.assert_consistent(spec, cases)

    def test_lowercase_t_as_documented_in_prompt(self):
        """PROMPT.md documents ``t = Integer(name="t", ...)`` with Blocks."""
        spec = make_spec("t")
        cases = spec.generate_testcases(random.Random(7))
        self.assert_consistent(spec, cases)

    def test_validator_reports_mismatched_block_count(self):
        spec = make_spec("t")
        case = spec.generate_testcases(random.Random(7))[0]
        case["__blocks__"] = case["__blocks__"][:1]
        case["t"] = 5
        errors = validate_testcase(spec, case)
        self.assertTrue(
            any("blocks" in e for e in errors),
            f"expected a block-count error, got {errors}",
        )

    def test_rendered_input_has_declared_block_count(self):
        """Header value and rendered blocks must agree in the written input."""
        spec = make_spec("t")
        case = spec.generate_testcases(random.Random(7))[0]
        block = case["__blocks__"][0]
        case["__blocks__"] = [dict(block) for _ in range(4)]
        case["t"] = 4

        self.assertEqual(validate_testcase(spec, case), [])

        rendered = spec.render_testcase(case)
        lines = rendered.splitlines()
        self.assertEqual(lines[0], "4")
        self.assertEqual(len(lines), 1 + 2 * 4)


if __name__ == "__main__":
    unittest.main()

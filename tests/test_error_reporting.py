"""Defect 7: generation retries swallow the underlying error."""

import random
import unittest

from framework import Problem, Integer


class TestErrorReporting(unittest.TestCase):
    def test_failing_custom_case_logs_the_cause(self):
        """The first failing attempt must be logged with its root cause."""
        def boom(rng):
            raise ValueError("exploded while building the case")

        spec = Problem(name="boom", testcases=2)
        spec.input(Integer(name="X", min_value=1, max_value=10))
        spec.add_custom_case(boom)

        with self.assertLogs(level="WARNING") as captured:
            with self.assertRaises(RuntimeError) as ctx:
                spec.generate_testcases(random.Random(1))

        joined = "\n".join(captured.output)
        self.assertIn("exploded while building the case", joined)
        self.assertIn("exploded while building the case", str(ctx.exception))

    def test_failure_names_the_case_origin(self):
        """Errors must say which strategy or custom case failed."""

        def boom(rng):
            raise ValueError("nope")

        spec = Problem(name="boom", testcases=2)
        spec.input(Integer(name="X", min_value=1, max_value=10))
        spec.add_custom_case(boom)

        with self.assertRaises(RuntimeError) as ctx:
            spec.generate_testcases(random.Random(1))

        message = str(ctx.exception)
        self.assertTrue(
            "custom" in message.lower() or "case" in message.lower(),
            f"error must name the failing origin: {message}",
        )

    def test_valid_generation_emits_no_warnings(self):
        spec = Problem(name="fine", testcases=3)
        spec.input(Integer(name="X", min_value=1, max_value=1000))

        with self.assertRaises(AssertionError):
            with self.assertLogs(level="WARNING"):
                spec.generate_testcases(random.Random(1))

    def test_variable_range_reported_when_impossible(self):
        """An unreachable request must explain the domain is too small."""
        spec = Problem(name="tiny", testcases=5)
        spec.input(Integer(name="X", min_value=1, max_value=1))

        with self.assertLogs(level="WARNING") as captured:
            cases = spec.generate_testcases(random.Random(1))

        message = "\n".join(captured.output)
        self.assertEqual(len(cases), 1, "the single distinct case is kept")
        self.assertIn("X", message)
        self.assertIn("1", message)


if __name__ == "__main__":
    unittest.main()

"""Task 5: --report must expose index, strategy, shape and status per case."""

import contextlib
import io
import random
import tempfile
import unittest
from pathlib import Path

import generate_tests
from framework import Problem, Integer, Array
from framework import maximum, all_equal, random_case

REPO_ROOT = Path(__file__).resolve().parent.parent


def two_sum_spec(testcases=6):
    spec = Problem(name="Two Sum", testcases=testcases)
    n = Integer(name="N", min_value=2, max_value=20)
    target = Integer(name="Target", min_value=1, max_value=100)
    a = Array(name="A", size=n, min_value=1, max_value=50)
    spec.input(n, target, a)
    spec.add_testcases(maximum(), all_equal(), random_case())
    return spec


class TestReportRows(unittest.TestCase):
    def test_rows_carry_index_strategy_shape_and_status(self):
        spec = two_sum_spec()
        cases = spec.generate_testcases(random.Random(7))
        rows = generate_tests.build_report_rows(spec, [], cases)

        self.assertEqual(len(rows), len(cases))
        for index, row in enumerate(rows, 1):
            self.assertEqual(row["index"], index)
            self.assertEqual(row["name"], f"testcase {index}")
            self.assertTrue(row["strategy"], "row must name its strategy")
            self.assertTrue(row["shape"], "row must carry a shape signature")
            self.assertEqual(row["status"], "valid")
        self.assertIn("maximum", {r["strategy"] for r in rows})

    def test_shape_signature_classifies_arrays(self):
        spec = two_sum_spec(testcases=1)

        def shape(values):
            return spec.shape_signature(
                {"N": len(values["A"]), "Target": 7, **values}
            )

        self.assertEqual(shape({"A": [9, 9, 9, 9, 9]}), "constant")
        self.assertEqual(shape({"A": [1, 2, 3, 4, 5]}), "sorted")
        self.assertEqual(shape({"A": [5, 4, 3, 2, 1]}), "reverse-sorted")
        self.assertEqual(shape({"A": [1, 2, 1, 2]}), "repeated")
        self.assertEqual(shape({"A": [3, 1, 4, 1, 5]}), "random")

    def test_report_renders_one_row_per_case(self):
        spec = two_sum_spec()
        cases = spec.generate_testcases(random.Random(7))
        rows = generate_tests.build_report_rows(spec, [], cases)
        text = generate_tests.format_report(spec, rows)

        lines = text.splitlines()
        self.assertIn("strategy", lines[0])
        self.assertIn("shape", lines[0])
        self.assertIn("status", lines[0])
        body = [line for line in lines[2:] if line.strip()]
        self.assertEqual(len(body), len(rows))
        for row in rows:
            self.assertIn(row["strategy"], text)


class TestReportFromDryRun(unittest.TestCase):
    def _contest(self, tmp):
        problem = Path(tmp) / "Contest" / "P1"
        problem.mkdir(parents=True)
        (problem / "spec.py").write_text(
            "from framework import *\n"
            "spec = Problem(name='TwoSum', testcases=4)\n"
            "N = Integer(name='N', min_value=1, max_value=20)\n"
            "A = Array(name='A', size=N, min_value=1, max_value=50)\n"
            "spec.input(N, A)\n"
            "spec.add_testcases(maximum(), all_equal(), random_case())\n",
            encoding="utf-8",
        )
        return Path(tmp) / "Contest"

    def test_report_works_without_compiling(self):
        with tempfile.TemporaryDirectory() as tmp:
            contest = self._contest(tmp)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                ok = generate_tests.dry_run(
                    contest, report=True, show_applicability=True, seed=1
                )
            text = out.getvalue()

        self.assertTrue(ok)
        self.assertIn("Solution: MISSING", text)
        self.assertIn("Report:", text)
        self.assertIn("strategy", text)
        self.assertIn("maximum", text)
        self.assertNotIn("Compiling", text)

    def test_default_dry_run_output_is_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            contest = self._contest(tmp)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                ok = generate_tests.dry_run(contest, report=False, seed=1)
            text = out.getvalue()

        self.assertTrue(ok)
        self.assertIn("Status: NO SOLUTION", text)
        self.assertNotIn("Report:", text)

    def test_problem1_report_exposes_the_constant_array_cases(self):
        spec = generate_tests.load_spec(
            REPO_ROOT / "Sample_contest" / "Problem_1" / "spec.py"
        )
        sample_cases, cases = generate_tests.generate_in_memory(spec, 12345)
        rows = generate_tests.build_report_rows(spec, sample_cases, cases)

        constant = [r for r in rows if r["shape"] == "constant"]
        self.assertGreaterEqual(
            len(constant), 3, "report must expose the constant-array cases"
        )
        self.assertLessEqual(
            {"maximum", "all_equal"},
            {r["strategy"] for r in constant},
        )


if __name__ == "__main__":
    unittest.main()

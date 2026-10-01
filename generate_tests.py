#!/usr/bin/env python3
import argparse
import importlib.util
import logging
import random
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from framework.problem import Problem, STRATEGY_KEY
from framework.validators import validate_testcase
from framework.runner import compile_cpp, run_cpp, normalize_output, cleanup_exe
from framework.zipper import create_problem_zip, verify_zip
from framework.checker import load_checker

logger = logging.getLogger(__name__)

MAX_RETRIES = 10


def setup_logging(verbose=False):
    level = logging.DEBUG if verbose else logging.INFO
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    logging.root.addHandler(handler)
    logging.root.setLevel(level)


def load_spec(spec_path):
    spec_path = Path(spec_path)
    module_name = f"spec_{spec_path.parent.name}"
    spec = importlib.util.spec_from_file_location(module_name, str(spec_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not hasattr(mod, "spec"):
        raise ValueError(f"{spec_path}: No 'spec' variable found. Must define spec = Problem(...)")
    if not isinstance(mod.spec, Problem):
        raise ValueError(f"{spec_path}: 'spec' must be a Problem instance, got {type(mod.spec).__name__}")
    return mod.spec


def discover_problems(contest_dir, problem_filter=None, require_solution=True):
    contest_dir = Path(contest_dir)
    if not contest_dir.is_dir():
        raise FileNotFoundError(f"Contest folder not found: {contest_dir}")

    problems = []
    for entry in sorted(contest_dir.iterdir()):
        if not entry.is_dir():
            continue
        if problem_filter and entry.name != problem_filter:
            continue
        solution = entry / "solution.cpp"
        spec_file = entry / "spec.py"
        if require_solution and not solution.exists():
            logger.warning(f"Skipping {entry.name}: no solution.cpp")
            continue
        if not spec_file.exists():
            logger.warning(f"Skipping {entry.name}: no spec.py")
            continue
        problems.append(entry)

    if not problems:
        if problem_filter:
            raise FileNotFoundError(f"Problem '{problem_filter}' not found in {contest_dir}")
        raise FileNotFoundError(f"No valid problems found in {contest_dir}")

    return problems


def normalize_input(text):
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if text and not text.endswith("\n"):
        text += "\n"
    return text


def write_testcase(spec, values, tc_dir, prefix, idx, exe_path, timeout, no_solve):
    """Write input and optionally output for a single testcase.

    Handles three kinds of *values*:
    * Normal generated case dict – rendered via ``spec.render_testcase``.
    * Literal sample dict with ``"__literal_input__"`` and ``"__literal_output__"`` keys.
    * Sample dict produced by ``Problem.generate_sample_testcases``.
    """
    # Literal sample handling
    if "__literal_input__" in values:
        input_text = normalize_input(values["__literal_input__"])
        output_text = values.get("__literal_output__")
    else:
        input_text = normalize_input(spec.render_testcase(values))
        output_text = None

    # Main cases are "input1.txt"; samples are "sample_input1.txt".
    stem = f"{prefix}_" if prefix else ""
    input_file = tc_dir / f"{stem}input{idx}.txt"
    with open(input_file, "w", newline="\n") as f:
        f.write(input_text)

    if no_solve or exe_path is None:
        return

    if output_text is None:
        # Normal case – run solution to obtain output.
        try:
            stdout = run_cpp(exe_path, input_file, timeout=timeout)
            output_text = normalize_output(stdout)
        except Exception as e:
            label = "Sample testcase" if prefix == "sample" else "Testcase"
            raise RuntimeError(f"{label} {idx} solution failed: {e}") from e
    else:
        # Literal sample – output already provided.
        pass

    output_file = tc_dir / f"{stem}output{idx}.txt"
    with open(output_file, "w", newline="\n") as f:
        f.write(output_text)


def case_status(spec, values):
    """Validity verdict for one case: ``valid`` or the first violated constraint."""
    try:
        errors = validate_testcase(spec, values)
    except Exception as e:
        return f"error: {type(e).__name__}: {e}"
    if errors:
        return errors[0]
    return "valid"


def build_report_rows(spec, sample_cases, cases):
    """One row per generated case: index, name, strategy, shape, status."""
    rows = []
    index = 0
    for entries, label in ((sample_cases, "sample"), (cases, "testcase")):
        for i, values in enumerate(entries, 1):
            index += 1
            rows.append(
                {
                    "index": index,
                    "name": f"{label} {i}",
                    "strategy": values.get(STRATEGY_KEY, "unknown"),
                    "shape": spec.shape_signature(values),
                    "status": case_status(spec, values),
                }
            )
    return rows


def format_report(spec, rows):
    """Render report rows as an aligned table plus any redundancy findings."""
    headers = ("#", "case", "strategy", "shape", "status")
    keys = ("index", "name", "strategy", "shape", "status")
    widths = [
        max(len(h), *(len(str(r[k])) for r in rows)) if rows else len(h)
        for h, k in zip(headers, keys)
    ]

    def line(values):
        return "  ".join(str(v).ljust(w) for v, w in zip(values, widths)).rstrip()

    out = [line(headers), line("-" * w for w in widths)]
    out.extend(line(r[k] for k in keys) for r in rows)

    flags = spec.redundancy_flags
    if flags:
        out.append("")
        out.append("redundancy:")
        for f in flags:
            out.append(
                f"  - {f['kind']}: '{f['first']}' and '{f['second']}' - {f['detail']}"
            )
    return "\n".join(out) + "\n"


def generate_in_memory(spec, seed):
    """Produce sample and main cases without compiling or writing anything."""
    sample_rng = random.Random(seed + 9999)
    sample_cases = spec.generate_sample_testcases(sample_rng, count=3, max_lines=15)
    sample_sigs = set(spec._case_signature(v) for v in sample_cases)
    cases = spec.generate_testcases(
        random.Random(seed), max_retries=MAX_RETRIES, external_seen=sample_sigs
    )
    return sample_cases, cases


def process_problem(prob_dir, seed, timeout, no_solve, keep, report=False):
    pid = prob_dir.name
    logger.info(f"Processing: {pid}")

    spec = load_spec(prob_dir / "spec.py")
    logger.info(f"  Name: {spec.name}")
    logger.info(f"  Testcases: {spec.testcases}")
    logger.info(f"  Variables: {len(spec._variables)}")

    tc_dir = prob_dir / "testcases"
    if tc_dir.exists():
        shutil.rmtree(tc_dir)
    tc_dir.mkdir(parents=True, exist_ok=True)

    exe_path = None
    if not no_solve:
        try:
            exe_path = compile_cpp(prob_dir / "solution.cpp", work_dir=prob_dir)
        except Exception as e:
            raise RuntimeError(f"solution failed: {e}") from e

    sample_cases, cases = generate_in_memory(spec, seed)
    sample_sigs = set(spec._case_signature(v) for v in sample_cases)
    logger.info(f"  Generating {len(sample_cases)} sample testcases")

    for i, values in enumerate(sample_cases, 1):
        errors = validate_testcase(spec, values)
        if errors:
            raise RuntimeError(
                f"Sample testcase {i} validation failed:\n"
                + "\n".join(f"  - {e}" for e in errors)
            )
        logger.info(f"  Generating sample testcase {i}/{len(sample_cases)}")
        write_testcase(spec, values, tc_dir, "sample", i, exe_path, timeout, no_solve)

    for i, values in enumerate(cases, 1):
        logger.info(f"  Generating testcase {i}/{len(cases)}")

        errors = validate_testcase(spec, values)
        if errors:
            raise RuntimeError(f"Testcase {i} validation failed:\n" + "\n".join(f"  - {e}" for e in errors))

        write_testcase(spec, values, tc_dir, "", i, exe_path, timeout, no_solve)

    if report:
        text = format_report(spec, build_report_rows(spec, sample_cases, cases))
        (prob_dir / "report.txt").write_text(text, newline="\n")
        print(text, end="")

    if exe_path is not None and not keep:
        cleanup_exe(exe_path)

    if not no_solve:
        all_files = list(tc_dir.glob("*.txt"))
        for f in all_files:
            if f.stat().st_size == 0:
                raise RuntimeError(f"{f.name} is empty")

        zip_path = prob_dir / f"{pid}.zip"
        # Verify checker.py exists
        checker_path = load_checker(prob_dir)
        if checker_path is None:
            logger.warning(f"  No checker.py found in {prob_dir}. Generate one using the PROMPT.md instructions.")
        create_problem_zip(tc_dir, zip_path, pid)
        in_count, out_count = verify_zip(zip_path)
        logger.info(f"  ZIP verified: {in_count} inputs, {out_count} outputs")
        logger.info(f"  ZIP created: {zip_path}")

    return True


def dry_run(contest_dir, problem_filter=None, show_applicability=False,
            report=False, seed=12345):
    contest_dir = Path(contest_dir)
    problems = discover_problems(contest_dir, problem_filter, require_solution=False)

    print(f"Contest: {contest_dir.name}")
    print(f"Problems found: {len(problems)}")
    print()

    success = True
    for prob_dir in problems:
        pid = prob_dir.name
        try:
            spec = load_spec(prob_dir / "spec.py")
            has_solution = (prob_dir / "solution.cpp").exists()
            status = "READY" if has_solution else "NO SOLUTION"
            print(f"  {pid}")
            print(f"    Name: {spec.name}")
            print(f"    Testcases: {spec.testcases}")
            print(f"    Variables: {', '.join(v.name for v in spec._variables)}")
            print(f"    Strategies: {len(spec._strategies)} + {len(spec._custom_cases)} custom")
            print(f"    Solution: {'OK' if has_solution else 'MISSING'}")
            print(f"    Status: {status}")
            if show_applicability and spec._strategies:
                print("    Strategy applicability:")
                for s in spec._strategies:
                    name = spec._origin_name(s)
                    reason = spec.strategy_applicability(s)
                    if reason is None:
                        print(f"      {name}: YES")
                    else:
                        print(f"      {name}: NO")
                        logger.warning("%s: not applicable: %s", name, reason)
            if report:
                sample_cases, cases = generate_in_memory(spec, seed)
                print("    Report:")
                print(format_report(spec, build_report_rows(spec, sample_cases, cases)), end="")
        except Exception as e:
            print(f"  {pid}")
            print(f"    Status: ERROR - {e}")
            success = False
        print()
    return success


def main():
    parser = argparse.ArgumentParser(
        description="Testcase Generator - Folder-driven competitive programming test generation"
    )
    parser.add_argument("contest", help="Contest folder name (e.g., Contest_1)")
    parser.add_argument("--problem", default=None, help="Process only this problem folder")
    parser.add_argument("--seed", type=int, default=12345, help="Random seed (default: 12345)")
    parser.add_argument("--timeout", type=int, default=30, help="Solution timeout in seconds (default: 30)")
    parser.add_argument("--dry-run", action="store_true", help="Show problem summary without generating")
    parser.add_argument("--no-solve", action="store_true", help="Generate inputs only, skip solution execution")
    parser.add_argument("--keep", action="store_true", help="Keep the compiled solution executable")
    parser.add_argument("--report", action="store_true", help="Print a per-case report and write report.txt")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()

    setup_logging(verbose=args.verbose)

    contest_dir = Path(args.contest)
    if not contest_dir.is_absolute():
        contest_dir = Path.cwd() / contest_dir

    if args.dry_run:
        try:
            success = dry_run(
                contest_dir,
                problem_filter=args.problem,
                show_applicability=True,
                report=args.report,
                seed=args.seed,
            )
            if not success:
                sys.exit(1)
        except (FileNotFoundError, ValueError) as e:
            logger.error(str(e))
            sys.exit(1)
        return

    try:
        problems = discover_problems(contest_dir, problem_filter=args.problem, require_solution=not args.no_solve)
    except (FileNotFoundError, ValueError) as e:
        logger.error(str(e))
        sys.exit(1)

    logger.info(f"Contest: {contest_dir.name}")
    logger.info(f"Problems: {len(problems)}")
    logger.info(f"Seed: {args.seed}")

    for prob_dir in problems:
        try:
            process_problem(
                prob_dir, args.seed, args.timeout, args.no_solve, args.keep,
                report=args.report,
            )
        except Exception as e:
            logger.error(f"Failed: {prob_dir.name}: {e}")
            sys.exit(1)

    logger.info("Generation complete")


if __name__ == "__main__":
    main()

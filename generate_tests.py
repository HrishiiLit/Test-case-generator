#!/usr/bin/env python3
import argparse
import importlib.util
import logging
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from framework.problem import Problem
from framework.validators import validate_testcase
from framework.runner import compile_cpp, run_cpp, normalize_output, cleanup_exe
from framework.zipper import create_problem_zip, verify_zip

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


def process_problem(prob_dir, seed, timeout, no_solve, keep):
    pid = prob_dir.name
    logger.info(f"Processing: {pid}")

    spec = load_spec(prob_dir / "spec.py")
    logger.info(f"  Name: {spec.name}")
    logger.info(f"  Testcases: {spec.testcases}")
    logger.info(f"  Variables: {len(spec._variables)}")

    tc_dir = prob_dir / "testcases"
    if tc_dir.exists():
        import shutil
        shutil.rmtree(tc_dir)
    tc_dir.mkdir(parents=True, exist_ok=True)

    exe_path = None
    if not no_solve:
        exe_path = compile_cpp(prob_dir / "solution.cpp", work_dir=prob_dir)

    rng = random.Random(seed)
    cases = spec.generate_testcases(rng, max_retries=MAX_RETRIES)

    for i, values in enumerate(cases, 1):
        logger.info(f"  Generating testcase {i}/{len(cases)}")

        errors = validate_testcase(spec, values)
        if errors:
            raise RuntimeError(f"Testcase {i} validation failed:\n" + "\n".join(f"  - {e}" for e in errors))

        input_text = normalize_input(spec.render_testcase(values))
        input_file = tc_dir / f"input{i}.txt"
        with open(input_file, "w", newline="\n") as f:
            f.write(input_text)

        if not no_solve and exe_path is not None:
            logger.info(f"  Running solution on testcase {i}")
            try:
                stdout = run_cpp(exe_path, input_file, timeout=timeout)
                output_text = normalize_output(stdout)
            except Exception as e:
                raise RuntimeError(f"Testcase {i} solution failed: {e}")

            output_file = tc_dir / f"output{i}.txt"
            with open(output_file, "w", newline="\n") as f:
                f.write(output_text)

    if exe_path is not None and not keep:
        cleanup_exe(exe_path)

    if not no_solve:
        for i in range(1, len(cases) + 1):
            inp = tc_dir / f"input{i}.txt"
            out = tc_dir / f"output{i}.txt"
            if not inp.exists():
                raise RuntimeError(f"Missing {inp.name}")
            if not out.exists():
                raise RuntimeError(f"Missing {out.name}")
            if inp.stat().st_size == 0:
                raise RuntimeError(f"{inp.name} is empty")
            if out.stat().st_size == 0:
                raise RuntimeError(f"{out.name} is empty")

        zip_path = prob_dir / f"{pid}.zip"
        create_problem_zip(tc_dir, zip_path, pid)
        in_count, out_count = verify_zip(zip_path)
        logger.info(f"  ZIP verified: {in_count} inputs, {out_count} outputs")
        logger.info(f"  ZIP created: {zip_path}")

    return True


def dry_run(contest_dir, problem_filter=None):
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
            print(f"    ZIP: {prob_dir / f'{pid}.zip'}")
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
    parser.add_argument("--timeout", type=int, default=5, help="Solution timeout in seconds (default: 5)")
    parser.add_argument("--dry-run", action="store_true", help="Show problem summary without generating")
    parser.add_argument("--no-solve", action="store_true", help="Generate inputs only, skip solution execution")
    parser.add_argument("--keep", action="store_true", help="Keep compiled executables")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()

    setup_logging(verbose=args.verbose)

    contest_dir = Path(args.contest)
    if not contest_dir.is_absolute():
        contest_dir = Path.cwd() / contest_dir

    if args.dry_run:
        try:
            success = dry_run(contest_dir, problem_filter=args.problem)
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
            process_problem(prob_dir, args.seed, args.timeout, args.no_solve, args.keep)
        except Exception as e:
            logger.error(f"Failed: {prob_dir.name}: {e}")
            sys.exit(1)

    logger.info("Generation complete")


if __name__ == "__main__":
    main()

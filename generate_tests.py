#!/usr/bin/env python3
import argparse
import importlib.util
import logging
import random
import shutil
import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from framework.problem import Problem, STRATEGY_KEY
from framework.validators import validate_testcase
from framework.runner import compile_cpp, run_cpp, normalize_output, cleanup_exe
from framework.zipper import create_problem_zip, verify_zip
from framework.checker import load_checker

logger = logging.getLogger(__name__)

MAX_RETRIES = 10

#: Width of the console report. Every heading rule and every aligned field is
#: measured against this, so the output stays readable in a normal terminal.
WIDTH = 68
RULE = "-" * WIDTH
TAG = 9


class ConsoleFormatter(logging.Formatter):
    """Keep library chatter aligned with the report.

    Messages from the ``framework`` package arrive mid-generation (a skipped
    strategy, a dropped case), so they are tagged and indented to sit in the
    same column as everything the CLI prints. The CLI's own lines are already
    laid out and pass through untouched.
    """

    TAG = "  note    "

    def format(self, record):
        text = super().format(record)
        if record.name == "__main__":
            return text
        wrapped = textwrap.fill(
            text, width=WIDTH, initial_indent=self.TAG, subsequent_indent=" " * 11
        )
        return wrapped


def setup_logging(verbose=False):
    level = logging.DEBUG if verbose else logging.INFO
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(ConsoleFormatter())
    logging.root.addHandler(handler)
    logging.root.setLevel(level)


class Printer:
    """Fixed-width report writer.

    Lines go to the logger by default so ``--verbose`` and log redirection keep
    working. ``dry_run`` passes ``sys.stdout`` instead, because its report is the
    product rather than progress chatter.
    """

    def __init__(self, stream=None):
        self.stream = stream

    def line(self, text=""):
        if self.stream is not None:
            self.stream.write(f"{text}\n")
            # Flush so a stdout report interleaves correctly with log lines on
            # stderr instead of appearing all at once at the end.
            self.stream.flush()
        else:
            logger.info(text)

    def banner(self, title, subtitle="", spacer=True):
        """Section heading: optional blank line, title, subtitle, then a rule."""
        if spacer:
            self.line("")
        self.line(title)
        if subtitle:
            self.line(f"  {subtitle}")
        self.line(RULE)

    def keyvalues(self, pairs, gap=4, pack_limit=18):
        """A borderless table of key/value pairs.

        Consecutive short values are packed several per row so a summary reads as
        one block; anything longer than *pack_limit* (a path, a long strategy
        count) takes a full row of its own so the packed columns never stretch.
        Input order is preserved.
        """
        cells = [(k, format_value(v)) for k, v in pairs if v not in (None, "")]
        if not cells:
            return
        key_width = max(len(k) for k, _ in cells) + 2

        def flush(run):
            if not run:
                return
            value_width = max(len(v) for _, v in run) + gap
            cell_width = key_width + value_width
            per_row = max(1, (WIDTH - 2) // cell_width)
            for start in range(0, len(run), per_row):
                chunk = run[start:start + per_row]
                self.line(
                    "".join(
                        f"  {k.ljust(key_width)}{v.ljust(value_width)}"
                        for k, v in chunk
                    ).rstrip()
                )

        run = []
        for key, value in cells:
            if len(value) > pack_limit:
                flush(run)
                run = []
                self.line(f"  {key.ljust(key_width)}{value}")
            else:
                run.append((key, value))
        flush(run)

    def table(self, headers, rows, aligns=None, indent="  "):
        """A bordered, column-aligned table.

        *aligns* holds one ``l`` or ``r`` per column; columns are padded to the
        widest cell so the body lines up on every row.
        """
        columns = list(zip(*([headers] + list(rows)))) if rows else [
            [h] for h in headers
        ]
        widths = [
            max(len(str(cell)) for cell in column) for column in columns
        ]
        aligns = aligns or ["l"] * len(headers)
        rule_char = "-"

        def render(cells):
            parts = []
            for cell, width, align in zip(cells, widths, aligns):
                text = str(cell)
                parts.append(text.rjust(width) if align == "r" else text.ljust(width))
            return (indent + "  ".join(parts)).rstrip()

        self.line(render(headers))
        self.line(indent + "  ".join(rule_char * w for w in widths))
        for row in rows:
            self.line(render(row))

    def field(self, label, value, width=14):
        """One aligned ``label   value`` line."""
        self.line(f"  {label.ljust(width)}{value}")

    def status(self, tag, message):
        """A tagged result line, e.g. ``zip`` or ``drop``."""
        self.line(f"  {tag.ljust(TAG)}{message}")

    def plain(self, message):
        """An indented line with no tag, for notes and sub-headings."""
        self.line(f"  {message}")


#: Progress output during a real generation run.
console = Printer()


def format_value(value):
    """Render a report value: booleans read as words, nothing stays hidden."""
    if isinstance(value, bool):
        return "yes" if value else "no"
    return str(value)


def display_path(path):
    """Shortest readable form of *path*: relative to the working directory."""
    path = Path(path)
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        return str(path)



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


def validate_case(spec, values):
    """Spec violations for one case; an empty list means the case is usable.

    Literal samples are verbatim text supplied by the user, so they are taken as
    written and never dropped by this check.
    """
    if "__literal_input__" in values:
        return []
    try:
        return validate_testcase(spec, values)
    except Exception as e:
        return [f"{type(e).__name__}: {e}"]


def case_status(spec, values):
    """Validity verdict for one case: ``valid`` or the first violated constraint."""
    errors = validate_case(spec, values)
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


def process_problem(prob_dir, seed, timeout, no_solve, keep, report=False,
                    position=None):
    pid = prob_dir.name
    spec = load_spec(prob_dir / "spec.py")

    heading = pid
    if position:
        heading = f"[{position}]  {pid}"
    console.banner(heading, spec.name.strip())
    console.keyvalues(
        [
            ("path", display_path(prob_dir)),
            ("testcases", spec.testcases),
            ("variables", len(spec._variables)),
            (
                "strategies",
                f"{len(spec._strategies)} built-in"
                + (
                    f", {len(spec._custom_cases)} custom"
                    if spec._custom_cases
                    else ""
                ),
            ),
        ]
    )
    console.line("")

    tc_dir = prob_dir / "testcases"
    if tc_dir.exists():
        shutil.rmtree(tc_dir)
    tc_dir.mkdir(parents=True, exist_ok=True)

    summary = {
        "problem": pid,
        "name": spec.name.strip(),
        "samples": 0,
        "cases": 0,
        "dropped": 0,
        "inputs": 0,
        "outputs": 0,
        "zip": "",
        "status": "ok",
    }

    exe_path = None
    if not no_solve:
        try:
            exe_path = compile_cpp(prob_dir / "solution.cpp", work_dir=prob_dir)
        except Exception as e:
            raise RuntimeError(f"solution failed: {e}") from e

    sample_cases, cases = generate_in_memory(spec, seed)

    dropped = 0
    written_samples = 0
    written_cases = 0

    for i, values in enumerate(sample_cases, 1):
        logger.debug(f"  sample testcase {i}/{len(sample_cases)}")
        errors = validate_case(spec, values)
        if errors:
            dropped += 1
            console.plain(
                f"drop  sample {i} ({spec.shape_signature(values)}): "
                + "; ".join(errors[:2])
            )
            continue
        write_testcase(spec, values, tc_dir, "sample", i, exe_path, timeout, no_solve)
        written_samples += 1

    for i, values in enumerate(cases, 1):
        logger.debug(f"  testcase {i}/{len(cases)}")
        errors = validate_case(spec, values)
        if errors:
            dropped += 1
            console.plain(
                f"drop  testcase {i} ({spec.shape_signature(values)}): "
                + "; ".join(errors[:2])
            )
            continue
        write_testcase(spec, values, tc_dir, "", i, exe_path, timeout, no_solve)
        written_cases += 1

    summary.update(
        samples=written_samples,
        cases=written_cases,
        dropped=dropped,
    )
    console.keyvalues(
        [
            ("build", "solution.cpp compiled" if exe_path else "skipped (--no-solve)"),
            ("cases", f"{written_samples} samples, {written_cases} test cases"),
            ("dropped", dropped or None),
            ("seed", seed),
        ]
    )

    if report:
        text = format_report(spec, build_report_rows(spec, sample_cases, cases))
        (prob_dir / "report.txt").write_text(text, newline="\n")
        console.line("")
        for line in text.rstrip("\n").splitlines():
            console.line(f"  {line}")

    if exe_path is not None and not keep:
        cleanup_exe(exe_path)

    if not no_solve:
        for f in tc_dir.glob("*.txt"):
            if f.stat().st_size == 0:
                raise RuntimeError(f"{f.name} is empty")

        zip_path = prob_dir / f"{pid}.zip"
        create_problem_zip(tc_dir, zip_path, pid)
        in_count, out_count = verify_zip(zip_path)
        summary.update(
            inputs=in_count,
            outputs=out_count,
            zip=display_path(zip_path),
        )
        console.keyvalues(
            [
                ("zip", f"{in_count} inputs, {out_count} outputs"),
                ("file", display_path(zip_path)),
                (
                    "checker",
                    load_checker(prob_dir) and "custom"
                    or "none (HackerRank compares exactly)",
                ),
            ]
        )

    return summary



def dry_run(contest_dir, problem_filter=None, show_applicability=False,
            report=False, seed=12345):
    contest_dir = Path(contest_dir)
    problems = discover_problems(contest_dir, problem_filter, require_solution=False)

    out = Printer(sys.stdout)
    out.banner(f"TESTCASE GENERATOR   {contest_dir.name}   (dry run)")
    out.keyvalues(
        [
            ("problems", len(problems)),
            ("seed", seed),
            ("writes", "none"),
        ]
    )

    rows = []
    success = True
    for index, prob_dir in enumerate(problems, 1):
        pid = prob_dir.name
        try:
            spec = load_spec(prob_dir / "spec.py")
            has_solution = (prob_dir / "solution.cpp").exists()
            usable = sum(
                1 for s in spec._strategies
                if spec.strategy_applicability(s) is None
            )
            rows.append(
                (
                    index,
                    pid,
                    spec.name.strip(),
                    spec.testcases,
                    len(spec._variables),
                    usable,
                    len(spec._custom_cases),
                    "yes" if has_solution else "NO",
                )
            )
            console_status = "ready" if has_solution else "no solution"
            out.banner(f"[{index}/{len(problems)}]  {pid}", spec.name.strip())
            out.keyvalues(
                [
                    ("testcases", spec.testcases),
                    ("variables", ", ".join(v.name for v in spec._variables)),
                    (
                        "strategies",
                        f"{usable} usable, "
                        f"{len(spec._strategies) - usable} skipped, "
                        f"{len(spec._custom_cases)} custom",
                    ),
                    ("solution", "found" if has_solution else "MISSING"),
                    ("status", console_status),
                ]
            )
            if show_applicability and spec._strategies:
                out.line("")
                out.line(
                    "  strategy                     applies  reason"
                )
                out.line(f"  {'-' * 29}  {'-' * 7}  {'-' * 30}")
                for s in spec._strategies:
                    name = spec._origin_name(s)
                    reason = spec.strategy_applicability(s)
                    mark = "yes" if reason is None else "no"
                    out.line(
                        f"  {name[:29].ljust(29)}  {mark.ljust(7)}  "
                        + ("" if reason is None else reason)
                    )
                    if reason is not None:
                        logger.warning("%s: not applicable: %s", name, reason)
            if report:
                sample_cases, cases = generate_in_memory(spec, seed)
                out.line("")
                out.line("  case report")
                for line in format_report(
                    spec, build_report_rows(spec, sample_cases, cases)
                ).rstrip("\n").splitlines():
                    out.line(f"  {line}")
        except Exception as e:
            rows.append((index, pid, "-", "-", "-", "-", "-", "error"))
            out.plain(f"error  {pid}  -  {e}")
            success = False

    out.banner("SUMMARY   (dry run, nothing written)")
    out.table(
        ("#", "problem", "name", "cases", "vars", "usable", "custom", "solution"),
        rows,
        aligns=["r", "l", "l", "r", "r", "r", "r", "l"],
    )
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

    console.banner(f"TESTCASE GENERATOR   {contest_dir.name}")
    console.keyvalues(
        [
            ("problems", len(problems)),
            ("seed", args.seed),
            ("timeout", f"{args.timeout}s"),
            ("solve", not args.no_solve),
        ]
    )

    summaries = []
    failures = []
    for index, prob_dir in enumerate(problems, 1):
        try:
            summaries.append(
                process_problem(
                    prob_dir, args.seed, args.timeout, args.no_solve, args.keep,
                    report=args.report,
                    position=f"{index}/{len(problems)}",
                )
            )
        except Exception as e:
            failures.append((prob_dir.name, e))
            summaries.append(
                {
                    "problem": prob_dir.name,
                    "name": "",
                    "samples": 0,
                    "cases": 0,
                    "dropped": 0,
                    "inputs": 0,
                    "outputs": 0,
                    "zip": "",
                    "status": "error",
                    "error": str(e),
                }
            )
            console.line("")
            console.plain(f"error  {prob_dir.name}  -  {e}")
            console.line(RULE)

    console.banner(
        "SUMMARY" if not failures else "SUMMARY   (finished with errors)"
    )
    console.table(
        ("#", "problem", "cases", "samples", "dropped", "inputs", "outputs", "status"),
        [
            (
                index,
                s["problem"],
                s["cases"],
                s["samples"],
                s["dropped"] or "-",
                s["inputs"] or "-",
                s["outputs"] or "-",
                s["status"],
            )
            for index, s in enumerate(summaries, 1)
        ],
        aligns=["r", "l", "r", "r", "r", "r", "r", "l"],
    )

    totals = {
        "cases": sum(s["cases"] for s in summaries),
        "samples": sum(s["samples"] for s in summaries),
        "dropped": sum(s["dropped"] for s in summaries),
        "inputs": sum(s["inputs"] for s in summaries),
        "outputs": sum(s["outputs"] for s in summaries),
    }
    console.line("")
    console.keyvalues(
        [
            ("cases", totals["cases"]),
            ("samples", totals["samples"]),
            ("dropped", totals["dropped"] or None),
            ("inputs", totals["inputs"]),
            ("outputs", totals["outputs"]),
            ("ok", f"{len(problems) - len(failures)}/{len(problems)}"),
        ]
    )
    for pid, err in failures:
        console.plain(f"error  {pid}  -  {err}")

    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()

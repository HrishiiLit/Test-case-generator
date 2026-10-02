# Testcase Generator

A folder-driven framework for generating competitive-programming testcases. No JSON config — just folders, solutions, and spec files.

Requires Python 3.10+ and a C++17 compiler (g++), **or** just Docker Desktop — see [Running with Docker](#running-with-docker).

## Quick Start

```
1. Create contest folder:    contests/MyContest/
2. Create problem folder:    contests/MyContest/Problem_1/
3. Add solution:             contests/MyContest/Problem_1/solution.cpp
4. Generate spec:            Give PROMPT.md + problem screenshot/description + solution.cpp to an LLM
5. Add spec:                 contests/MyContest/Problem_1/spec.py
6. Generate:                 python generate_tests.py contests/MyContest
7. Upload ZIP:               contests/MyContest/Problem_1/Problem_1.zip → HackerRank
```

## Running with Docker

Use this if you do not have Python or a C++ compiler installed. The image bundles
Python 3.12 and `g++`, so [Docker Desktop](https://www.docker.com/products/docker-desktop/)
is the only requirement. There is nothing to pip install — the project is pure stdlib.

**One-time setup**

```bash
docker build -t testcase-generator .
```

**Every run**

```bash
# Linux, macOS, WSL, Git Bash
docker run --rm -it -v "$PWD:/app" testcase-generator contests/MyContest

# PowerShell
docker run --rm -it -v "${PWD}:/app" testcase-generator contests/MyContest

# cmd.exe
docker run --rm -it -v "%cd%:/app" testcase-generator contests/MyContest
```

The `-v` mount is what makes this pleasant: your `spec.py` edits are picked up with no
rebuild, and the generated `testcases/` folder plus `Problem_1.zip` are written straight
back to your project folder, ready to upload.

Everything after the image name is passed to the CLI unchanged:

```bash
docker run --rm -it -v "$PWD:/app" testcase-generator contests/MyContest --report
docker run --rm -it -v "$PWD:/app" testcase-generator contests/MyContest --problem Problem_1
docker run --rm -it -v "$PWD:/app" testcase-generator contests/MyContest --dry-run
docker run --rm -it -v "$PWD:/app" testcase-generator contests/MyContest --timeout 10
```

Notes:
- The container compiles `solution.cpp` into a Linux binary, so a `solution` left behind
  (only with `--keep`) will not run on Windows and vice versa. Generated inputs and
  expected outputs are identical either way.
- Reproducibility assumes the same container. Reuse the image rather than mixing a host
  run and a container run if you care about exact output for a given seed.
- Files created inside the container are owned by `root` on Linux hosts. On Windows and
  macOS with Docker Desktop this is transparent.

## Project Structure

```
testcase-generator/
├── generate_tests.py      # Main CLI
├── PROMPT.md              # LLM prompt for generating spec.py + checker.py
├── FRAMEWORK_PROMPT.md    # Quick API reference (optional, for human reference)
├── Dockerfile             # Optional: Python 3.12 + g++ environment
├── framework/             # Core library
│   ├── __init__.py
│   ├── problem.py
│   ├── generators.py
│   ├── graphs.py
│   ├── strategies.py
│   ├── validators.py
│   ├── runner.py
│   ├── zipper.py
│   └── checker.py         # Checker utilities (load, validate)
├── contests/
│   └── Sample_contest/    # Example contest (committed; other contests are gitignored)
└── tests/                 # Test suite
```

## CLI

```bash
python generate_tests.py contests/MyContest                 # All problems
python generate_tests.py contests/MyContest --problem P1     # One problem
python generate_tests.py contests/MyContest --dry-run        # Preview, writes nothing
python generate_tests.py contests/MyContest --report         # Per-case table
python generate_tests.py contests/MyContest --seed 999       # Custom seed (default 12345)
python generate_tests.py contests/MyContest --timeout 10     # Solution timeout, seconds (default 30)
python generate_tests.py contests/MyContest --no-solve       # Inputs only
python generate_tests.py contests/MyContest --keep           # Keep solution binary after the run
python generate_tests.py contests/MyContest --verbose        # Debug logging
```

**Note:** Contest folder names containing spaces are not supported. Use folder names without spaces (e.g., `Sample_contest`) or rename the folder accordingly.

## spec.py

```python
from framework import *

spec = Problem(name="Two Sum", testcases=30)

N = Integer(name="N", min_value=2, max_value=100000)
Target = Integer(name="Target", min_value=1, max_value=10**9)
A = Array(name="A", size=N, min_value=-10**9, max_value=10**9)

spec.input(N, Target, A)

spec.add_testcases(
    minimum(),
    maximum(),
    random_case(),
    stress_case(),
    increasing(),
    decreasing(),
    boundary_values(),
)
```

## Data Types

| Type | Example |
|------|---------|
| `Integer` | `Integer(name="N", min_value=1, max_value=100000)` |
| `LongInteger` | `LongInteger(name="X", min_value=-10**18, max_value=10**18)` |
| `Float` | `Float(name="P", min_value=0.0, max_value=1.0, decimals=6)` |
| `String` | `String(name="S", length=10, alphabet="abc")` |
| `Array` | `Array(name="A", size=N, min_value=1, max_value=100)` |
| `Matrix` | `Matrix(name="M", rows=N, cols=N, min_value=0, max_value=100)` |
| `Permutation` | `Permutation(name="P", size=N)` |
| `Graph` | `Graph(name="G", num_vertices=N, num_edges=M)` |
| `Tree` | `Tree(name="T", num_vertices=N)` |

## Strategies

**Scalar:** `minimum()`, `maximum()`, `random_case()`, `stress_case()`, `all_equal()`, `all_zero()`, `increasing()`, `decreasing()`, `mixed_signs()`, `positive_only()`, `negative_only()`, `alternating()`, `boundary_values()`, `duplicates()`

**String:** `min_length()`, `max_length()`, `single_char()`, `all_same_char()`, `alternating_chars()`, `palindrome()`, `repeated_pattern()`

**Graph/Tree:** `chain()`, `star()`, `disconnected()`, `dense()`, `single_node()`, `balanced()`, `skewed()`

## Custom Testcases

```python
def my_special_case(rng):
    return {"N": 5, "A": [1, 2, 3, 4, 5]}

spec.add_custom_case(my_special_case)
```

## checker.py (Optional)

The LLM may also generate a `checker.py` for custom judging. This is optional — only use it if your problem needs partial scoring, whitespace-tolerant matching, or custom validation logic. Without a checker, HackerRank uses exact-match comparison.

If provided, place it alongside `spec.py` and `solution.cpp` in the problem folder.

**The checker is not part of the ZIP.** `Problem_1.zip` contains test data only —
`input/` and `output/`. The generator validates that your `checker.py` defines
`run_custom_checker` and reports that a checker exists, but it never copies the
file into the archive. Attach it separately through the contest's custom-checker
setting on HackerRank.

```python
def run_custom_checker(t_obj, r_obj):
    # Read input
    with open(t_obj.testcase_input_path) as f:
        data = f.read().split()

    # Read contestant output
    with open(t_obj.testcase_output_path) as f:
        output = f.read().strip()

    # Validate and score
    if output == expected_answer:
        r_obj.result = True
        r_obj.score = 1.0
        r_obj.message = "Success"
    else:
        r_obj.result = False
        r_obj.score = 0.0
        r_obj.message = f"Expected {expected_answer}, got {output}"
```

**Key fields:**
- `t_obj.testcase_input_path` — path to input file
- `t_obj.testcase_output_path` — path to contestant's output
- `t_obj.testcase_expected_output_path` — path to expected output
- `r_obj.result` — `True` (accepted) or `False` (rejected)
- `r_obj.score` — `0.0` to `1.0`
- `r_obj.message` — visible to the contestant

## How It Works

1. You create folders and add `solution.cpp`
2. You get `spec.py` (and optionally `checker.py`) from an LLM using `PROMPT.md` (provide problem screenshot or description + solution.cpp)
3. The framework generates testcases, validates them, runs your solution, and creates ZIPs

The `solution.cpp` is the oracle — it produces expected outputs. The optional `checker.py` validates contestant output and computes scores.

## Deterministic

Same spec + same seed = identical testcases.

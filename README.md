# Testcase Generator Framework
## Getting Started

```bash
git clone https://github.com/yourusername/testcase-generator.git
cd testcase-generator
```

Ensure you have Python 3.10+ and a C++17 compiler (g++) installed.

A lightweight, folder-driven framework for generating competitive-programming testcases, inspired by [TCFrame](https://tcframe.toki.id/docs).


**No JSON config required.** Just folders, solutions, and spec.py files.

## Quick Start

```
STEP 1: Create a contest folder
    Contest_1/

STEP 2: Create a problem folder
    Contest_1/Problem_1/

STEP 3: Add your accepted solution
    Contest_1/Problem_1/solution.cpp

STEP 4: Give the problem statement + solution to any LLM
    Use SPEC_PROMPT.md with ChatGPT, Claude, or Gemini

STEP 5: Receive spec.py and paste it into the problem folder
    Contest_1/Problem_1/spec.py

STEP 6: Run one command
    python generate_tests.py Contest_1

STEP 7: Find the ZIP
    Contest_1/Problem_1/Problem_1.zip

STEP 8: Upload to HackerRank
```

## How It Works

1. You create folders manually
2. You write or paste `solution.cpp` (the accepted solution)
3. You get `spec.py` from an LLM (describes input structure + testcases)
4. The framework generates testcases, validates them, runs your solution, and creates ZIPs

The official `solution.cpp` is the **oracle** — it produces expected outputs. The framework never computes answers itself.

## Project Structure

```
testcase-generator/
├── generate_tests.py          # Main CLI — run this
├── FRAMEWORK_PROMPT.md        # Full API reference for LLMs
├── SPEC_PROMPT.md             # Copy-paste prompt for generating spec.py
├── README.md
├── framework/
│   ├── __init__.py            # Exports all API classes
│   ├── problem.py             # Problem class
│   ├── generators.py          # Integer, Array, String, Matrix, Permutation
│   ├── graphs.py              # Graph, Tree
│   ├── strategies.py          # Edge-case generation strategies
│   ├── validators.py          # Input validation
│   ├── runner.py              # C++ compilation and execution
│   └── zipper.py              # ZIP creation and verification
└── Contest_1/
    ├── Problem_1/
    │   ├── solution.cpp
    │   └── spec.py
    └── Problem_2/
        ├── solution.cpp
        └── spec.py
```

## CLI Commands

### Generate all problems in a contest

```bash
python generate_tests.py Contest_1
```

### Generate one problem only

```bash
python generate_tests.py Contest_1 --problem Problem_1
```

### Dry run (preview, no files created)

```bash
python generate_tests.py Contest_1 --dry-run
```

### Set random seed

```bash
python generate_tests.py Contest_1 --seed 999
```

### Verbose logging

```bash
python generate_tests.py Contest_1 --verbose
```

### Skip solution execution (inputs only)

```bash
python generate_tests.py Contest_1 --no-solve
```

## Output Structure

```
Contest_1/
└── Problem_1/
    ├── solution.cpp
    ├── spec.py
    ├── testcases/
    │   ├── input1.txt
    │   ├── output1.txt
    │   ├── input2.txt
    │   ├── output2.txt
    │   └── ...
    └── Problem_1.zip          ← Upload this to HackerRank
```

Each problem gets its **own ZIP** containing only testcase files.

### ZIP Format (HackerRank upload format)

Inside each `Problem_ID.zip`:

```
input/
├── input00.txt
├── input01.txt
└── ...
output/
├── output00.txt
├── output01.txt
└── ...
```

Files are zero-padded (`input00.txt`, `input01.txt`, ...) and split into `input/`
and `output/` folders — exactly what HackerRank's testcase uploader expects.
The local `testcases/` folder keeps plain names (`input1.txt`) for readability;
the renaming happens only inside the archive.

## spec.py Format

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
    random_case(),
    stress_case(),
    increasing(),
    decreasing(),
    boundary_values(),
)
```

## Available Data Types

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

## Available Strategies

**Scalar:** `minimum()`, `maximum()`, `random_case()`, `stress_case()`, `all_equal()`, `all_zero()`, `increasing()`, `decreasing()`, `mixed_signs()`, `positive_only()`, `negative_only()`, `alternating()`, `boundary_values()`, `duplicates()`

**String:** `min_length()`, `max_length()`, `single_char()`, `all_same_char()`, `alternating_chars()`, `palindrome()`, `repeated_pattern()`

**Graph/Tree:** `chain()`, `star()`, `disconnected()`, `dense()`, `single_node()`, `balanced()`, `skewed()`

## Custom Testcases

```python
def my_special_case(rng):
    return {"N": 5, "A": [1, 2, 3, 4, 5]}

spec.add_custom_case(my_special_case)
```

## Deterministic Generation

Same spec + same seed = identical testcases.

```bash
python generate_tests.py Contest_1 --seed 12345  # Run 1
python generate_tests.py Contest_1 --seed 12345  # Run 2 — identical
```

## How to Add a New Problem

1. Create `Contest_1/NewProblem/`
2. Add `solution.cpp` (your accepted solution)
3. Use `SPEC_PROMPT.md` with any LLM to generate `spec.py`
4. Paste `spec.py` into the folder
5. Run `python generate_tests.py Contest_1`

## How to Add a New Contest

1. Create a new folder: `Contest_2/`
2. Add problem subfolders with `solution.cpp` and `spec.py`
3. Run `python generate_tests.py Contest_2`

Each contest is independent. Running one never affects another.

## Uploading to HackerRank

1. Run `python generate_tests.py Contest_1 --problem Problem_1`
2. Find `Contest_1/Problem_1/Problem_1.zip`
3. In HackerRank, go to the problem's "Test Cases" tab
4. Click "Upload Test Cases" and select the ZIP
5. HackerRank reads `input/inputNN.txt` and `output/outputNN.txt` pairs automatically

## Requirements

- Python 3.10+
- g++ with C++17 support
- No pip packages needed (standard library only)
# Test-case

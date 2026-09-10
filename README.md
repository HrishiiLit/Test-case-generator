# Testcase Generator

A folder-driven framework for generating competitive-programming testcases. No JSON config — just folders, solutions, and spec files.

Requires Python 3.10+ and g++ (C++17).

## Quick Start

```
1. Create contest folder:    contests/MyContest/
2. Create problem folder:    contests/MyContest/Problem_1/
3. Add solution:             contests/MyContest/Problem_1/solution.cpp
4. Generate spec:            Give PROMPT.md + problem statement + solution.cpp to an LLM
5. Add spec:                 contests/MyContest/Problem_1/spec.py
6. Generate:                 python generate_tests.py contests/MyContest
7. Upload ZIP:               contests/MyContest/Problem_1/Problem_1.zip → HackerRank
```

## Project Structure

```
testcase-generator/
├── generate_tests.py      # Main CLI
├── PROMPT.md              # LLM prompt for generating spec.py
├── FRAMEWORK_PROMPT.md    # Quick API reference
├── framework/             # Core library
│   ├── __init__.py
│   ├── problem.py
│   ├── generators.py
│   ├── graphs.py
│   ├── strategies.py
│   ├── validators.py
│   ├── runner.py
│   └── zipper.py
├── Sample_contest/        # Example contest (committed)
└── contests/              # Your contests (gitignored)
```

## CLI

```bash
python generate_tests.py contests/MyContest              # All problems
python generate_tests.py contests/MyContest --problem P1  # One problem
python generate_tests.py contests/MyContest --dry-run     # Preview
python generate_tests.py contests/MyContest --seed 999    # Custom seed
python generate_tests.py contests/MyContest --verbose     # Debug
python generate_tests.py contests/MyContest --no-solve    # Inputs only
```

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

## How It Works

1. You create folders and add `solution.cpp`
2. You get `spec.py` from an LLM using `PROMPT.md`
3. The framework generates testcases, validates them, runs your solution, and creates ZIPs

The `solution.cpp` is the oracle — it produces expected outputs. The framework never computes answers itself.

## Deterministic

Same spec + same seed = identical testcases.

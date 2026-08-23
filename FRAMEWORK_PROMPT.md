# Framework Reference

This document describes the complete testcase-generation framework API.

## Quick Start

```
1. Create contest folder:    Contest_1/
2. Create problem folder:    Contest_1/Problem_1/
3. Add solution:             Contest_1/Problem_1/solution.cpp
4. Get spec from LLM:       Use SPEC_PROMPT.md with ChatGPT/Claude/Gemini
5. Add spec:                 Contest_1/Problem_1/spec.py
6. Generate:                 python generate_tests.py Contest_1
7. Find ZIP:                 Contest_1/Problem_1/Problem_1.zip
8. Upload to HackerRank
```

## Project Structure

```
testcase-generator/
├── generate_tests.py          # Main CLI
├── FRAMEWORK_PROMPT.md        # This file
├── SPEC_PROMPT.md             # Copy-paste prompt for LLMs
├── README.md
├── framework/
│   ├── __init__.py            # Exports all API classes
│   ├── problem.py             # Problem class
│   ├── generators.py          # Integer, Array, String, etc.
│   ├── graphs.py              # Graph, Tree
│   ├── strategies.py          # Edge-case strategies
│   ├── validators.py          # Input validation
│   ├── runner.py              # C++ compilation/execution
│   └── zipper.py              # ZIP creation
└── Contest_1/
    └── Problem_1/
        ├── solution.cpp
        └── spec.py
```

## API Classes

### Problem

```python
spec = Problem(name="Two Sum", testcases=30)
spec.input(N, Target, A)
spec.add_testcases(minimum(), maximum(), random_case())
spec.add_custom_case(my_func)
```

### Integer / LongInteger

```python
N = Integer(name="N", min_value=1, max_value=100000)
```

### Line

Groups variables that appear on the SAME line in the input format.
Inner variables are still generated/validated normally.

```python
spec.input(T, Line(N, K, X), A)
# Renders:
# T
# N K X
# A...
```

### Blocks

Marks variables that repeat once per test-case block in multi-test inputs
(problems whose solution reads `t`, then loops over test cases). Declare T
with its full stated range; everything read per test case goes inside Blocks.

```python
spec.input(T, Blocks(Line(N, K, X), A))
# Renders (repeated T times for the block part):
# T
# N K X
# A...
```

Standard strategies replicate their single generated block and lower T so the
total stays within the framework size budget. For varied multi-test cases,
custom cases return blocks explicitly:

```python
def multi_random(rng):
    t = rng.randint(1, 10000)
    blocks, sum_n = [], 0
    for _ in range(t):
        budget = 200000 - sum_n
        if budget < 1:
            break
        n = rng.randint(1, min(1000, budget))
        a = [rng.randint(1, 100) for _ in range(n)]
        blocks.append({"N": n, "A": a})
        sum_n += n
    return {"T": len(blocks), "__blocks__": blocks}

spec.add_custom_case(multi_random)
```

The validator checks `T == len(__blocks__)` and validates every block against
the declared variables.

### Float

```python
X = Float(name="X", min_value=0.0, max_value=1.0, decimals=6)
```

### String

```python
S = String(name="S", length=10, alphabet="abcdefghijklmnopqrstuvwxyz")
S = String(name="S", min_length=1, max_length=100, alphabet="ab")
```

### Array

```python
A = Array(name="A", size=N, min_value=-10**9, max_value=10**9)
A = Array(name="A", min_size=1, max_size=100, min_value=1, max_value=100, unique=True)
```

### Matrix

```python
M = Matrix(name="M", rows=N, cols=N, min_value=0, max_value=100)
```

### Permutation

```python
P = Permutation(name="P", size=N, min_value=1, max_value=N)
```

### Graph

```python
G = Graph(name="G", num_vertices=N, num_edges=M, directed=False, weighted=False)
```

Output format: `N M\nu1 v1\nu2 v2\n...`

### Tree

```python
T = Tree(name="T", num_vertices=N)
```

Output format: `N\nu1 v1\nu2 v2\n...`

## Strategies

### Scalar Strategies

| Strategy | Description |
|----------|-------------|
| `minimum()` | All variables at minimum bound |
| `maximum()` | All variables at maximum bound |
| `random_case()` | Random valid values |
| `stress_case()` | Large values near bounds |
| `all_equal()` | All values same |
| `all_zero()` | Zeros where valid |
| `increasing()` | Sorted ascending |
| `decreasing()` | Sorted descending |
| `mixed_signs()` | Positive and negative |
| `positive_only()` | All positive |
| `negative_only()` | All negative |
| `alternating()` | Alternating values |
| `boundary_values()` | Min/max/zero mix |
| `duplicates()` | Repeated values |

### String Strategies

| Strategy | Description |
|----------|-------------|
| `min_length()` | Shortest possible |
| `max_length()` | Longest possible |
| `single_char()` | One character |
| `all_same_char()` | Repeated character |
| `alternating_chars()` | ababab... |
| `palindrome()` | Reads same both ways |
| `repeated_pattern()` | abcabc... |

### Graph/Tree Strategies

| Strategy | Description |
|----------|-------------|
| `chain()` | Linear chain |
| `star()` | Star topology |
| `disconnected()` | Disconnected components |
| `dense()` | Many edges (graph only) |
| `single_node()` | One vertex |
| `balanced()` | Balanced tree |
| `skewed()` | Skewed tree |

## Custom Cases

```python
def special_case(rng):
    return {"N": 5, "A": [1, 2, 3, 4, 5]}

spec.add_custom_case(special_case)
```

## CLI Commands

```bash
# Generate all problems in a contest
python generate_tests.py Contest_1

# Generate one problem only
python generate_tests.py Contest_1 --problem Problem_1

# Dry run (no files created)
python generate_tests.py Contest_1 --dry-run

# Set seed
python generate_tests.py Contest_1 --seed 999

# Verbose logging
python generate_tests.py Contest_1 --verbose

# Skip solution execution
python generate_tests.py Contest_1 --no-solve

# Keep executables
python generate_tests.py Contest_1 --keep
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
    └── Problem_1.zip
```

## Determinism

Same spec + same seed = identical testcases.

```bash
python generate_tests.py Contest_1 --seed 12345  # First run
python generate_tests.py Contest_1 --seed 12345  # Identical output
```

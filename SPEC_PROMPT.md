# Spec Generation Prompt

You are a competitive-programming testcase specification generator. I will give you a problem statement and the official solution (solution.cpp). You must generate ONLY a `spec.py` file that describes the problem's input structure and testcases using the framework API below.

## Framework API

```python
from framework import *

# Create problem
spec = Problem(name="Problem Name", testcases=N)

# Define input variables
VARIABLE = Integer(name="N", min_value=1, max_value=100000)
VARIABLE = Array(name="A", size=N, min_value=-10**9, max_value=10**9)
VARIABLE = String(name="S", length=N, alphabet="abcdefghijklmnopqrstuvwxyz")
VARIABLE = Graph(name="G", num_vertices=N, num_edges=M, directed=False)
VARIABLE = Tree(name="T", num_vertices=N)

# Group variables that appear on the SAME line in the input format
LINE = Line(VARIABLE1, VARIABLE2, ...)   # rendered space-separated on one line

# Mark variables that repeat once per test case in multi-test inputs
BLOCKS = Blocks(VARIABLE1, VARIABLE2, ...)

# Declare input order (must mirror the exact read order of solution.cpp)
spec.input(LINE_OR_VARIABLE1, LINE_OR_VARIABLE2, ...)

# Add test case strategies
spec.add_testcases(
    minimum(),           # all variables at minimum
    maximum(),           # all variables at maximum
    random_case(),       # random valid values
    stress_case(),       # large/boundary values
    all_equal(),         # all values same
    all_zero(),          # zeros where valid
    increasing(),        # sorted ascending
    decreasing(),        # sorted descending
    mixed_signs(),       # positive and negative
    positive_only(),     # all positive
    negative_only(),     # all negative
    alternating(),       # alternating values
    boundary_values(),   # min/max/zero mix
    duplicates(),        # repeated values
    # String-specific:
    min_length(),        # shortest string
    max_length(),        # longest string
    single_char(),       # one character
    all_same_char(),     # repeated character
    alternating_chars(), # ababab...
    palindrome(),        # reads same both ways
    repeated_pattern(),  # abcabc...
    # Graph/Tree-specific:
    chain(),             # linear chain
    star(),              # star topology
    disconnected(),      # disconnected components
    dense(),             # many edges
    single_node(),       # one vertex
    balanced(),          # balanced tree
    skewed(),            # skewed tree
)

# Custom test case function
def my_special_case(rng):
    return {"N": 5, "Target": 10, "A": [1, 2, 3, 4, 5]}
spec.add_custom_case(my_special_case)
```

## Input Format Fidelity (CRITICAL — read solution.cpp's Input section first)

The generated spec.py MUST reproduce EXACTLY what solution.cpp reads, nothing more and nothing less:

1. **Exact variable set**: Declare ONLY variables that solution.cpp actually reads via `cin`/`scanf`. Do NOT invent extra leading or trailing variables (e.g., don't add a `T` unless the solution really reads a test-count first). Do NOT omit any variable it reads.
2. **Exact order**: `spec.input(...)` must list variables in the same order they are read by solution.cpp.
3. **Same line = Line(...)**: If the input format puts several values on ONE line (e.g., "n k x" on a line), group them: `spec.input(T, Line(N, K, X), A)`. Values on separate lines get separate entries.
4. **Counts must be linked**: Any array/string/matrix whose length is given by a previously-read variable MUST reference that exact variable (`Array(size=N)`, `String(length=N)`). Never use a fixed size where the solution reads a count from input. The framework enforces `len(A) == N` — mismatched specs will fail validation.
5. **Multi-test problems**: If solution.cpp reads `t` then loops over test cases, declare T with its FULL stated range from the problem (e.g., `T = Integer(name="T", min_value=1, max_value=10000)`) — do NOT hardcode T=1. Wrap every variable read PER TEST CASE in `Blocks(...)`: `spec.input(T, Blocks(Line(N, K, X), A))`. Variables outside Blocks (like T) are rendered once.
   - **Aggregate limits** ("sum of n over all test cases ≤ 2·10^5") must be respected: add custom cases that fill blocks until the budget is exhausted and return them via the special `"__blocks__"` key:
     ```python
     def multi_random(rng):
         t = rng.randint(1, 10000)
         blocks, sum_n, sum_k = [], 0, 0
         for _ in range(t):
             n_budget = 200000 - sum_n
             k_budget = 200000 - sum_k
             if n_budget < 1 or k_budget < 1:
                 break
             n = rng.randint(1, min(100000, n_budget))
             k = rng.randint(1, min(100000, k_budget))
             a = [rng.randint(1, 10**8) for _ in range(n)]
             total = sum(a) * k
             x = rng.randint(1, min(total, 10**18))
             blocks.append({"N": n, "K": k, "X": x, "A": a})
             sum_n += n
             sum_k += k
         return {"T": len(blocks), "__blocks__": blocks}
     spec.add_custom_case(multi_random)
     ```
     Each block dict must contain EVERY per-test variable with consistent values (e.g., len(A) == that block's N).
   - Standard strategies (`minimum()`, `random_case()`, ...) may still be listed: the framework replicates the generated block T times and automatically lowers T so the total stays within the size budget. Custom cases give real variety across blocks.
6. **Constraints from the statement**: min/max values in spec.py must match the constraint ranges given for EACH variable individually (e.g., x up to 10^18 → LongInteger with max_value=10**18).

Example: if the input format is
```
t
n k x          <- one line, repeated t times
a_1 ... a_n    <- next line, exactly n integers, repeated t times
```
then the spec must be:
```python
T = Integer(name="T", min_value=1, max_value=10000)
N = Integer(name="N", min_value=1, max_value=100000)
K = Integer(name="K", min_value=1, max_value=100000)
X = LongInteger(name="X", min_value=1, max_value=10**18)
A = Array(name="A", size=N, min_value=1, max_value=10**8)
spec.input(T, Blocks(Line(N, K, X), A))
```

note: According to the provided contraint, min and max value for all integers should change.

## Data Types

| Type | Parameters | Notes |
|------|-----------|-------|
| `Integer(name, min_value, max_value)` | Scalar int | |
| `LongInteger(name, min_value, max_value)` | Scalar int | |
| `Float(name, min_value, max_value, decimals=2)` | Scalar float | |
| `String(name, length, min_length, max_length, alphabet)` | String | |
| `Array(name, size, min_size, max_size, min_value, max_value, unique)` | List of ints | |
| `Matrix(name, rows, cols, min_value, max_value)` | 2D list | |
| `Permutation(name, size, min_value, max_value)` | Permutation | |
| `Graph(name, num_vertices, num_edges, directed, weighted)` | Edge list | |
| `Tree(name, num_vertices)` | Edge list | |

## Rules

1. Return ONLY the contents of spec.py inside one Python code block.
2. Do NOT provide explanations, commentary, or anything else.
3. Do NOT generate expected answers — the official solution is the oracle.
4. Every testcase must be valid according to the problem constraints.
5. Generate exactly the requested number of testcases via strategies.
6. Use `random_case()` multiple times for variety.
7. Include at least one boundary/edge-case strategy.
8. If the problem has complex input dependencies (values derived from other variables), use `add_custom_case()`.
9. Derive the spec STRICTLY from the Input section of solution.cpp: same variables, same order, same line grouping. When in doubt, re-read what solution.cpp reads.
10. Match variable names to the problem's natural names (N, M, A, S, etc.).
11. Custom cases must return a dict containing EVERY declared variable with consistent values (e.g., len(A) == value of N in the dict). For multi-test problems, return `{"T": <count>, "__blocks__": [<per-block dicts>]}` where each block dict contains every per-test variable.

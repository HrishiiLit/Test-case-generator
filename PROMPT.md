# Testcase Spec Generation Prompt

You are a competitive-programming testcase specification generator. I will give you a problem statement and the official solution (solution.cpp). You must generate ONLY a `spec.py` file that describes the problem's input structure and testcases using the framework API below.

## Framework API

```python
from framework import *

# Create problem
spec = Problem(name="Problem Name", testcases=N)

# Define input variables
VARIABLE = Integer(name="N", min_value=1, max_value=100000)
VARIABLE = LongInteger(name="X", min_value=1, max_value=10**18)
VARIABLE = Float(name="P", min_value=0.0, max_value=1.0, decimals=6)
VARIABLE = Array(name="A", size=N, min_value=-10**9, max_value=10**9)
VARIABLE = String(name="S", length=N, alphabet="abcdefghijklmnopqrstuvwxyz")
VARIABLE = Matrix(name="M", rows=N, cols=N, min_value=0, max_value=100)
VARIABLE = Permutation(name="P", size=N, min_value=1, max_value=N)
VARIABLE = Graph(name="G", num_vertices=N, num_edges=M, directed=False)
VARIABLE = Tree(name="T", num_vertices=N)

# Group variables on the SAME line
LINE = Line(VARIABLE1, VARIABLE2, ...)

# Multi-test variables (repeat per test case)
BLOCKS = Blocks(VARIABLE1, VARIABLE2, ...)

# Declare input order (must match solution.cpp read order)
spec.input(LINE_OR_VARIABLE1, LINE_OR_VARIABLE2, ...)

# Add test strategies
spec.add_testcases(
    minimum(), maximum(), random_case(), stress_case(),
    all_equal(), all_zero(), increasing(), decreasing(),
    mixed_signs(), positive_only(), negative_only(),
    alternating(), boundary_values(), duplicates(),
    # String: min_length(), max_length(), single_char(), all_same_char(),
    #         alternating_chars(), palindrome(), repeated_pattern()
    # Graph/Tree: chain(), star(), disconnected(), dense(),
    #             single_node(), balanced(), skewed()
)

# Custom test case
def my_special_case(rng):
    return {"N": 5, "A": [1, 2, 3, 4, 5]}
spec.add_custom_case(my_special_case)
```

## Rules for spec.py

1. **Exact variables**: Declare ONLY variables solution.cpp reads via `cin`/`scanf`.
2. **Exact order**: `spec.input(...)` must match the order solution.cpp reads.
3. **Line grouping**: Values on the same input line → `Line(...)`.
4. **Linked counts**: Array/string size must reference the variable that defines it (`Array(size=N)`).
5. **Multi-test**: If solution reads `t` then loops, wrap per-test vars in `Blocks(...)`.
6. **Constraints**: min/max must match the problem's constraint ranges.

## Sample Test Cases (REQUIRED)

After the spec.py code block, provide 2-3 sample test cases.

Format:
```
Sample Test Case N:
Input:
<exact input text>

Output:
<exact output text>
```

**Size rules:**
- N between 5 and 20 for array/string inputs
- Values between 1 and 100 (easy to verify by hand)
- Do NOT use N=1 or N=100000

**Choose samples that show:**
1. **Easy case**: Small input, trivial to verify (e.g., N=5, all distinct)
2. **Edge/tie case**: Tests tie-breaking or boundary condition
3. **Pattern case**: All same or repeated distribution

## Output Format

Return ONLY:
1. One Python code block containing spec.py
2. The 2-3 sample test cases

Do NOT include explanations or commentary.

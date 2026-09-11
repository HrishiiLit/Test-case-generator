# Testcase Spec Generation Prompt

You are a competitive-programming testcase specification generator. I will give you a problem statement (as screenshot or text) and the official solution (solution.cpp). You must generate ONLY a `spec.py` file that describes the problem's input structure and testcases using the framework API below.

## Input Methods

You can receive problem information in either format:

### Option A: Screenshot/Image
If I provide a screenshot of the problem statement, extract:
- **Problem name** and description
- **Input format** (what variables, what order, same line or separate)
- **Constraints** (e.g., `1 ≤ n ≤ 2×10⁵`, `1 ≤ k ≤ 10⁹`)
- **Output format** (what to print, format specifics)
- **Sample test cases** (for verification)

### Option B: Text
If I paste the problem text, use it directly.

### Always Provided
- **solution.cpp**: The official solution code. Analyze this to determine:
  - Exact variable names and read order (`cin >>` calls)
  - Algorithm used (for TLE case design)
  - Time/memory limits (from comments)

## Framework Reference

### Quick Start

```
1. Create contest folder:    contests/MyContest/
2. Create problem folder:    contests/MyContest/Problem_1/
3. Add solution:             contests/MyContest/Problem_1/solution.cpp
4. Get spec from LLM:       Provide this prompt + problem statement + solution.cpp
5. Verify samples:           Check the 2-3 sample test cases (N=5-20, values 1-100)
6. Add spec:                 contests/MyContest/Problem_1/spec.py
7. Generate:                 python generate_tests.py contests/MyContest
8. Find ZIP:                 contests/MyContest/Problem_1/Problem_1.zip
9. Upload to HackerRank
```

### CLI

```bash
python generate_tests.py contests/MyContest              # All problems
python generate_tests.py contests/MyContest --problem P1  # One problem
python generate_tests.py contests/MyContest --dry-run     # Preview
python generate_tests.py contests/MyContest --seed 999    # Custom seed
python generate_tests.py contests/MyContest --verbose     # Debug
python generate_tests.py contests/MyContest --no-solve    # Inputs only
```

### Output Structure

```
contests/MyContest/
└── Problem_1/
    ├── solution.cpp
    ├── spec.py
    ├── testcases/
    │   ├── input1.txt
    │   ├── output1.txt
    │   └── ...
    └── Problem_1.zip
```

## Step 1: Analyze the Solution Code

Before writing spec.py, carefully analyze solution.cpp:

1. **Read the problem statement** in the comments (top of file) to get:
   - Variable names and their meanings
   - Constraint ranges (e.g., `1 ≤ n ≤ 100`, `1 ≤ k_i ≤ 10^9`)
   - Input format description

2. **Extract time and memory limits** from comments:
   - Look for lines like `// Time limit : 1.00 s` or `// time limit per test:1 second`
   - Look for lines like `// Memory limit : 512 MB` or `// memory limit per test:256 megabytes`
   - These inform TLE severity: stricter limits (≤1s) need more aggressive collision patterns

3. **Trace the `cin >>` calls** to determine:
   - Exact variable names (must match what solution reads)
   - Read order (must match `spec.input(...)` order)
   - Whether variables are on the same line or separate lines

4. **Identify algorithm complexity and data structures**:
   - `unordered_map/set` → hash collision attack
   - Nested loops O(n²) → max constraint values
   - Brute force → worst-case structure
   - O(n log n) or O(n) → no TLE case needed
   - Determine if TLE case is needed BEFORE writing spec.py

## Step 2: Write spec.py

### Framework API

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

### Rules for spec.py

1. **Exact variables**: Declare ONLY variables solution.cpp reads via `cin`/`scanf`. Do NOT add extra variables.

2. **Exact order**: `spec.input(...)` must match the order solution.cpp reads. Example:
   ```cpp
   cin >> n;        // First
   cin >> m;        // Second
   cin >> k;        // Third
   ```
   Must be: `spec.input(n, m, k)`

3. **Line grouping**: If solution reads multiple values on one line with `cin >> a >> b`, use `Line(a, b)`. If each value is on its own line, use separate variables.

4. **Linked counts**: Array/string size must reference the variable that defines it:
   ```python
   n = Integer(name="n", min_value=1, max_value=100000)
   a = Array(name="a", size=n, min_value=1, max_value=10**9)
   ```

5. **Multi-test format**: If solution reads `t` (test count) then loops, wrap per-test variables in `Blocks(...)`:
   ```python
   t = Integer(name="t", min_value=1, max_value=100)
   n = Integer(name="n", min_value=1, max_value=100000)
   a = Array(name="a", size=n, min_value=1, max_value=10**9)
   spec.input(t, Blocks(n, a))
   ```
   
   **IMPORTANT**: Custom cases for multi-test problems MUST use `"__blocks__"` (double underscores) as the key:
   ```python
   def my_custom_case(rng):
       return {
           "t": 3,
           "__blocks__": [  # NOT "blocks" - must be "__blocks__"
               {"n": 4, "a": [1, 2, 3, 4]},
               {"n": 3, "a": [5, 6, 7]},
               {"n": 2, "a": [8, 9]},
           ],
       }
   ```

6. **Constraints**: min/max MUST match the problem's constraint ranges exactly. Extract from problem statement comments in solution.cpp:
   ```
   // 1 ≤ n ≤ 100        → min_value=1, max_value=100
   // 1 ≤ k_i ≤ 10^9     → min_value=1, max_value=10**9
   // -10^6 ≤ x ≤ 10^6   → min_value=-10**6, max_value=10**6
   ```

7. **Variable names**: Use the SAME variable names as in the problem statement (e.g., `n`, `k`, `a`). This ensures clarity.

8. **Test case quality**: Every test case must serve a purpose. AVOID:
   - **Duplicates**: No two test cases should have identical input parameters
   - **Redundant patterns**: Don't use `all_equal()` + `duplicates()` together (both test same scenario)
   - **Useless random**: Multiple `random_case()` produce similar random inputs with no specific purpose
   - **Generic patterns**: `increasing()` and `decreasing()` rarely test meaningful edge cases

   INSTEAD, use problem-specific custom cases:
   - Boundary: min/max constraints
   - Edge cases: exact budget, empty result, full result
   - Pattern traps: greedy fails, all same values, all different values
   - Stress: max constraint with meaningful variation

9. **testcases count**: Set to 10 test cases total. Use custom cases for specific scenarios, not generic strategies.

### TLE Considerations

**Step 1: Detect vulnerability from solution code**

Read the solution.cpp and identify which data structures / algorithms are used. Then generate the matching TLE custom case.

#### 1.1 Hash containers (`unordered_map` / `unordered_set`)

**Trigger:** Solution uses `unordered_map`, `unordered_set`, `unordered_multimap`, or `unordered_multiset`.

**Why it TLEs:** These use hash tables. With a bad hash function or adversarial input, all keys collide into one bucket, turning O(1) into O(n) per operation.

**How to build the attack:**
- After `reserve(2*n)` with `max_load_factor(0.7)`, bucket_count = next power of 2 ≥ `ceil(2n / 0.7)`.
- For n=200000: bucket_count = 2^20 = 1048576.
- `std::hash<int>` is identity. Bucket index = `key & (bucket_count - 1)`.
- All multiples of 1048576 land in bucket 0. Within [1, 10^9], we get 953 unique values.
- Cycle through these 953 values to fill n elements → chain length 953 → O(n × 953) ≈ 2×10^8 → TLE at 1s.

```python
def case_tle_hash(rng):
    """All values hash to same bucket in unordered_map."""
    N_val = 200000
    BUCKET_SIZE = 1048576  # 2^20
    pool = [BUCKET_SIZE * (i + 1) for i in range(953)]
    k = [pool[i % 953] for i in range(N_val)]
    return {"n": N_val, "k": k}
```

#### 1.2 Ordered containers (`map` / `set`)

**Trigger:** Solution uses `map`, `set`, `multimap`, or `multiset` (red-black tree based).

**Why it TLEs:** These are O(log n) per operation, but with extreme key distributions the tree becomes degenerate or cache-unfriendly.

**How to build the attack:**
- Use max constraint values to maximize tree height.
- Alternating min/max values cause excessive rebalancing.

```python
def case_tle_ordered(rng):
    """Maximize tree operations with alternating extremes."""
    N_val = 200000
    a = []
    lo, hi = 1, 10**9
    for i in range(N_val):
        a.append(lo if i % 2 == 0 else hi)
    return {"n": N_val, "a": a}
```

#### 1.3 Nested loops O(n²)

**Trigger:** Solution has `for(i) { for(j) }` or `for(i) { while(j) }` where both iterate up to n.

**Why it TLEs:** n² = (2×10^5)² = 4×10^10, far beyond 1s limit.

**How to build the attack:**
- Set n to maximum constraint.
- Use values that force the inner loop to run fully (e.g., sorted descending when looking for ascending pairs).

```python
def case_tle_nested(rng):
    """Force full inner loop iterations."""
    N_val = 200000
    # Reverse sorted: every pair triggers inner scan
    a = list(range(N_val, 0, -1))
    return {"n": N_val, "a": a}
```

#### 1.4 Brute force subsets / permutations

**Trigger:** Solution uses bitmask enumeration `for(mask)`, `next_permutation`, or recursive backtracking over all subsets.

**Why it TLEs:** 2^n or n! grows exponentially. Even n=20 gives 2^20 ≈ 10^6, n=25 gives 3×10^7.

**How to build the attack:**
- Use the maximum n where 2^n or n! exceeds the operation budget.
- For 1s limit (~2×10^8 ops): n=27 for subsets (2^27 = 1.3×10^8), n=12 for permutations (12! = 4.8×10^8).

```python
def case_tle_bruteforce(rng):
    """Maximize subset/permutation enumeration."""
    N_val = 27  # 2^27 ≈ 1.3×10^8
    a = [rng.randint(1, 10**9) for _ in range(N_val)]
    return {"n": N_val, "a": a}
```

#### 1.5 Sorting O(n²) (bubble / selection sort)

**Trigger:** Solution implements bubble sort, selection sort, or insertion sort manually.

**Why it TLEs:** These are O(n²) even on random input. n=200000 → 4×10^10 comparisons.

**How to build the attack:**
- Nearly sorted input is worst for bubble sort (many swaps needed).
- Reverse sorted is worst for selection/insertion sort.

```python
def case_tle_sort(rng):
    """Worst case for O(n²) sorting algorithms."""
    N_val = 200000
    # Reverse sorted: maximum comparisons and swaps
    a = list(range(N_val, 0, -1))
    return {"n": N_val, "a": a}
```

#### 1.6 Graph O(V²) or O(V×E)

**Trigger:** Solution uses adjacency matrix (`g[i][j]`) or visits all edges repeatedly.

**Why it TLEs:** V=200000 with adjacency matrix → 4×10^10 memory accesses.

**How to build the attack:**
- Dense graph with max vertices and edges.
- Chain graph for DFS stack overflow (though not strictly TLE).

```python
def case_tle_graph(rng):
    """Dense graph maximizing edge iterations."""
    N_val = 2000
    # Complete graph: N*(N-1)/2 edges = ~2×10^6
    edges = []
    for i in range(1, N_val + 1):
        for j in range(i + 1, N_val + 1):
            edges.append((i, j))
    M_val = len(edges)
    return {"n": N_val, "m": M_val, "edges": edges}
```

#### 1.7 String matching O(n×m)

**Trigger:** Solution uses nested loops over two strings (naive pattern matching).

**Why it TLEs:** n=m=200000 → 4×10^10 character comparisons.

**How to build the attack:**
- Worst case: pattern with repeated prefix causes maximum backtracking.
- Example: text="aaaa...a", pattern="aaa...ab" (b only at end).

```python
def case_tle_string(rng):
    """Worst case for naive string matching."""
    N_val = 200000
    # All same character: forces full scan at each position
    s = "a" * N_val
    # Pattern: all 'a' except last char 'b' — no match until very end
    p = "a" * (N_val - 1) + "b"
    return {"n": N_val, "s": s, "m": len(p), "p": p}
```

#### 1.8 DP with large state

**Trigger:** Solution uses 2D DP table `dp[n][n]` or `dp[n][W]` where both dimensions scale with input.

**Why it TLEs:** dp[200000][200000] = 4×10^10 entries.

**How to build the attack:**
- Maximize both dimensions of the DP table.
- Use values that force full table computation.

```python
def case_tle_dp(rng):
    """Maximize DP table size."""
    N_val = 5000
    W_val = 10**7
    w = [rng.randint(1, W_val) for _ in range(N_val)]
    v = [rng.randint(1, 10**9) for _ in range(N_val)]
    return {"n": N_val, "W": W_val, "w": w, "v": v}
```

#### 1.9 Priority queue / heap with many operations

**Trigger:** Solution pushes/pops from `priority_queue` or `heap` O(n) times with O(log n) each, but constant factors are high.

**Why it TLEs:** With n=200000 and repeated push/pop, cache misses degrade performance.

**How to build the attack:**
- Alternate between push and pop to maximize heap operations.
- Use adversarial ordering that causes maximum heapify.

```python
def case_tle_heap(rng):
    """Maximize priority queue operations."""
    N_val = 200000
    # Alternating values force constant heapify
    a = [(i if i % 2 == 0 else -i) for i in range(1, N_val + 1)]
    return {"n": N_val, "a": a}
```

#### 1.10 Recursion without memoization

**Trigger:** Solution has recursive calls with overlapping subproblems but no memoization table.

**Why it TLEs:** Exponential call stack. fib(40) ≈ 10^8 calls.

**How to build the attack:**
- Use the maximum n that causes exponential blowup.
- For fib-like recursion: n=40-45 for 1s limit.

```python
def case_tle_recursion(rng):
    """Maximize recursive call count."""
    N_val = 40  # Fibonacci(40) ≈ 10^8 calls
    return {"n": N_val}
```

**Step 2: Calculate TLE operations based on time limit**

```
Time Limit    Target Operations
≤ 0.5s       ~4×10^8
1.0s         ~2×10^8
2.0s         ~1×10^8
```

Use this to calibrate n, array sizes, and pool sizes in your custom TLE cases.

**Step 3: Skip TLE if not needed**

If the solution uses only O(n) or O(n log n) algorithms with efficient data structures (`map`, `set`, `sort`, `priority_queue`), no custom TLE case is needed. Do NOT add one.

**Key rules for ALL TLE cases:**
- Values must fit within the constraint range from the problem statement
- Array sizes should be at or near maximum constraint
- The custom case must be a valid input (not garbage)
- Include a comment explaining the attack vector

### Sample Test Cases (REQUIRED)

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

## Framework Features

- **Deduplication**: The framework automatically removes duplicate test cases. You don't need to worry about producing identical inputs - they will be filtered out.
- **Auto-filling**: If you define fewer custom cases than `testcases` count, the framework fills the rest with random valid inputs.

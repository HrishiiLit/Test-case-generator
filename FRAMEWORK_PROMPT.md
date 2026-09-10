# Framework Reference

Quick reference for the testcase-generation framework. For full generation instructions, see `PROMPT.md`.

## Quick Start

```
1. Create contest folder:    contests/MyContest/
2. Create problem folder:    contests/MyContest/Problem_1/
3. Add solution:             contests/MyContest/Problem_1/solution.cpp
4. Get spec from LLM:       Provide PROMPT.md + problem statement + solution.cpp
5. Verify samples:           Check the 2-3 sample test cases (N=5-20, values 1-100)
6. Add spec:                 contests/MyContest/Problem_1/spec.py
7. Generate:                 python generate_tests.py contests/MyContest
8. Find ZIP:                 contests/MyContest/Problem_1/Problem_1.zip
9. Upload to HackerRank
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

## Output

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

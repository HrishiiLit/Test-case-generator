from framework import *

spec = Problem(
    name="Array Sum",
    testcases=15
)

N = Integer(name="N", min_value=1, max_value=50)
A = Array(name="A", size=N, min_value=-100, max_value=100)

spec.input(N, A)

spec.add_testcases(
    minimum(),
    maximum(),
    all_zero(),
    all_equal(),
    positive_only(),
    negative_only(),
    mixed_signs(),
    increasing(),
    decreasing(),
    alternating(),
    duplicates(),
    boundary_values(),
    random_case(),
    random_case(),
    stress_case(),
)

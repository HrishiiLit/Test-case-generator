from framework import *

spec = Problem(
    name="Two Sum",
    testcases=15
)

N = Integer(name="N", min_value=2, max_value=20)
Target = Integer(name="Target", min_value=1, max_value=100)
A = Array(name="A", size=N, min_value=1, max_value=50)

spec.input(Line(N, Target), A)

spec.add_testcases(
    minimum(),
    maximum(),
    all_equal(),
    increasing(),
    decreasing(),
    random_case(),
    random_case(),
    random_case(),
    random_case(),
    random_case(),
    stress_case(),
    boundary_values(),
    alternating(),
    duplicates(),
    mixed_signs(),
)

from framework import *

# Two Sum
# Find two distinct indices i < j such that a[i] + a[j] == target.
#
# Constraints:
# 2 <= n <= 200000
# -10^9 <= a[i] <= 10^9
# -2*10^9 <= target <= 2*10^9

spec = Problem(name="Two Sum", testcases=15)

n = Integer(name="n", min_value=2, max_value=200000)
target = LongInteger(name="target", min_value=-2 * 10**9, max_value=2 * 10**9)
a = Array(name="a", size=n, min_value=-10**9, max_value=10**9)

spec.input(n, target, a)

spec.add_testcases(
    minimum(),
    maximum(),
    all_equal(),
    all_zero(),
    random_case(),
)


# ---------------------------------------------------------
# Custom cases
# ---------------------------------------------------------

def case_small_pair(rng):
    return {
        "n": 5,
        "target": 9,
        "a": [2, 7, 11, 15, 3]
    }


def case_no_pair(rng):
    return {
        "n": 6,
        "target": 100,
        "a": [1, 2, 3, 4, 5, 6]
    }


def case_duplicate_pair(rng):
    return {
        "n": 8,
        "target": 10,
        "a": [5, 5, 1, 2, 3, 4, 20, 30]
    }


def case_negative_values(rng):
    return {
        "n": 7,
        "target": -5,
        "a": [-10, 5, -3, -2, 8, 12, 20]
    }


def case_zero_sum(rng):
    return {
        "n": 6,
        "target": 0,
        "a": [-5, 2, 7, -2, 10, -7]
    }


def case_pair_at_end(rng):
    return {
        "n": 10,
        "target": 100,
        "a": [1, 2, 3, 4, 5, 6, 7, 8, 9, 91]
    }


def case_extreme_values(rng):
    return {
        "n": 6,
        "target": 0,
        "a": [-10**9, 10**9, -999999999, 999999999, 123, -123]
    }


def case_large_duplicates(rng):
    N = 200000
    return {
        "n": N,
        "target": 0,
        "a": [7] * (N // 2) + [-7] * (N - N // 2)
    }


def case_large_no_pair(rng):
    N = 200000
    a = list(range(1, N + 1))

    # Maximum possible sum is (N-1) + N.
    # Use a target greater than that while remaining within target bounds.
    return {
        "n": N,
        "target": 2 * 10**9,
        "a": a
    }


def case_large_pair(rng):
    N = 200000
    a = list(range(1, N + 1))

    # Put a guaranteed pair at the end.
    a[-2] = 999999999
    a[-1] = 1

    return {
        "n": N,
        "target": 1000000000,
        "a": a
    }


spec.add_custom_case(case_small_pair)
spec.add_custom_case(case_no_pair)
spec.add_custom_case(case_duplicate_pair)
spec.add_custom_case(case_negative_values)
spec.add_custom_case(case_zero_sum)
spec.add_custom_case(case_pair_at_end)
spec.add_custom_case(case_extreme_values)
spec.add_custom_case(case_large_duplicates)
spec.add_custom_case(case_large_no_pair)
spec.add_custom_case(case_large_pair)
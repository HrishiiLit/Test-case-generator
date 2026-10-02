from framework import *

# Problem:
# Given n integers and a target value, find the first pair of indices
# i < j such that a[i] + a[j] == target.
# If no such pair exists, print -1.
#
# Constraints chosen for this problem:
# 2 <= n <= 200000
# -10^9 <= a[i] <= 10^9
# -2*10^9 <= target <= 2*10^9

spec = Problem(name="Two Sum", testcases=10)

n = Integer(name="n", min_value=2, max_value=200000)
target = LongInteger(name="target", min_value=-2 * 10**9, max_value=2 * 10**9)
a = Array(
    name="a",
    size=n,
    min_value=-10**9,
    max_value=10**9
)

spec.input(n, target, a)


# ------------------------------------------------------------
# Custom test cases
# ------------------------------------------------------------

def case_small_pair(rng):
    return {
        "n": 5,
        "target": 9,
        "a": [2, 7, 4, 5, 10]
    }


def case_no_solution(rng):
    return {
        "n": 8,
        "target": 100,
        "a": [1, 2, 3, 4, 5, 6, 7, 8]
    }


def case_duplicate_values(rng):
    return {
        "n": 10,
        "target": 10,
        "a": [5, 5, 1, 9, 2, 8, 3, 7, 4, 6]
    }


def case_negative_values(rng):
    return {
        "n": 8,
        "target": -3,
        "a": [-10, 7, -5, 2, 4, -8, 5, 9]
    }


def case_first_pair_not_unique(rng):
    return {
        "n": 7,
        "target": 10,
        "a": [1, 9, 4, 6, 2, 8, 5]
    }


def case_pair_at_end(rng):
    return {
        "n": 12,
        "target": 50,
        "a": [1, 3, 7, 11, 15, 19, 21, 25, 30, 40, 12, 20]
    }


def case_all_equal(rng):
    return {
        "n": 20,
        "target": 20,
        "a": [10] * 20
    }


def case_large_no_solution(rng):
    # Maximum n with no valid pair.
    # Forces the O(n^2) solution to inspect every pair.
    N = 200000
    return {
        "n": N,
        "target": 2000000000,
        "a": [i - 1000000000 for i in range(N)]
    }


def case_large_negative(rng):
    N = 200000
    return {
        "n": N,
        "target": -2000000000,
        "a": [-1000000000] * N
    }


spec.add_custom_case(case_small_pair)
spec.add_custom_case(case_no_solution)
spec.add_custom_case(case_duplicate_values)
spec.add_custom_case(case_negative_values)
spec.add_custom_case(case_first_pair_not_unique)
spec.add_custom_case(case_pair_at_end)
spec.add_custom_case(case_all_equal)
spec.add_custom_case(case_large_no_solution)
spec.add_custom_case(case_large_negative)
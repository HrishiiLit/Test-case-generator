from framework import *

# Problem:
# Given an array a of length n, construct b by concatenating a exactly k times.
# Count the number of positions l (1-indexed) such that:
#
#     b[l] + b[l+1] + ... + b[n*k] >= x
#
# Constraints:
# 1 <= t <= 10^4
# 1 <= n, k <= 10^5
# 1 <= x <= 10^18
# 1 <= a[i] <= 10^8
#
# Additional constraints:
# sum(n) <= 2*10^5
# sum(k) <= 2*10^5
#
# The official solution uses binary search over the answer.
# A naive O(n*k) solution can be made to TLE because n*k can be 10^10.

spec = Problem(name="Count Suitable Positions", testcases=10)

t = Integer(name="t", min_value=1, max_value=10000)

n = Integer(name="n", min_value=1, max_value=100000)
k = Integer(name="k", min_value=1, max_value=100000)
x = LongInteger(name="x", min_value=1, max_value=10**18)

a = Array(
    name="a",
    size=n,
    min_value=1,
    max_value=10**8
)

spec.input(t, Blocks(n, k, x, a))


# ------------------------------------------------------------
# Custom test cases
# Every case respects:
#   sum(n) <= 2e5
#   sum(k) <= 2e5
# ------------------------------------------------------------

def case_small_basic(rng):
    return {
        "t": 3,
        "__blocks__": [
            {
                "n": 5,
                "k": 2,
                "x": 10,
                "a": [1, 2, 3, 4, 5]
            },
            {
                "n": 4,
                "k": 3,
                "x": 20,
                "a": [2, 4, 6, 8]
            },
            {
                "n": 6,
                "k": 1,
                "x": 100,
                "a": [1, 2, 3, 4, 5, 6]
            }
        ]
    }


def case_x_one(rng):
    # Since all a[i] >= 1, every suffix has sum >= 1.
    return {
        "t": 2,
        "__blocks__": [
            {
                "n": 5,
                "k": 4,
                "x": 1,
                "a": [1, 2, 3, 4, 5]
            },
            {
                "n": 8,
                "k": 2,
                "x": 1,
                "a": [100, 1, 50, 2, 25, 3, 10, 4]
            }
        ]
    }


def case_x_too_large(rng):
    # Total sum < x => answer must be 0.
    return {
        "t": 3,
        "__blocks__": [
            {
                "n": 5,
                "k": 2,
                "x": 1000,
                "a": [1, 2, 3, 4, 5]
            },
            {
                "n": 3,
                "k": 5,
                "x": 10000,
                "a": [10, 20, 30]
            },
            {
                "n": 7,
                "k": 1,
                "x": 100,
                "a": [1, 1, 1, 1, 1, 1, 1]
            }
        ]
    }


def case_exact_total(rng):
    # x equals the entire sum of b.
    # Only l = 1 is suitable.
    return {
        "t": 3,
        "__blocks__": [
            {
                "n": 5,
                "k": 2,
                "x": 30,
                "a": [1, 2, 3, 4, 5]
            },
            {
                "n": 4,
                "k": 3,
                "x": 60,
                "a": [2, 4, 6, 8]
            },
            {
                "n": 6,
                "k": 2,
                "x": 42,
                "a": [1, 2, 3, 4, 5, 6]
            }
        ]
    }


def case_all_equal(rng):
    # Useful for checking exact boundaries.
    return {
        "t": 3,
        "__blocks__": [
            {
                "n": 10,
                "k": 10,
                "x": 50,
                "a": [5] * 10
            },
            {
                "n": 7,
                "k": 9,
                "x": 100,
                "a": [3] * 7
            },
            {
                "n": 8,
                "k": 5,
                "x": 40,
                "a": [1] * 8
            }
        ]
    }


def case_large_k(rng):
    # n is small, k is maximum.
    # A naive construction of b is impossible because n*k is huge.
    return {
        "t": 4,
        "__blocks__": [
            {
                "n": 1,
                "k": 100000,
                "x": 500000000000,
                "a": [10000000]
            },
            {
                "n": 2,
                "k": 99999,
                "x": 999980000000,
                "a": [10000000, 10000000]
            },
            {
                "n": 3,
                "k": 50000,
                "x": 100000000000,
                "a": [1000000, 2000000, 3000000]
            },
            {
                "n": 4,
                "k": 1,
                "x": 1,
                "a": [100000000, 99999999, 99999998, 99999997]
            }
        ]
    }


def case_large_n(rng):
    # Large n with small k.
    # Tests binary search and suffix calculation.
    N = 50000

    return {
        "t": 3,
        "__blocks__": [
            {
                "n": N,
                "k": 1,
                "x": 10**12,
                "a": [100000000] * N
            },
            {
                "n": 40000,
                "k": 2,
                "x": 10**12,
                "a": [99999999] * 40000
            },
            {
                "n": 10000,
                "k": 3,
                "x": 10**12,
                "a": [50000000] * 10000
            }
        ]
    }


def case_maximum_constraints(rng):
    # Large total n and k while keeping the aggregate constraints valid.
    return {
        "t": 4,
        "__blocks__": [
            {
                "n": 50000,
                "k": 50000,
                "x": 10**18,
                "a": [100000000] * 50000
            },
            {
                "n": 50000,
                "k": 50000,
                "x": 1,
                "a": [1] * 50000
            },
            {
                "n": 50000,
                "k": 50000,
                "x": 10**17,
                "a": [99999999] * 50000
            },
            {
                "n": 50000,
                "k": 50000,
                "x": 10**18,
                "a": [100000000] * 50000
            }
        ]
    }


def case_varied_values(rng):
    return {
        "t": 5,
        "__blocks__": [
            {
                "n": 10,
                "k": 20,
                "x": 1000,
                "a": [1, 100, 2, 99, 3, 98, 4, 97, 5, 96]
            },
            {
                "n": 9,
                "k": 15,
                "x": 500,
                "a": [10, 20, 30, 40, 50, 60, 70, 80, 90]
            },
            {
                "n": 12,
                "k": 8,
                "x": 2000,
                "a": [100, 1, 100, 1, 100, 1, 100, 1, 100, 1, 100, 1]
            },
            {
                "n": 15,
                "k": 5,
                "x": 1500,
                "a": [5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75]
            },
            {
                "n": 20,
                "k": 4,
                "x": 10000,
                "a": [100000000 - i for i in range(20)]
            }
        ]
    }


def case_tle_naive(rng):
    # Attack against solutions that explicitly construct b or iterate
    # over all n*k positions.
    #
    # n*k = 100000 * 100000 = 10^10.
    # This is valid because n and k individually satisfy their limits.
    #
    # sum(n) and sum(k) are both 100000 here.

    return {
        "t": 1,
        "__blocks__": [
            {
                "n": 100000,
                "k": 100000,
                "x": 10**18,
                "a": [100000000] * 100000
            }
        ]
    }


spec.add_custom_case(case_small_basic)
spec.add_custom_case(case_x_one)
spec.add_custom_case(case_x_too_large)
spec.add_custom_case(case_exact_total)
spec.add_custom_case(case_all_equal)
spec.add_custom_case(case_large_k)
spec.add_custom_case(case_large_n)
spec.add_custom_case(case_maximum_constraints)
spec.add_custom_case(case_varied_values)
spec.add_custom_case(case_tle_naive)
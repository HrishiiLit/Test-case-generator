from framework import *

spec = Problem(name="Polycarp Resting Hours", testcases=20)

N = Integer(name="N", min_value=1, max_value=200000)
A = Array(name="A", size=N, min_value=0, max_value=1)

spec.input(N, A)


def single_working_hour(rng):
    return {"N": 1, "A": [0]}


def all_resting_except_first(rng):
    n = rng.randint(2, 200000)
    return {"N": n, "A": [0] + [1] * (n - 1)}


def all_resting_except_last(rng):
    n = rng.randint(2, 200000)
    return {"N": n, "A": [1] * (n - 1) + [0]}


def all_resting_except_middle(rng):
    n = rng.randint(3, 200000)
    a = [1] * n
    a[n // 2] = 0
    return {"N": n, "A": a}


def alternating_zero_one(rng):
    n = rng.randint(2, 200000)
    a = [i % 2 for i in range(n)]
    return {"N": n, "A": a}


def alternating_one_zero(rng):
    n = rng.randint(2, 200000)
    a = [1 - (i % 2) for i in range(n)]
    return {"N": n, "A": a}


def two_working_hours(rng):
    return {"N": 2, "A": [0, 1]}


def zero_at_both_ends(rng):
    n = rng.randint(3, 200000)
    a = [0] + [1] * (n - 2) + [0]
    return {"N": n, "A": a}


def split_long_rest_blocks(rng):
    n = rng.randint(10, 200000)
    pos = rng.randint(1, n - 2)
    a = [1] * n
    a[pos] = 0
    return {"N": n, "A": a}


def many_zeros(rng):
    n = rng.randint(10, 200000)
    a = [0 if rng.random() < 0.5 else 1 for _ in range(n)]
    if all(x == 1 for x in a):
        a[rng.randrange(n)] = 0
    return {"N": n, "A": a}


def sparse_zeros(rng):
    n = rng.randint(10, 200000)
    a = [1] * n
    zero_count = max(1, n // 100)
    positions = rng.sample(range(n), zero_count)
    for p in positions:
        a[p] = 0
    return {"N": n, "A": a}


def large_almost_all_resting(rng):
    n = 200000
    a = [1] * n
    a[rng.randrange(n)] = 0
    return {"N": n, "A": a}


def large_alternating(rng):
    n = 200000
    a = [i % 2 for i in range(n)]
    return {"N": n, "A": a}


def large_zero_blocks(rng):
    n = 200000
    a = [1] * n

    for i in range(0, n, 10000):
        a[i] = 0

    return {"N": n, "A": a}


def circular_boundary_case(rng):
    n = rng.randint(5, 200000)
    a = [0] * n
    a[0] = 1
    a[-1] = 1
    return {"N": n, "A": a}


def maximum_valid_case(rng):
    n = 200000
    return {"N": n, "A": [1] * (n - 1) + [0]}


spec.add_custom_case(single_working_hour)
spec.add_custom_case(all_resting_except_first)
spec.add_custom_case(all_resting_except_last)
spec.add_custom_case(all_resting_except_middle)
spec.add_custom_case(alternating_zero_one)
spec.add_custom_case(alternating_one_zero)
spec.add_custom_case(two_working_hours)
spec.add_custom_case(zero_at_both_ends)
spec.add_custom_case(split_long_rest_blocks)
spec.add_custom_case(many_zeros)
spec.add_custom_case(sparse_zeros)
spec.add_custom_case(large_almost_all_resting)
spec.add_custom_case(large_alternating)
spec.add_custom_case(large_zero_blocks)
spec.add_custom_case(circular_boundary_case)
spec.add_custom_case(maximum_valid_case)

spec.add_testcases(
    minimum(),
    all_zero(),
    random_case(),
    random_case(),
)
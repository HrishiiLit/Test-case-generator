from framework import *

spec = Problem(name="Number of Suitable Positions", testcases=20)

T = Integer(name="T", min_value=1, max_value=10000)
N = Integer(name="N", min_value=1, max_value=100000)
K = Integer(name="K", min_value=1, max_value=100000)
X = LongInteger(name="X", min_value=1, max_value=10**18)
A = Array(name="A", size=N, min_value=1, max_value=10**8)

spec.input(T, Blocks(Line(N, K, X), A))


def make_block(n, k, x, a):
    return {
        "N": n,
        "K": k,
        "X": x,
        "A": a
    }


def multi_minimum(rng):
    blocks = [
        make_block(1, 1, 1, [1])
    ]
    return {"T": 1, "__blocks__": blocks}


def multi_single_large_k(rng):
    blocks = []
    for _ in range(10):
        k = rng.randint(1, 100000)
        a_value = rng.randint(1, 10**8)
        total = a_value * k
        x = rng.randint(1, total)
        blocks.append(make_block(1, k, x, [a_value]))

    return {"T": len(blocks), "__blocks__": blocks}


def multi_single_large_n(rng):
    n = 100000
    k = 1
    a = [rng.randint(1, 10**8) for _ in range(n)]
    total = sum(a)

    return {
        "T": 1,
        "__blocks__": [
            make_block(n, k, rng.randint(1, total), a)
        ]
    }


def multi_large_n_k(rng):
    blocks = []

    n1 = 100000
    k1 = 100000
    a1 = [10**8] * n1

    blocks.append(make_block(n1, k1, 10**18, a1))

    return {"T": 1, "__blocks__": blocks}


def multi_maximum_values(rng):
    blocks = [
        make_block(
            100000,
            100000,
            10**18,
            [10**8] * 100000
        )
    ]

    return {"T": 1, "__blocks__": blocks}


def multi_impossible(rng):
    blocks = []

    sum_n = 0
    sum_k = 0

    while sum_n < 200000 and sum_k < 200000 and len(blocks) < 20:
        n = rng.randint(1, min(100000, 200000 - sum_n))
        k = rng.randint(1, min(100000, 200000 - sum_k))

        # Keep the total safely below 1e18.
        a = [rng.randint(1, 100) for _ in range(n)]
        total = sum(a) * k

        x = total + 1

        blocks.append(make_block(n, k, x, a))
        sum_n += n
        sum_k += k

    return {"T": len(blocks), "__blocks__": blocks}


def multi_exact_total(rng):
    blocks = []

    sum_n = 0
    sum_k = 0

    while sum_n < 200000 and sum_k < 200000 and len(blocks) < 20:
        n = rng.randint(1, min(10000, 200000 - sum_n))
        k = rng.randint(1, min(10000, 200000 - sum_k))

        a = [rng.randint(1, 100000) for _ in range(n)]
        total = sum(a) * k

        blocks.append(make_block(n, k, total, a))

        sum_n += n
        sum_k += k

    return {"T": len(blocks), "__blocks__": blocks}


def multi_x_one(rng):
    blocks = []

    sum_n = 0
    sum_k = 0

    for _ in range(100):
        if sum_n >= 200000 or sum_k >= 200000:
            break

        n = rng.randint(1, min(2000, 200000 - sum_n))
        k = rng.randint(1, min(2000, 200000 - sum_k))
        a = [rng.randint(1, 10**8) for _ in range(n)]

        blocks.append(make_block(n, k, 1, a))

        sum_n += n
        sum_k += k

    return {"T": len(blocks), "__blocks__": blocks}


def multi_all_equal(rng):
    blocks = []

    sum_n = 0
    sum_k = 0

    while sum_n < 200000 and sum_k < 200000 and len(blocks) < 30:
        n = rng.randint(1, min(10000, 200000 - sum_n))
        k = rng.randint(1, min(10000, 200000 - sum_k))
        value = rng.randint(1, 10**8)

        a = [value] * n
        total = value * n * k
        x = rng.randint(1, total)

        blocks.append(make_block(n, k, x, a))

        sum_n += n
        sum_k += k

    return {"T": len(blocks), "__blocks__": blocks}


def multi_increasing(rng):
    blocks = []

    sum_n = 0
    sum_k = 0

    while sum_n < 200000 and sum_k < 200000 and len(blocks) < 20:
        n = rng.randint(1, min(10000, 200000 - sum_n))
        k = rng.randint(1, min(10000, 200000 - sum_k))

        a = [i + 1 for i in range(n)]
        total = sum(a) * k
        x = rng.randint(1, total)

        blocks.append(make_block(n, k, x, a))

        sum_n += n
        sum_k += k

    return {"T": len(blocks), "__blocks__": blocks}


def multi_decreasing(rng):
    blocks = []

    sum_n = 0
    sum_k = 0

    while sum_n < 200000 and sum_k < 200000 and len(blocks) < 20:
        n = rng.randint(1, min(10000, 200000 - sum_n))
        k = rng.randint(1, min(10000, 200000 - sum_k))

        a = list(range(n, 0, -1))
        total = sum(a) * k
        x = rng.randint(1, total)

        blocks.append(make_block(n, k, x, a))

        sum_n += n
        sum_k += k

    return {"T": len(blocks), "__blocks__": blocks}


def multi_alternating(rng):
    blocks = []

    sum_n = 0
    sum_k = 0

    while sum_n < 200000 and sum_k < 200000 and len(blocks) < 20:
        n = rng.randint(2, min(10000, 200000 - sum_n))
        k = rng.randint(1, min(10000, 200000 - sum_k))

        a = [1 if i % 2 == 0 else 10**8 for i in range(n)]
        total = sum(a) * k
        x = rng.randint(1, total)

        blocks.append(make_block(n, k, x, a))

        sum_n += n
        sum_k += k

    return {"T": len(blocks), "__blocks__": blocks}


def multi_one_huge_element(rng):
    blocks = []

    sum_n = 0
    sum_k = 0

    while sum_n < 200000 and sum_k < 200000 and len(blocks) < 20:
        n = rng.randint(2, min(10000, 200000 - sum_n))
        k = rng.randint(1, min(10000, 200000 - sum_k))

        a = [1] * n
        a[rng.randrange(n)] = 10**8

        total = sum(a) * k
        x = rng.randint(1, total)

        blocks.append(make_block(n, k, x, a))

        sum_n += n
        sum_k += k

    return {"T": len(blocks), "__blocks__": blocks}


def multi_prefix_heavy(rng):
    blocks = []

    sum_n = 0
    sum_k = 0

    while sum_n < 200000 and sum_k < 200000 and len(blocks) < 20:
        n = rng.randint(2, min(10000, 200000 - sum_n))
        k = rng.randint(1, min(10000, 200000 - sum_k))

        split = rng.randint(1, n - 1)
        a = [10**8] * split + [1] * (n - split)

        total = sum(a) * k
        x = rng.randint(1, total)

        blocks.append(make_block(n, k, x, a))

        sum_n += n
        sum_k += k

    return {"T": len(blocks), "__blocks__": blocks}


def multi_suffix_heavy(rng):
    blocks = []

    sum_n = 0
    sum_k = 0

    while sum_n < 200000 and sum_k < 200000 and len(blocks) < 20:
        n = rng.randint(2, min(10000, 200000 - sum_n))
        k = rng.randint(1, min(10000, 200000 - sum_k))

        split = rng.randint(1, n - 1)
        a = [1] * split + [10**8] * (n - split)

        total = sum(a) * k
        x = rng.randint(1, total)

        blocks.append(make_block(n, k, x, a))

        sum_n += n
        sum_k += k

    return {"T": len(blocks), "__blocks__": blocks}


def multi_repeated_values(rng):
    blocks = []

    sum_n = 0
    sum_k = 0

    values = [1, 2, 10, 100, 10000, 10**8]

    while sum_n < 200000 and sum_k < 200000 and len(blocks) < 30:
        n = rng.randint(1, min(10000, 200000 - sum_n))
        k = rng.randint(1, min(10000, 200000 - sum_k))

        a = [rng.choice(values) for _ in range(n)]
        total = sum(a) * k
        x = rng.randint(1, total)

        blocks.append(make_block(n, k, x, a))

        sum_n += n
        sum_k += k

    return {"T": len(blocks), "__blocks__": blocks}


def multi_random(rng):
    blocks = []

    sum_n = 0
    sum_k = 0

    target_cases = rng.randint(5, 100)

    for _ in range(target_cases):
        n_budget = 200000 - sum_n
        k_budget = 200000 - sum_k

        if n_budget < 1 or k_budget < 1:
            break

        n = rng.randint(1, min(100000, n_budget))
        k = rng.randint(1, min(100000, k_budget))

        a = [rng.randint(1, 10**8) for _ in range(n)]
        total = sum(a) * k

        x = rng.randint(1, min(total, 10**18))

        blocks.append(make_block(n, k, x, a))

        sum_n += n
        sum_k += k

    return {"T": len(blocks), "__blocks__": blocks}


def multi_stress_n_budget(rng):
    blocks = [
        make_block(
            100000,
            1,
            10**18,
            [10**8] * 100000
        ),
        make_block(
            100000,
            1,
            1,
            [1] * 100000
        )
    ]

    return {"T": 2, "__blocks__": blocks}


def multi_stress_k_budget(rng):
    blocks = [
        make_block(1, 100000, 10**18, [10**8]),
        make_block(1, 100000, 1, [1])
    ]

    return {"T": 2, "__blocks__": blocks}


def multi_max_t(rng):
    blocks = []

    for _ in range(10000):
        if rng.random() < 0.5:
            a = [1]
            x = 1
        else:
            a = [rng.randint(1, 10**8)]
            x = rng.randint(1, a[0])

        blocks.append(
            make_block(
                1,
                1,
                x,
                a
            )
        )

    return {"T": 10000, "__blocks__": blocks}


def multi_boundary_x(rng):
    blocks = []

    sum_n = 0
    sum_k = 0

    while sum_n < 200000 and sum_k < 200000 and len(blocks) < 30:
        n = rng.randint(1, min(10000, 200000 - sum_n))
        k = rng.randint(1, min(10000, 200000 - sum_k))

        a = [rng.randint(1, 10**8) for _ in range(n)]
        total = sum(a) * k

        x = rng.choice([
            1,
            max(1, total - 1),
            total
        ])

        blocks.append(make_block(n, k, x, a))

        sum_n += n
        sum_k += k

    return {"T": len(blocks), "__blocks__": blocks}


def multi_mixed_sizes(rng):
    blocks = []

    sizes = [
        (1, 1),
        (2, 100000),
        (100000, 1),
        (3, 99999),
        (99999, 2),
        (1000, 1000),
        (50000, 3),
        (3, 50000)
    ]

    sum_n = sum(n for n, k in sizes)
    sum_k = sum(k for n, k in sizes)

    # The selected sizes stay within both aggregate constraints.
    for n, k in sizes:
        a = [rng.randint(1, 10**8) for _ in range(n)]
        total = sum(a) * k
        x = rng.randint(1, min(total, 10**18))

        blocks.append(make_block(n, k, x, a))

    return {
        "T": len(blocks),
        "__blocks__": blocks
    }


def multi_large_values_near_limit(rng):
    blocks = []

    configurations = [
        (100000, 2),
        (50000, 4),
        (25000, 8),
        (10000, 20),
        (5000, 40)
    ]

    sum_n = sum(n for n, k in configurations)
    sum_k = sum(k for n, k in configurations)

    if sum_n > 200000 or sum_k > 200000:
        configurations = [(100000, 2), (50000, 4), (25000, 8)]

    for n, k in configurations:
        a = [10**8] * n
        total = sum(a) * k
        x = rng.choice([
            1,
            total // 2,
            total - 1,
            total
        ])

        blocks.append(make_block(n, k, x, a))

    return {
        "T": len(blocks),
        "__blocks__": blocks
    }


spec.add_custom_case(multi_minimum)
spec.add_custom_case(multi_single_large_k)
spec.add_custom_case(multi_single_large_n)
spec.add_custom_case(multi_large_n_k)
spec.add_custom_case(multi_maximum_values)
spec.add_custom_case(multi_impossible)
spec.add_custom_case(multi_exact_total)
spec.add_custom_case(multi_x_one)
spec.add_custom_case(multi_all_equal)
spec.add_custom_case(multi_increasing)
spec.add_custom_case(multi_decreasing)
spec.add_custom_case(multi_alternating)
spec.add_custom_case(multi_one_huge_element)
spec.add_custom_case(multi_prefix_heavy)
spec.add_custom_case(multi_suffix_heavy)
spec.add_custom_case(multi_repeated_values)
spec.add_custom_case(multi_random)
spec.add_custom_case(multi_stress_n_budget)
spec.add_custom_case(multi_stress_k_budget)
spec.add_custom_case(multi_max_t)
spec.add_custom_case(multi_boundary_x)
spec.add_custom_case(multi_mixed_sizes)
spec.add_custom_case(multi_large_values_near_limit)
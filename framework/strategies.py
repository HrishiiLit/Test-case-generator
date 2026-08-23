import random as _random
from framework.graphs import Graph, Tree


class _SyncDict(dict):
    """A dict that writes through to the strategy context.

    Ensures that when a variable (e.g., an Array) depends on another
    variable (e.g., N via size=N), it sees the value of N that was
    actually resolved for this testcase, not a fresh random one.
    """

    def __init__(self, context):
        super().__init__()
        self._context = context

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        self._context[key] = value

    def update(self, *args, **kwargs):
        super().update(*args, **kwargs)
        self._context.update(self)


def _resolve_bound(bound, context):
    if bound is None:
        return 0
    if callable(bound):
        return bound(context)
    if hasattr(bound, "resolve"):
        if bound.name in context:
            return int(context[bound.name])
        return bound.resolve(_random.Random(0), context)
    return int(bound)


def _has_explicit_size(v):
    sized = getattr(v, "size", None) is not None
    ranged = (
        getattr(v, "min_size", None) is not None
        and getattr(v, "max_size", None) is not None
    )
    return sized or ranged


def _make_scalar(v, val, context, rng):
    if isinstance(v, Graph):
        n = _resolve_bound(v.num_vertices, context)
        edges = []
        return {v.name: edges, f"{v.name}_n": n, f"{v.name}_m": 0}
    if isinstance(v, Tree):
        n = _resolve_bound(v.num_vertices, context)
        return {v.name: [], f"{v.name}_n": n}
    if hasattr(v, "_resolve_size"):
        n = v._resolve_size(rng, context)
        return {v.name: [val] * n}
    if hasattr(v, "alphabet"):
        n = _resolve_bound(v.length, context) if v.length else 5
        return {v.name: v.alphabet[0] * n if v.alphabet else "a" * n}
    return {v.name: val}


def minimum():
    def strategy(spec, rng, context):
        result = _SyncDict(context)
        for v in spec._variables:
            lo = _resolve_bound(v.min_value, context)
            result.update(_make_scalar(v, lo, context, rng))
        return result
    return strategy


def maximum():
    def strategy(spec, rng, context):
        result = _SyncDict(context)
        for v in spec._variables:
            hi = _resolve_bound(v.max_value, context)
            if isinstance(v, Graph):
                n = _resolve_bound(v.num_vertices, context)
                max_edges = n * (n - 1) // 2
                m = min(_resolve_bound(v.num_edges, context), max_edges) if v.num_edges else max_edges
                edges = []
                seen = set()
                for i in range(1, n + 1):
                    for j in range(i + 1, n + 1):
                        if len(edges) >= m:
                            break
                        edges.append((i, j))
                    if len(edges) >= m:
                        break
                result[v.name] = edges
                result[f"{v.name}_n"] = n
                result[f"{v.name}_m"] = len(edges)
            elif isinstance(v, Tree):
                n = _resolve_bound(v.num_vertices, context)
                edges = [(1, i) for i in range(2, n + 1)]
                result[v.name] = edges
                result[f"{v.name}_n"] = n
            elif hasattr(v, "_resolve_size"):
                n = v._resolve_size(rng, context)
                result[v.name] = [hi] * n
            elif hasattr(v, "alphabet"):
                n = _resolve_bound(v.length, context) if v.length else 20
                result[v.name] = (v.alphabet[-1] if v.alphabet else "z") * n
            else:
                result[v.name] = hi
        return result
    return strategy


def random_case():
    def strategy(spec, rng, context):
        result = _SyncDict(context)
        for v in spec._variables:
            if isinstance(v, Graph):
                n = _resolve_bound(v.num_vertices, context)
                m = _resolve_bound(v.num_edges, context) if v.num_edges else min(n, n * (n - 1) // 4)
                edges = v._generate_edges(n, m, rng)
                result[v.name] = edges
                result[f"{v.name}_n"] = n
                result[f"{v.name}_m"] = m
            elif isinstance(v, Tree):
                n = _resolve_bound(v.num_vertices, context)
                edges = v._generate_edges(n, rng)
                result[v.name] = edges
                result[f"{v.name}_n"] = n
            else:
                result[v.name] = v.resolve(rng, context)
        return result
    return strategy


def stress_case():
    def strategy(spec, rng, context):
        result = _SyncDict(context)
        for v in spec._variables:
            hi = _resolve_bound(v.max_value, context)
            lo = _resolve_bound(v.min_value, context)
            if isinstance(v, Graph):
                n = _resolve_bound(v.num_vertices, context)
                n = max(n, 50)
                max_edges = n * (n - 1) // 2
                m = min(max_edges, 200)
                edges = v._generate_edges(n, m, rng)
                result[v.name] = edges
                result[f"{v.name}_n"] = n
                result[f"{v.name}_m"] = m
            elif isinstance(v, Tree):
                n = _resolve_bound(v.num_vertices, context)
                n = max(n, 50)
                edges = v._generate_edges(n, rng)
                result[v.name] = edges
                result[f"{v.name}_n"] = n
            elif hasattr(v, "_resolve_size"):
                if _has_explicit_size(v):
                    n = v._resolve_size(rng, context)
                else:
                    n = max(50, _resolve_bound(v.max_size, context) if hasattr(v, "max_size") and v.max_size else 50)
                result[v.name] = [rng.randint(lo, hi) for _ in range(n)]
            elif hasattr(v, "alphabet"):
                n = _resolve_bound(v.length, context) if v.length else 50
                result[v.name] = "".join(rng.choice(v.alphabet) for _ in range(n))
            else:
                result[v.name] = hi
        return result
    return strategy


def all_equal():
    def strategy(spec, rng, context):
        result = _SyncDict(context)
        for v in spec._variables:
            lo = _resolve_bound(v.min_value, context)
            hi = _resolve_bound(v.max_value, context)
            val = rng.randint(lo, hi)
            result.update(_make_scalar(v, val, context, rng))
        return result
    return strategy


def all_zero():
    def strategy(spec, rng, context):
        result = _SyncDict(context)
        for v in spec._variables:
            lo = _resolve_bound(v.min_value, context)
            hi = _resolve_bound(v.max_value, context)
            if lo <= 0 <= hi:
                result.update(_make_scalar(v, 0, context, rng))
            else:
                result.update(_make_scalar(v, lo, context, rng))
        return result
    return strategy


def increasing():
    def strategy(spec, rng, context):
        result = _SyncDict(context)
        for v in spec._variables:
            lo = _resolve_bound(v.min_value, context)
            hi = _resolve_bound(v.max_value, context)
            if isinstance(v, (Graph, Tree)):
                result.update(_make_scalar(v, lo, context, rng))
            elif hasattr(v, "_resolve_size"):
                n = v._resolve_size(rng, context)
                step = max(1, (hi - lo) // max(n, 1))
                result[v.name] = [lo + i * step for i in range(n)]
            else:
                result[v.name] = rng.randint(lo, hi)
        return result
    return strategy


def decreasing():
    def strategy(spec, rng, context):
        result = _SyncDict(context)
        for v in spec._variables:
            lo = _resolve_bound(v.min_value, context)
            hi = _resolve_bound(v.max_value, context)
            if isinstance(v, (Graph, Tree)):
                result.update(_make_scalar(v, hi, context, rng))
            elif hasattr(v, "_resolve_size"):
                n = v._resolve_size(rng, context)
                step = max(1, (hi - lo) // max(n, 1))
                result[v.name] = [hi - i * step for i in range(n)]
            else:
                result[v.name] = rng.randint(lo, hi)
        return result
    return strategy


def mixed_signs():
    def strategy(spec, rng, context):
        result = _SyncDict(context)
        for v in spec._variables:
            lo = _resolve_bound(v.min_value, context)
            hi = _resolve_bound(v.max_value, context)
            if isinstance(v, (Graph, Tree)):
                result.update(_make_scalar(v, lo, context, rng))
            elif hasattr(v, "_resolve_size"):
                n = v._resolve_size(rng, context)
                values = []
                for i in range(n):
                    if i % 2 == 0 and lo < 0:
                        values.append(rng.randint(max(lo, -50), -1))
                    else:
                        values.append(rng.randint(1, min(hi, 50)) if hi > 0 else hi)
                result[v.name] = values
            elif lo < 0:
                result[v.name] = rng.randint(lo, -1)
            else:
                result[v.name] = rng.randint(max(lo, 1), max(hi, 1))
        return result
    return strategy


def positive_only():
    def strategy(spec, rng, context):
        result = _SyncDict(context)
        for v in spec._variables:
            lo = max(1, _resolve_bound(v.min_value, context))
            hi = _resolve_bound(v.max_value, context)
            if isinstance(v, (Graph, Tree)):
                result.update(_make_scalar(v, lo, context, rng))
            elif hasattr(v, "_resolve_size"):
                n = v._resolve_size(rng, context)
                result[v.name] = [rng.randint(lo, hi) for _ in range(n)]
            else:
                result[v.name] = rng.randint(lo, hi)
        return result
    return strategy


def negative_only():
    def strategy(spec, rng, context):
        result = _SyncDict(context)
        for v in spec._variables:
            lo = _resolve_bound(v.min_value, context)
            hi = min(-1, _resolve_bound(v.max_value, context))
            if lo > hi:
                hi = lo
            if isinstance(v, (Graph, Tree)):
                result.update(_make_scalar(v, lo, context, rng))
            elif hasattr(v, "_resolve_size"):
                n = v._resolve_size(rng, context)
                result[v.name] = [rng.randint(lo, hi) for _ in range(n)]
            else:
                result[v.name] = rng.randint(lo, hi)
        return result
    return strategy


def alternating():
    def strategy(spec, rng, context):
        result = _SyncDict(context)
        for v in spec._variables:
            lo = _resolve_bound(v.min_value, context)
            hi = _resolve_bound(v.max_value, context)
            if isinstance(v, (Graph, Tree)):
                result.update(_make_scalar(v, lo, context, rng))
            elif hasattr(v, "_resolve_size"):
                n = v._resolve_size(rng, context)
                a = rng.randint(lo, hi)
                b = rng.randint(lo, hi)
                result[v.name] = [a if i % 2 == 0 else b for i in range(n)]
            else:
                result[v.name] = rng.randint(lo, hi)
        return result
    return strategy


def boundary_values():
    def strategy(spec, rng, context):
        result = _SyncDict(context)
        for v in spec._variables:
            lo = _resolve_bound(v.min_value, context)
            hi = _resolve_bound(v.max_value, context)
            if isinstance(v, (Graph, Tree)):
                result.update(_make_scalar(v, lo, context, rng))
            elif hasattr(v, "_resolve_size"):
                n = v._resolve_size(rng, context)
                vals = [lo, hi, lo, hi, 0 if lo <= 0 <= hi else lo]
                while len(vals) < n:
                    vals.append(rng.randint(lo, hi))
                result[v.name] = vals[:n]
            else:
                result[v.name] = rng.choice([lo, hi, 0 if lo <= 0 <= hi else lo])
        return result
    return strategy


def duplicates():
    def strategy(spec, rng, context):
        result = _SyncDict(context)
        for v in spec._variables:
            lo = _resolve_bound(v.min_value, context)
            hi = _resolve_bound(v.max_value, context)
            if isinstance(v, (Graph, Tree)):
                result.update(_make_scalar(v, lo, context, rng))
            elif hasattr(v, "_resolve_size"):
                n = v._resolve_size(rng, context)
                k = max(1, n // 3)
                pool = [rng.randint(lo, hi) for _ in range(k)]
                result[v.name] = [pool[i % k] for i in range(n)]
            else:
                result[v.name] = rng.randint(lo, hi)
        return result
    return strategy


def min_length():
    def strategy(spec, rng, context):
        result = _SyncDict(context)
        for v in spec._variables:
            if isinstance(v, (Graph, Tree)):
                result.update(_make_scalar(v, 0, context, rng))
            elif hasattr(v, "alphabet"):
                n = _resolve_bound(v.min_length, context) if v.min_length else 1
                result[v.name] = "".join(rng.choice(v.alphabet) for _ in range(n))
            elif hasattr(v, "_resolve_size"):
                n = v._resolve_size(rng, context) if _has_explicit_size(v) else 1
                lo = _resolve_bound(v.min_value, context)
                hi = _resolve_bound(v.max_value, context)
                result[v.name] = [rng.randint(lo, hi) for _ in range(n)]
            else:
                result[v.name] = _resolve_bound(v.min_value, context)
        return result
    return strategy


def max_length():
    def strategy(spec, rng, context):
        result = _SyncDict(context)
        for v in spec._variables:
            if isinstance(v, (Graph, Tree)):
                result.update(_make_scalar(v, 0, context, rng))
            elif hasattr(v, "alphabet"):
                n = _resolve_bound(v.max_length, context) if v.max_length else 100
                result[v.name] = "".join(rng.choice(v.alphabet) for _ in range(n))
            elif hasattr(v, "_resolve_size"):
                n = v._resolve_size(rng, context) if _has_explicit_size(v) else 100
                lo = _resolve_bound(v.min_value, context)
                hi = _resolve_bound(v.max_value, context)
                result[v.name] = [rng.randint(lo, hi) for _ in range(n)]
            else:
                result[v.name] = _resolve_bound(v.max_value, context)
        return result
    return strategy


def single_char():
    def strategy(spec, rng, context):
        result = _SyncDict(context)
        for v in spec._variables:
            if isinstance(v, (Graph, Tree)):
                result.update(_make_scalar(v, 0, context, rng))
            elif hasattr(v, "alphabet"):
                result[v.name] = rng.choice(v.alphabet)
            else:
                result[v.name] = _resolve_bound(v.min_value, context)
        return result
    return strategy


def all_same_char():
    def strategy(spec, rng, context):
        result = _SyncDict(context)
        for v in spec._variables:
            if isinstance(v, (Graph, Tree)):
                result.update(_make_scalar(v, 0, context, rng))
            elif hasattr(v, "alphabet"):
                ch = rng.choice(v.alphabet)
                n = _resolve_bound(v.length, context) if v.length else rng.randint(5, 20)
                result[v.name] = ch * n
            else:
                result[v.name] = _resolve_bound(v.min_value, context)
        return result
    return strategy


def alternating_chars():
    def strategy(spec, rng, context):
        result = _SyncDict(context)
        for v in spec._variables:
            if isinstance(v, (Graph, Tree)):
                result.update(_make_scalar(v, 0, context, rng))
            elif hasattr(v, "alphabet"):
                n = _resolve_bound(v.length, context) if v.length else rng.randint(5, 20)
                a, b = rng.sample(v.alphabet, 2) if len(v.alphabet) >= 2 else (v.alphabet[0], v.alphabet[0])
                result[v.name] = "".join(a if i % 2 == 0 else b for i in range(n))
            else:
                result[v.name] = _resolve_bound(v.min_value, context)
        return result
    return strategy


def palindrome():
    def strategy(spec, rng, context):
        result = _SyncDict(context)
        for v in spec._variables:
            if isinstance(v, (Graph, Tree)):
                result.update(_make_scalar(v, 0, context, rng))
            elif hasattr(v, "alphabet"):
                n = _resolve_bound(v.length, context) if v.length else rng.randint(5, 20)
                half = n // 2
                left = "".join(rng.choice(v.alphabet) for _ in range(half))
                mid = rng.choice(v.alphabet) if n % 2 == 1 else ""
                result[v.name] = left + mid + left[::-1]
            else:
                result[v.name] = _resolve_bound(v.min_value, context)
        return result
    return strategy


def repeated_pattern():
    def strategy(spec, rng, context):
        result = _SyncDict(context)
        for v in spec._variables:
            if isinstance(v, (Graph, Tree)):
                result.update(_make_scalar(v, 0, context, rng))
            elif hasattr(v, "alphabet"):
                pat_len = rng.randint(2, 5)
                pattern = "".join(rng.choice(v.alphabet) for _ in range(pat_len))
                n = _resolve_bound(v.length, context) if v.length else rng.randint(10, 30)
                result[v.name] = (pattern * (n // pat_len + 1))[:n]
            else:
                result[v.name] = _resolve_bound(v.min_value, context)
        return result
    return strategy


def chain():
    def strategy(spec, rng, context):
        result = _SyncDict(context)
        for v in spec._variables:
            if isinstance(v, Graph):
                n = _resolve_bound(v.num_vertices, context)
                edges = [(i, i + 1) for i in range(1, n)]
                result[v.name] = edges
                result[f"{v.name}_n"] = n
                result[f"{v.name}_m"] = len(edges)
            elif isinstance(v, Tree):
                n = _resolve_bound(v.num_vertices, context)
                edges = [(i, i + 1) for i in range(1, n)]
                result[v.name] = edges
                result[f"{v.name}_n"] = n
            else:
                result.update(_make_scalar(v, _resolve_bound(v.min_value, context), context, rng))
        return result
    return strategy


def star():
    def strategy(spec, rng, context):
        result = _SyncDict(context)
        for v in spec._variables:
            if isinstance(v, Graph):
                n = _resolve_bound(v.num_vertices, context)
                edges = [(1, i) for i in range(2, n + 1)]
                result[v.name] = edges
                result[f"{v.name}_n"] = n
                result[f"{v.name}_m"] = len(edges)
            elif isinstance(v, Tree):
                n = _resolve_bound(v.num_vertices, context)
                edges = [(1, i) for i in range(2, n + 1)]
                result[v.name] = edges
                result[f"{v.name}_n"] = n
            else:
                result.update(_make_scalar(v, _resolve_bound(v.min_value, context), context, rng))
        return result
    return strategy


def disconnected():
    def strategy(spec, rng, context):
        result = _SyncDict(context)
        for v in spec._variables:
            if isinstance(v, Graph):
                n = _resolve_bound(v.num_vertices, context)
                half = max(2, n // 2)
                edges = [(i, i + 1) for i in range(1, half)]
                edges += [(half + i, half + i + 1) for i in range(1, n - half)]
                result[v.name] = edges
                result[f"{v.name}_n"] = n
                result[f"{v.name}_m"] = len(edges)
            else:
                result.update(_make_scalar(v, _resolve_bound(v.min_value, context), context, rng))
        return result
    return strategy


def dense():
    def strategy(spec, rng, context):
        result = _SyncDict(context)
        for v in spec._variables:
            if isinstance(v, Graph):
                n = _resolve_bound(v.num_vertices, context)
                edges = []
                for i in range(1, n + 1):
                    for j in range(i + 1, n + 1):
                        if rng.random() < 0.7:
                            edges.append((i, j))
                if not edges:
                    edges = [(1, 2)]
                result[v.name] = edges
                result[f"{v.name}_n"] = n
                result[f"{v.name}_m"] = len(edges)
            else:
                result.update(_make_scalar(v, _resolve_bound(v.min_value, context), context, rng))
        return result
    return strategy


def single_node():
    def strategy(spec, rng, context):
        result = _SyncDict(context)
        for v in spec._variables:
            if isinstance(v, Tree):
                result[v.name] = []
                result[f"{v.name}_n"] = 1
            elif isinstance(v, Graph):
                result[v.name] = []
                result[f"{v.name}_n"] = 1
                result[f"{v.name}_m"] = 0
            else:
                result.update(_make_scalar(v, _resolve_bound(v.min_value, context), context, rng))
        return result
    return strategy


def balanced():
    def strategy(spec, rng, context):
        result = _SyncDict(context)
        for v in spec._variables:
            if isinstance(v, Tree):
                n = _resolve_bound(v.num_vertices, context)
                edges = [(i // 2, i) for i in range(2, n + 1)]
                result[v.name] = edges
                result[f"{v.name}_n"] = n
            else:
                result.update(_make_scalar(v, _resolve_bound(v.min_value, context), context, rng))
        return result
    return strategy


def skewed():
    def strategy(spec, rng, context):
        result = _SyncDict(context)
        for v in spec._variables:
            if isinstance(v, Tree):
                n = _resolve_bound(v.num_vertices, context)
                edges = [(i, i + 1) for i in range(1, n)]
                result[v.name] = edges
                result[f"{v.name}_n"] = n
            else:
                result.update(_make_scalar(v, _resolve_bound(v.min_value, context), context, rng))
        return result
    return strategy

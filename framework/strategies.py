import random as _random
from framework.graphs import Graph, Tree
from framework.generators import resolve_bound, resolve_range


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


def _has_explicit_size(v):
    sized = getattr(v, "size", None) is not None
    ranged = (
        getattr(v, "min_size", None) is not None
        and getattr(v, "max_size", None) is not None
    )
    return sized or ranged


def _applicable(fn, check):
    """Tag a strategy closure with an ``applicable(spec) -> reason|None`` check."""
    fn.applicable = check
    return fn


def _declared_range(bound):
    """Inclusive ``(lo, hi)`` for a literal or ``_Var`` bound, else ``None``."""
    if bound is None:
        return None
    if hasattr(bound, "min_value") and hasattr(bound, "max_value"):
        lo = getattr(bound, "min_value", None)
        hi = getattr(bound, "max_value", None)
        if lo is None or hi is None:
            return None
        try:
            return int(resolve_bound(lo, {})), int(resolve_bound(hi, {}))
        except Exception:
            return None
    try:
        value = int(resolve_bound(bound, {}))
    except Exception:
        return None
    return value, value


def _needs_array(strategy_name):
    def check(spec):
        for v in spec._variables:
            if hasattr(v, "_resolve_size"):
                return None
        return f"{strategy_name} needs at least one array variable"
    return check


def _needs_graph_or_tree(strategy_name):
    def check(spec):
        for v in spec._variables:
            if isinstance(v, (Graph, Tree)):
                return None
        return f"{strategy_name} needs a Graph or Tree variable"
    return check


def _needs_graph(strategy_name):
    def check(spec):
        for v in spec._variables:
            if isinstance(v, Graph):
                return None
        return f"{strategy_name} needs a Graph variable"
    return check


def _needs_tree(strategy_name):
    def check(spec):
        for v in spec._variables:
            if isinstance(v, Tree):
                return None
        return f"{strategy_name} needs a Tree variable"
    return check


def _needs_string(strategy_name):
    def check(spec):
        for v in spec._variables:
            if hasattr(v, "alphabet"):
                return None
        return f"{strategy_name} needs a String variable"
    return check


def _vertex_range(v, context, default=(1, 1)):
    return resolve_range(getattr(v, "num_vertices", None), context, default)


def _edge_range(v, context, default=(0, None)):
    return resolve_range(getattr(v, "num_edges", None), context, default)


def _max_edges(n, directed):
    if n < 2:
        return 0
    return n * (n - 1) if directed else n * (n - 1) // 2


def _edge_pool(n, directed):
    if n < 2:
        return []
    if directed:
        return [(a, b) for a in range(1, n + 1) for b in range(1, n + 1) if a != b]
    return [(a, b) for a in range(1, n + 1) for b in range(a + 1, n + 1)]


def _weighted(v, pairs, rng):
    if not v.weighted:
        return list(pairs)
    return [(a, b, rng.randint(v.weight_min, v.weight_max)) for a, b in pairs]


def _pick_edges(v, n, m, rng):
    """Choose exactly ``m`` simple edges on ``n`` vertices, or explain why not."""
    cap = _max_edges(n, v.directed)
    if m > cap:
        raise ValueError(f"cannot place {m} edges on {n} vertices (max {cap})")
    if m == 0:
        return []
    if m > cap // 2:
        if cap > 2_000_000:
            raise ValueError(
                f"graph is too dense to build directly ({m} of {cap} possible edges)"
            )
        pool = _edge_pool(n, v.directed)
        rng.shuffle(pool)
        return _weighted(v, pool[:m], rng)
    return v._generate_edges(n, m, rng)


def _fit_n(m, lo, hi, directed):
    """Smallest vertex count in ``[lo, hi]`` that can hold ``m`` simple edges."""
    for n in range(lo, hi + 1):
        if _max_edges(n, directed) >= m:
            return n
    raise ValueError(
        f"no vertex count in [{lo}, {hi}] can hold {m} edges "
        f"(num_vertices / num_edges constraints conflict)"
    )


def _graph_case(v, context, rng, mode):
    """Build a Graph value dict honouring declared num_vertices/num_edges.

    ``mode`` is ``min`` (smallest feasible), ``max`` (largest declared) or
    ``random`` (a declared-feasible draw), so every strategy yields a graph
    that passes validation instead of an arbitrary or empty edge list.
    """
    nlo, nhi = _vertex_range(v, context)
    mlo, mhi = _edge_range(v, context)
    if nlo > nhi:
        raise ValueError(f"num_vertices range is empty: [{nlo}, {nhi}]")

    if mode == "min":
        n = _fit_n(mlo, nlo, nhi, v.directed)
        m = mlo
    elif mode == "max":
        n = nhi
        cap = _max_edges(n, v.directed)
        m = cap if mhi is None else min(mhi, cap)
        if m < mlo:
            raise ValueError(
                f"{n} vertices fit only {cap} edges but num_edges minimum is {mlo}"
            )
    else:
        n = _fit_n(mlo, rng.randint(nlo, nhi), nhi, v.directed)
        cap = _max_edges(n, v.directed)
        upper = cap if mhi is None else min(mhi, cap)
        if upper < mlo:
            raise ValueError(
                f"{n} vertices fit only {cap} edges but num_edges minimum is {mlo}"
            )
        m = rng.randint(mlo, upper)

    edges = _pick_edges(v, n, m, rng)
    return {v.name: edges, f"{v.name}_n": n, f"{v.name}_m": len(edges)}


def _tree_case(v, context, rng, mode):
    nlo, nhi = _vertex_range(v, context)
    if nlo > nhi:
        raise ValueError(f"num_vertices range is empty: [{nlo}, {nhi}]")
    if mode == "min":
        n = nlo
    elif mode == "max":
        n = nhi
    else:
        n = rng.randint(nlo, nhi)
    if n < 1:
        raise ValueError(f"num_vertices minimum is {nlo}; cannot build a tree")
    return {v.name: v._generate_edges(n, rng), f"{v.name}_n": n}


def _make_scalar(v, val, context, rng):
    if isinstance(v, Graph):
        return _graph_case(v, context, rng, "min")
    if isinstance(v, Tree):
        return _tree_case(v, context, rng, "min")
    if hasattr(v, "_resolve_size"):
        n = v._resolve_size(rng, context)
        return {v.name: [val] * n}
    if hasattr(v, "alphabet"):
        n = resolve_bound(v.length, context) if v.length else 5
        return {v.name: v.alphabet[0] * n if v.alphabet else "a" * n}
    return {v.name: val}


def minimum():
    def minimum_strategy(spec, rng, context):
        result = _SyncDict(context)
        for v in spec._variables:
            lo = resolve_bound(getattr(v, "min_value", None), context)
            result.update(_make_scalar(v, lo, context, rng))
        return result
    return minimum_strategy


def maximum():
    def maximum_strategy(spec, rng, context):
        result = _SyncDict(context)
        for v in spec._variables:
            if isinstance(v, Graph):
                result.update(_graph_case(v, context, rng, "max"))
            elif isinstance(v, Tree):
                result.update(_tree_case(v, context, rng, "max"))
            else:
                hi = resolve_bound(getattr(v, "max_value", None), context)
                if hasattr(v, "_resolve_size"):
                    n = v._resolve_size(rng, context)
                    result[v.name] = [hi] * n
                elif hasattr(v, "alphabet"):
                    n = resolve_bound(v.length, context) if v.length else 20
                    result[v.name] = (v.alphabet[-1] if v.alphabet else "z") * n
                else:
                    result[v.name] = hi
        return result
    return maximum_strategy


def random_case():
    def random_case_strategy(spec, rng, context):
        result = _SyncDict(context)
        for v in spec._variables:
            if isinstance(v, Graph):
                result.update(_graph_case(v, context, rng, "random"))
            elif isinstance(v, Tree):
                result.update(_tree_case(v, context, rng, "random"))
            else:
                result[v.name] = v.resolve(rng, context)
        return result
    return random_case_strategy


def _stress_applicability(spec):
    for v in spec._variables:
        if isinstance(v, (Graph, Tree)):
            return None
        if hasattr(v, "size") and getattr(v, "size", None) is None:
            return None
        if hasattr(v, "alphabet") and getattr(v, "length", None) is None:
            return None
    return (
        "stress_case has nothing to stress: no Graph/Tree and no sequence with "
        "a free size to maximise, so it only repeats another strategy's "
        "value treatment"
    )


def _mixed_signs_applicability(spec):
    for v in spec._variables:
        rng = _declared_range(getattr(v, "min_value", None))
        if rng and rng[0] < 0:
            return None
    return "mixed_signs needs a negative minimum; every declared minimum is >= 0"


def _positive_only_applicability(spec):
    for v in spec._variables:
        rng = _declared_range(getattr(v, "max_value", None))
        if rng and rng[1] >= 1:
            return None
    return "positive_only needs a positive value in range; every maximum is < 1"


def _negative_only_applicability(spec):
    for v in spec._variables:
        rng = _declared_range(getattr(v, "min_value", None))
        if rng and rng[0] <= -1:
            return None
    return "negative_only needs a negative value in range; every minimum is >= 0"


def _all_zero_applicability(spec):
    for v in spec._variables:
        lo = _declared_range(getattr(v, "min_value", None))
        hi = _declared_range(getattr(v, "max_value", None))
        if lo is None or hi is None:
            continue
        if lo[0] <= 0 <= hi[1]:
            return None
    return "all_zero needs 0 inside some declared range"


def _duplicates_applicability(spec):
    for v in spec._variables:
        if not hasattr(v, "_resolve_size"):
            continue
        size = getattr(v, "size", None)
        rng = _declared_range(size if size is not None else getattr(v, "max_size", None))
        if rng is None or rng[1] >= 3:
            return None
    return "duplicates needs an array whose maximum size is at least 3"


def _single_node_applicability(spec):
    for v in spec._variables:
        if not isinstance(v, (Graph, Tree)):
            continue
        nlo, _ = _vertex_range(v, {})
        if nlo > 1:
            continue
        if isinstance(v, Graph):
            mlo, _ = _edge_range(v, {})
            if mlo > 0:
                continue
        return None
    return (
        "single_node needs a Graph/Tree whose num_vertices minimum is 1 "
        "(and num_edges minimum 0 for a Graph)"
    )


def stress_case():
    def stress_case_strategy(spec, rng, context):
        result = _SyncDict(context)
        for v in spec._variables:
            hi = resolve_bound(getattr(v, "max_value", None), context)
            lo = resolve_bound(getattr(v, "min_value", None), context)
            if isinstance(v, Graph):
                result.update(_graph_case(v, context, rng, "max"))
            elif isinstance(v, Tree):
                result.update(_tree_case(v, context, rng, "max"))
            elif hasattr(v, "_resolve_size"):
                if v.size is not None:
                    n = v._resolve_size(rng, context)
                elif getattr(v, "max_size", None) is not None:
                    n = resolve_bound(v.max_size, context)
                else:
                    n = 50
                result[v.name] = [rng.randint(lo, hi) for _ in range(n)]
            elif hasattr(v, "alphabet"):
                n = resolve_bound(v.length, context) if v.length else 50
                result[v.name] = "".join(rng.choice(v.alphabet) for _ in range(n))
            else:
                result[v.name] = hi
        return result
    return _applicable(stress_case_strategy, _stress_applicability)


def all_equal():
    def all_equal_strategy(spec, rng, context):
        result = _SyncDict(context)
        for v in spec._variables:
            lo = resolve_bound(getattr(v, "min_value", None), context)
            hi = resolve_bound(getattr(v, "max_value", None), context)
            val = rng.randint(lo, hi)
            result.update(_make_scalar(v, val, context, rng))
        return result
    return all_equal_strategy


def all_zero():
    def all_zero_strategy(spec, rng, context):
        result = _SyncDict(context)
        for v in spec._variables:
            lo = resolve_bound(getattr(v, "min_value", None), context)
            hi = resolve_bound(getattr(v, "max_value", None), context)
            if lo <= 0 <= hi:
                result.update(_make_scalar(v, 0, context, rng))
            else:
                result.update(_make_scalar(v, lo, context, rng))
        return result
    return _applicable(all_zero_strategy, _all_zero_applicability)


def increasing():
    def increasing_strategy(spec, rng, context):
        result = _SyncDict(context)
        for v in spec._variables:
            lo = resolve_bound(getattr(v, "min_value", None), context)
            hi = resolve_bound(getattr(v, "max_value", None), context)
            if isinstance(v, (Graph, Tree)):
                result.update(_make_scalar(v, lo, context, rng))
            elif hasattr(v, "_resolve_size"):
                n = v._resolve_size(rng, context)
                step = max(1, (hi - lo) // max(n, 1))
                result[v.name] = [lo + i * step for i in range(n)]
            else:
                result[v.name] = rng.randint(lo, hi)
        return result
    return _applicable(increasing_strategy, _needs_array("increasing"))


def decreasing():
    def decreasing_strategy(spec, rng, context):
        result = _SyncDict(context)
        for v in spec._variables:
            lo = resolve_bound(getattr(v, "min_value", None), context)
            hi = resolve_bound(getattr(v, "max_value", None), context)
            if isinstance(v, (Graph, Tree)):
                result.update(_make_scalar(v, hi, context, rng))
            elif hasattr(v, "_resolve_size"):
                n = v._resolve_size(rng, context)
                step = max(1, (hi - lo) // max(n, 1))
                result[v.name] = [hi - i * step for i in range(n)]
            else:
                result[v.name] = rng.randint(lo, hi)
        return result
    return _applicable(decreasing_strategy, _needs_array("decreasing"))


def mixed_signs():
    def mixed_signs_strategy(spec, rng, context):
        result = _SyncDict(context)
        for v in spec._variables:
            lo = resolve_bound(getattr(v, "min_value", None), context)
            hi = resolve_bound(getattr(v, "max_value", None), context)
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
    return _applicable(mixed_signs_strategy, _mixed_signs_applicability)


def positive_only():
    def positive_only_strategy(spec, rng, context):
        result = _SyncDict(context)
        for v in spec._variables:
            lo = max(1, resolve_bound(getattr(v, "min_value", None), context))
            hi = resolve_bound(getattr(v, "max_value", None), context)
            if isinstance(v, (Graph, Tree)):
                result.update(_make_scalar(v, lo, context, rng))
            elif hasattr(v, "_resolve_size"):
                n = v._resolve_size(rng, context)
                result[v.name] = [rng.randint(lo, hi) for _ in range(n)]
            else:
                result[v.name] = rng.randint(lo, hi)
        return result
    return _applicable(positive_only_strategy, _positive_only_applicability)


def negative_only():
    def negative_only_strategy(spec, rng, context):
        result = _SyncDict(context)
        for v in spec._variables:
            lo = resolve_bound(getattr(v, "min_value", None), context)
            hi = min(-1, resolve_bound(getattr(v, "max_value", None), context))
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
    return _applicable(negative_only_strategy, _negative_only_applicability)


def alternating():
    def alternating_strategy(spec, rng, context):
        result = _SyncDict(context)
        for v in spec._variables:
            lo = resolve_bound(getattr(v, "min_value", None), context)
            hi = resolve_bound(getattr(v, "max_value", None), context)
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
    return alternating_strategy


def boundary_values():
    def boundary_values_strategy(spec, rng, context):
        result = _SyncDict(context)
        for v in spec._variables:
            lo = resolve_bound(getattr(v, "min_value", None), context)
            hi = resolve_bound(getattr(v, "max_value", None), context)
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
    return boundary_values_strategy


def duplicates():
    def duplicates_strategy(spec, rng, context):
        result = _SyncDict(context)
        for v in spec._variables:
            lo = resolve_bound(getattr(v, "min_value", None), context)
            hi = resolve_bound(getattr(v, "max_value", None), context)
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
    return _applicable(duplicates_strategy, _duplicates_applicability)


def min_length():
    def min_length_strategy(spec, rng, context):
        result = _SyncDict(context)
        for v in spec._variables:
            if isinstance(v, (Graph, Tree)):
                result.update(_make_scalar(v, 0, context, rng))
            elif hasattr(v, "alphabet"):
                n = resolve_bound(v.min_length, context) if v.min_length else 1
                result[v.name] = "".join(rng.choice(v.alphabet) for _ in range(n))
            elif hasattr(v, "_resolve_size"):
                n = v._resolve_size(rng, context) if _has_explicit_size(v) else 1
                lo = resolve_bound(getattr(v, "min_value", None), context)
                hi = resolve_bound(getattr(v, "max_value", None), context)
                result[v.name] = [rng.randint(lo, hi) for _ in range(n)]
            else:
                result[v.name] = resolve_bound(getattr(v, "min_value", None), context)
        return result
    return _applicable(min_length_strategy, _needs_string("min_length"))


def max_length():
    def max_length_strategy(spec, rng, context):
        result = _SyncDict(context)
        for v in spec._variables:
            if isinstance(v, (Graph, Tree)):
                result.update(_make_scalar(v, 0, context, rng))
            elif hasattr(v, "alphabet"):
                n = resolve_bound(v.max_length, context) if v.max_length else 100
                result[v.name] = "".join(rng.choice(v.alphabet) for _ in range(n))
            elif hasattr(v, "_resolve_size"):
                n = v._resolve_size(rng, context) if _has_explicit_size(v) else 100
                lo = resolve_bound(getattr(v, "min_value", None), context)
                hi = resolve_bound(getattr(v, "max_value", None), context)
                result[v.name] = [rng.randint(lo, hi) for _ in range(n)]
            else:
                result[v.name] = resolve_bound(getattr(v, "max_value", None), context)
        return result
    return _applicable(max_length_strategy, _needs_string("max_length"))


def single_char():
    def single_char_strategy(spec, rng, context):
        result = _SyncDict(context)
        for v in spec._variables:
            if isinstance(v, (Graph, Tree)):
                result.update(_make_scalar(v, 0, context, rng))
            elif hasattr(v, "alphabet"):
                result[v.name] = rng.choice(v.alphabet)
            else:
                result[v.name] = resolve_bound(getattr(v, "min_value", None), context)
        return result
    return _applicable(single_char_strategy, _needs_string("single_char"))


def all_same_char():
    def all_same_char_strategy(spec, rng, context):
        result = _SyncDict(context)
        for v in spec._variables:
            if isinstance(v, (Graph, Tree)):
                result.update(_make_scalar(v, 0, context, rng))
            elif hasattr(v, "alphabet"):
                ch = rng.choice(v.alphabet)
                n = resolve_bound(v.length, context) if v.length else rng.randint(5, 20)
                result[v.name] = ch * n
            else:
                result[v.name] = resolve_bound(getattr(v, "min_value", None), context)
        return result
    return _applicable(all_same_char_strategy, _needs_string("all_same_char"))


def alternating_chars():
    def alternating_chars_strategy(spec, rng, context):
        result = _SyncDict(context)
        for v in spec._variables:
            if isinstance(v, (Graph, Tree)):
                result.update(_make_scalar(v, 0, context, rng))
            elif hasattr(v, "alphabet"):
                n = resolve_bound(v.length, context) if v.length else rng.randint(5, 20)
                a, b = rng.sample(v.alphabet, 2) if len(v.alphabet) >= 2 else (v.alphabet[0], v.alphabet[0])
                result[v.name] = "".join(a if i % 2 == 0 else b for i in range(n))
            else:
                result[v.name] = resolve_bound(getattr(v, "min_value", None), context)
        return result
    return _applicable(alternating_chars_strategy, _needs_string("alternating_chars"))


def palindrome():
    def palindrome_strategy(spec, rng, context):
        result = _SyncDict(context)
        for v in spec._variables:
            if isinstance(v, (Graph, Tree)):
                result.update(_make_scalar(v, 0, context, rng))
            elif hasattr(v, "alphabet"):
                n = resolve_bound(v.length, context) if v.length else rng.randint(5, 20)
                half = n // 2
                left = "".join(rng.choice(v.alphabet) for _ in range(half))
                mid = rng.choice(v.alphabet) if n % 2 == 1 else ""
                result[v.name] = left + mid + left[::-1]
            else:
                result[v.name] = resolve_bound(getattr(v, "min_value", None), context)
        return result
    return _applicable(palindrome_strategy, _needs_string("palindrome"))


def repeated_pattern():
    def repeated_pattern_strategy(spec, rng, context):
        result = _SyncDict(context)
        for v in spec._variables:
            if isinstance(v, (Graph, Tree)):
                result.update(_make_scalar(v, 0, context, rng))
            elif hasattr(v, "alphabet"):
                pat_len = rng.randint(2, 5)
                pattern = "".join(rng.choice(v.alphabet) for _ in range(pat_len))
                n = resolve_bound(v.length, context) if v.length else rng.randint(10, 30)
                result[v.name] = (pattern * (n // pat_len + 1))[:n]
            else:
                result[v.name] = resolve_bound(getattr(v, "min_value", None), context)
        return result
    return _applicable(repeated_pattern_strategy, _needs_string("repeated_pattern"))


def _structural_graph(v, context, rng, pairs_fn, n_mode="random", m_mode="max"):
    """Build a Graph from a structural edge shape, honouring declared limits.

    ``n_mode`` picks the vertex count (min/max/random) and ``m_mode`` how many
    of the structural edges are kept, so a chain or star never exceeds the
    declared ``num_edges`` and never drops below its minimum.
    """
    nlo, nhi = _vertex_range(v, context)
    mlo, mhi = _edge_range(v, context)
    if nlo > nhi:
        raise ValueError(f"num_vertices range is empty: [{nlo}, {nhi}]")
    if n_mode == "max":
        n = nhi
    elif n_mode == "min":
        n = _fit_n(mlo, nlo, nhi, v.directed)
    else:
        n = _fit_n(mlo, rng.randint(nlo, nhi), nhi, v.directed)

    cap = _max_edges(n, v.directed)
    upper = cap if mhi is None else min(mhi, cap)
    if upper < mlo:
        raise ValueError(
            f"{n} vertices fit {cap} edges but num_edges minimum is {mlo}"
        )

    structural = list(pairs_fn(n))
    if len(structural) < mlo:
        raise ValueError(
            f"this shape yields {len(structural)} edges on {n} vertices but "
            f"num_edges minimum is {mlo}"
        )
    limit = min(upper, len(structural))
    if m_mode == "min":
        m = mlo
    elif m_mode == "max":
        m = limit
    else:
        m = rng.randint(mlo, limit)

    edges = _weighted(v, structural[:m], rng)
    return {v.name: edges, f"{v.name}_n": n, f"{v.name}_m": len(edges)}


def _structural_tree(v, context, rng, pairs_fn, n_mode="random"):
    nlo, nhi = _vertex_range(v, context)
    if nlo > nhi:
        raise ValueError(f"num_vertices range is empty: [{nlo}, {nhi}]")
    if n_mode == "max":
        n = nhi
    elif n_mode == "min":
        n = nlo
    else:
        n = rng.randint(nlo, nhi)
    if n < 1:
        raise ValueError(f"num_vertices minimum is {nlo}; cannot build a tree")
    return {v.name: list(pairs_fn(n)), f"{v.name}_n": n}


def _path_edges(n):
    return [(i, i + 1) for i in range(1, n)]


def _star_edges(n):
    return [(1, i) for i in range(2, n + 1)]


def _balanced_edges(n):
    return [(i // 2, i) for i in range(2, n + 1)]


def _two_component_edges(n):
    half = max(1, n // 2)
    edges = [(i, i + 1) for i in range(1, half)]
    edges += [(half + i, half + i + 1) for i in range(1, n - half)]
    return edges


def chain():
    def chain_strategy(spec, rng, context):
        result = _SyncDict(context)
        for v in spec._variables:
            if isinstance(v, Graph):
                result.update(
                    _structural_graph(v, context, rng, _path_edges, m_mode="max")
                )
            elif isinstance(v, Tree):
                result.update(_structural_tree(v, context, rng, _path_edges))
            else:
                result.update(_make_scalar(v, resolve_bound(getattr(v, "min_value", None), context), context, rng))
        return result
    return _applicable(chain_strategy, _needs_graph_or_tree("chain"))


def star():
    def star_strategy(spec, rng, context):
        result = _SyncDict(context)
        for v in spec._variables:
            if isinstance(v, Graph):
                result.update(
                    _structural_graph(v, context, rng, _star_edges, m_mode="max")
                )
            elif isinstance(v, Tree):
                result.update(_structural_tree(v, context, rng, _star_edges))
            else:
                result.update(_make_scalar(v, resolve_bound(getattr(v, "min_value", None), context), context, rng))
        return result
    return _applicable(star_strategy, _needs_graph_or_tree("star"))


def disconnected():
    def disconnected_strategy(spec, rng, context):
        result = _SyncDict(context)
        for v in spec._variables:
            if isinstance(v, Graph):
                result.update(
                    _structural_graph(
                        v, context, rng, _two_component_edges, m_mode="max"
                    )
                )
            else:
                # A Tree must stay connected, so there is no disconnected shape.
                result.update(_make_scalar(v, resolve_bound(getattr(v, "min_value", None), context), context, rng))
        return result
    return _applicable(disconnected_strategy, _needs_graph("disconnected"))


def dense():
    def dense_strategy(spec, rng, context):
        result = _SyncDict(context)
        for v in spec._variables:
            if isinstance(v, Graph):
                result.update(_graph_case(v, context, rng, "max"))
            elif isinstance(v, Tree):
                result.update(_tree_case(v, context, rng, "max"))
            else:
                result.update(_make_scalar(v, resolve_bound(getattr(v, "min_value", None), context), context, rng))
        return result
    return _applicable(dense_strategy, _needs_graph_or_tree("dense"))


def single_node():
    def single_node_strategy(spec, rng, context):
        result = _SyncDict(context)
        for v in spec._variables:
            if isinstance(v, (Tree, Graph)):
                nlo, _ = _vertex_range(v, context)
                if nlo > 1:
                    raise ValueError(
                        f"{v.name}: num_vertices minimum is {nlo}, so a single "
                        f"node is not a valid test case"
                    )
                if isinstance(v, Graph):
                    mlo, _ = _edge_range(v, context)
                    if mlo > 0:
                        raise ValueError(
                            f"{v.name}: num_edges minimum is {mlo}, so a single "
                            f"node is not a valid test case"
                        )
                    result[v.name] = []
                    result[f"{v.name}_n"] = 1
                    result[f"{v.name}_m"] = 0
                else:
                    result[v.name] = []
                    result[f"{v.name}_n"] = 1
            else:
                result.update(_make_scalar(v, resolve_bound(getattr(v, "min_value", None), context), context, rng))
        return result
    return _applicable(single_node_strategy, _single_node_applicability)


def balanced():
    def balanced_strategy(spec, rng, context):
        result = _SyncDict(context)
        for v in spec._variables:
            if isinstance(v, Tree):
                result.update(_structural_tree(v, context, rng, _balanced_edges))
            else:
                result.update(_make_scalar(v, resolve_bound(getattr(v, "min_value", None), context), context, rng))
        return result
    return _applicable(balanced_strategy, _needs_tree("balanced"))


def skewed():
    def skewed_strategy(spec, rng, context):
        result = _SyncDict(context)
        for v in spec._variables:
            if isinstance(v, Tree):
                result.update(_structural_tree(v, context, rng, _path_edges))
            else:
                result.update(_make_scalar(v, resolve_bound(getattr(v, "min_value", None), context), context, rng))
        return result
    return _applicable(skewed_strategy, _needs_tree("skewed"))

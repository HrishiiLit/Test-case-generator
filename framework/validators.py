from framework.generators import _Var, resolve_bound, resolve_range
from framework.graphs import Graph, Tree


def _check_var(v, val, context, errors, prefix=""):
    name = f"{prefix}{v.name}"
    if val is None:
        errors.append(f"Missing value for '{name}'")
        return

    lo = resolve_bound(v.min_value, context) if getattr(v, "min_value", None) is not None else None
    hi = resolve_bound(v.max_value, context) if getattr(v, "max_value", None) is not None else None

    if isinstance(v, Graph):
        edges = val
        nlo, nhi = resolve_range(getattr(v, "num_vertices", None), context, (1, 1))
        n = context.get(f"{v.name}_n", resolve_bound(v.num_vertices, context))
        if not nlo <= n <= nhi:
            errors.append(
                f"{prefix}{v.name}_n={n} outside declared "
                f"num_vertices [{nlo}, {nhi}]"
            )
        declared_m = context.get(f"{v.name}_m", len(edges))
        if declared_m != len(edges):
            errors.append(
                f"{prefix}{v.name}: header declares {declared_m} edges but "
                f"{len(edges)} were provided"
            )
        if v.num_edges is not None:
            mlo, mhi = resolve_range(v.num_edges, context, (0, None))
            if declared_m < mlo:
                errors.append(
                    f"{prefix}{v.name}_m={declared_m} below num_edges "
                    f"minimum {mlo}"
                )
            if mhi is not None and declared_m > mhi:
                errors.append(
                    f"{prefix}{v.name}_m={declared_m} above num_edges "
                    f"declared {mhi}"
                )
        seen = set()
        for idx, edge in enumerate(edges):
            a, b = edge[0], edge[1]
            if a < 1 or a > n:
                errors.append(f"{prefix}Graph edge {idx}: vertex {a} out of range [1, {n}]")
            if b < 1 or b > n:
                errors.append(f"{prefix}Graph edge {idx}: vertex {b} out of range [1, {n}]")
            if not v.allow_self_loops and a == b:
                errors.append(f"{prefix}Graph edge {idx}: self-loop at {a}")
            if not v.allow_multi_edges:
                key = (a, b) if v.directed else (min(a, b), max(a, b))
                if key in seen:
                    errors.append(f"{prefix}Graph edge {idx}: duplicate edge {a} {b}")
                seen.add(key)
    elif isinstance(v, Tree):
        edges = val
        nlo, nhi = resolve_range(getattr(v, "num_vertices", None), context, (1, 1))
        n = context.get(f"{v.name}_n", resolve_bound(v.num_vertices, context))
        if not nlo <= n <= nhi:
            errors.append(
                f"{prefix}{v.name}_n={n} outside declared "
                f"num_vertices [{nlo}, {nhi}]"
            )
        if len(edges) != max(n - 1, 0) and n > 1:
            errors.append(f"{prefix}Tree: expected {n - 1} edges, got {len(edges)}")
        for idx, edge in enumerate(edges):
            a, b = edge[0], edge[1]
            if a < 1 or a > n:
                errors.append(f"{prefix}Tree edge {idx}: vertex {a} out of range [1, {n}]")
            if b < 1 or b > n:
                errors.append(f"{prefix}Tree edge {idx}: vertex {b} out of range [1, {n}]")
    elif getattr(v, "rows", None) is not None or (isinstance(val, list) and val and isinstance(val[0], list)):
        if getattr(v, "rows", None) is not None:
            expected_r = resolve_bound(v.rows, context)
            if len(val) != expected_r:
                errors.append(f"{name}: declared {expected_r} rows but got {len(val)}")
        expected_c = resolve_bound(v.cols, context) if getattr(v, "cols", None) is not None else None
        for r_idx, row in enumerate(val):
            if not isinstance(row, list):
                errors.append(f"{name}[{r_idx}]: expected list, got {type(row).__name__}")
                continue
            if expected_c is not None and len(row) != expected_c:
                errors.append(f"{name}[{r_idx}]: declared {expected_c} cols but got {len(row)}")
            for c_idx, cell in enumerate(row):
                if isinstance(cell, (int, float)):
                    if lo is not None and cell < lo:
                        errors.append(f"{name}[{r_idx}][{c_idx}]={cell} < min {lo}")
                    if hi is not None and cell > hi:
                        errors.append(f"{name}[{r_idx}][{c_idx}]={cell} > max {hi}")
    elif hasattr(v, "_resolve_size") and getattr(v, "alphabet", None) is None and getattr(v, "rows", None) is None and type(v).__name__ == "Permutation":
        if not isinstance(val, list):
            errors.append(f"{name}: expected list, got {type(val).__name__}")
            return
        expected = resolve_bound(v.size, context) if getattr(v, "size", None) is not None else len(val)
        if len(val) != expected:
            errors.append(f"{name}: declared size {expected} but got {len(val)} elements")
        lo_p = lo if lo is not None else 1
        expected_set = set(range(int(lo_p), int(lo_p + len(val))))
        if set(val) != expected_set:
            errors.append(f"{name}: elements do not match valid permutation of {len(val)} values starting at {lo_p}")
    elif isinstance(val, list):
        if getattr(v, "size", None) is not None:
            expected = resolve_bound(v.size, context)
            if len(val) != expected:
                errors.append(f"{name}: declared size {expected} but got {len(val)} elements")
        if getattr(v, "unique", False):
            if len(set(val)) != len(val):
                errors.append(f"{name}: duplicate elements found in unique array")
        for idx, item in enumerate(val):
            if isinstance(item, (int, float)):
                if lo is not None and item < lo:
                    errors.append(f"{name}[{idx}]={item} < min {lo}")
                if hi is not None and item > hi:
                    errors.append(f"{name}[{idx}]={item} > max {hi}")
    elif isinstance(val, str):
        if hasattr(v, "alphabet"):
            for ch in val:
                if ch not in v.alphabet:
                    errors.append(f"{name}: char '{ch}' not in alphabet")
        if getattr(v, "length", None) is not None:
            expected_len = resolve_bound(v.length, context)
            if len(val) != expected_len:
                errors.append(f"{name}: declared length {expected_len} but got {len(val)}")
        if hasattr(v, "min_length") and v.min_length is not None:
            min_len = resolve_bound(v.min_length, context)
            if len(val) < min_len:
                errors.append(f"{name}: length {len(val)} < min {min_len}")
        if hasattr(v, "max_length") and v.max_length is not None:
            max_len = resolve_bound(v.max_length, context)
            if len(val) > max_len:
                errors.append(f"{name}: length {len(val)} > max {max_len}")
    elif isinstance(val, (int, float)):
        if lo is not None and val < lo:
            errors.append(f"{name}={val} < min {lo}")
        if hi is not None and val > hi:
            errors.append(f"{name}={val} > max {hi}")


def validate_testcase(spec, values):
    from framework.generators import Blocks, flatten_vars

    errors = []
    group = None
    for v in spec._input_order:
        if isinstance(v, Blocks):
            group = v
            break

    blocks = values.get("__blocks__")

    if group is not None:
        inner_vars = flatten_vars(group)
        t_var = spec._count_var()
        if blocks is None:
            errors.append("Multi-test problem: missing '__blocks__' list")
        else:
            if t_var is None:
                errors.append(
                    "Multi-test problem: no count variable declared before Blocks(...)"
                )
            else:
                t_val = values.get(t_var.name)
                if t_val != len(blocks):
                    errors.append(
                        f"{t_var.name}={t_val} does not match number of "
                        f"blocks ({len(blocks)})"
                    )
                _check_var(t_var, t_val, values, errors)

        for bi, block in enumerate(blocks or []):
            scope = dict(values)
            scope.update(block)
            for inner in inner_vars:
                _check_var(inner, block.get(inner.name), scope, errors,
                           prefix=f"block[{bi}].")
        return errors

    for v in spec._variables:
        _check_var(v, values.get(v.name), values, errors)

    return errors

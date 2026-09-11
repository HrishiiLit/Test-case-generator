from framework.generators import _Var, resolve_bound
from framework.graphs import Graph, Tree


def _check_var(v, val, context, errors, prefix=""):
    name = f"{prefix}{v.name}"
    if val is None:
        errors.append(f"Missing value for '{name}'")
        return

    lo = resolve_bound(getattr(v, "min_value", None), context)
    hi = resolve_bound(getattr(v, "max_value", None), context)

    if isinstance(v, Graph):
        edges = val
        n = context.get(f"{v.name}_n", resolve_bound(v.num_vertices, context))
        for idx, edge in enumerate(edges):
            a, b = edge[0], edge[1]
            if a < 1 or a > n:
                errors.append(f"{prefix}Graph edge {idx}: vertex {a} out of range [1, {n}]")
            if b < 1 or b > n:
                errors.append(f"{prefix}Graph edge {idx}: vertex {b} out of range [1, {n}]")
            if not v.allow_self_loops and a == b:
                errors.append(f"{prefix}Graph edge {idx}: self-loop at {a}")
    elif isinstance(v, Tree):
        edges = val
        n = context.get(f"{v.name}_n", resolve_bound(v.num_vertices, context))
        if len(edges) != n - 1 and n > 1:
            errors.append(f"{prefix}Tree: expected {n - 1} edges, got {len(edges)}")
        for idx, edge in enumerate(edges):
            a, b = edge[0], edge[1]
            if a < 1 or a > n:
                errors.append(f"{prefix}Tree edge {idx}: vertex {a} out of range [1, {n}]")
            if b < 1 or b > n:
                errors.append(f"{prefix}Tree edge {idx}: vertex {b} out of range [1, {n}]")
    elif isinstance(val, list):
        if hasattr(v, "_resolve_size"):
            if getattr(v, "size", None) is not None:
                expected = resolve_bound(v.size, context)
                if len(val) != expected:
                    errors.append(
                        f"{name}: declared size {expected} but got {len(val)} elements"
                    )
        for idx, item in enumerate(val):
            if isinstance(item, (int, float)):
                if item < lo:
                    errors.append(f"{name}[{idx}]={item} < min {lo}")
                if item > hi:
                    errors.append(f"{name}[{idx}]={item} > max {hi}")
    elif isinstance(val, str):
        if hasattr(v, "alphabet"):
            for ch in val:
                if ch not in v.alphabet:
                    errors.append(f"{name}: char '{ch}' not in alphabet")
        if hasattr(v, "min_length") and v.min_length is not None:
            min_len = resolve_bound(v.min_length, context)
            if len(val) < min_len:
                errors.append(f"{name}: length {len(val)} < min {min_len}")
        if hasattr(v, "max_length") and v.max_length is not None:
            max_len = resolve_bound(v.max_length, context)
            if len(val) > max_len:
                errors.append(f"{name}: length {len(val)} > max {max_len}")
    elif isinstance(val, (int, float)):
        if val < lo:
            errors.append(f"{name}={val} < min {lo}")
        if val > hi:
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
        t_var = next((x for x in spec._variables if x.name == "T"), None)
        if blocks is None:
            errors.append("Multi-test problem: missing '__blocks__' list")
        else:
            if t_var is not None:
                t_val = values.get("T")
                if t_val != len(blocks):
                    errors.append(
                        f"T={t_val} does not match number of blocks ({len(blocks)})"
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

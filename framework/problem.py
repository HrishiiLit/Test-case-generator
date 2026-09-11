import random as _random
from framework.generators import (
    _Var, resolve_bound, Line, Blocks, flatten_vars,
    Array, Matrix, String,
)
from framework.graphs import Graph, Tree


BLOCK_BUDGET = 200000


class Problem:
    def __init__(self, name="Problem", testcases=10):
        self.name = name
        self.testcases = testcases
        self._variables = []
        self._input_order = []
        self._strategies = []
        self._custom_cases = []

    def input(self, *vars):
        for v in vars:
            if isinstance(v, (Line, Blocks)):
                for inner in flatten_vars(v):
                    self._variables.append(inner)
                self._input_order.append(v)
            else:
                self._variables.append(v)
                self._input_order.append(v)
        return self

    def _blocks_group(self):
        for v in self._input_order:
            if isinstance(v, Blocks):
                return v
        return None

    def add_testcases(self, *strategies):
        for s in strategies:
            self._strategies.append(s)
        return self

    def add_custom_case(self, fn):
        self._custom_cases.append(fn)
        return self

    @staticmethod
    def _case_signature(vals):
        """Convert a test case dict to a hashable form for deduplication."""
        def make_hashable(v):
            if isinstance(v, list):
                return tuple(make_hashable(x) for x in v)
            if isinstance(v, dict):
                return tuple(sorted((k2, make_hashable(v2)) for k2, v2 in v.items()))
            return v
        return tuple(sorted((k, make_hashable(v)) for k, v in vals.items() if k != "__blocks__"))

    def generate_testcases(self, rng, max_retries=10, external_seen=None):
        all_cases = []
        seen = set(external_seen) if external_seen else set()

        def _add_case(vals):
            sig = self._case_signature(vals)
            if sig in seen:
                return False
            seen.add(sig)
            all_cases.append(vals)
            return True

        def _retry_generate(gen_fn, label):
            for attempt in range(max_retries):
                try:
                    return gen_fn()
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise RuntimeError(f"{label} failed after {max_retries} retries: {e}")

        for strat in self._strategies:
            def _gen_strat():
                ctx = {}
                vals = strat(self, rng, ctx)
                return self._expand_blocks(vals)
            result = _retry_generate(_gen_strat, "Strategy")
            if result is not None:
                _add_case(result)

        for custom_fn in self._custom_cases:
            def _gen_custom():
                vals = custom_fn(rng)
                if not isinstance(vals, dict):
                    raise ValueError("Custom case must return a dict")
                return vals
            result = _retry_generate(_gen_custom, "Custom case")
            if result is not None:
                _add_case(result)

        remaining = self.testcases - len(all_cases)
        if remaining > 0:
            strat = self._default_random_strategy()
            for _ in range(remaining):
                def _gen_random():
                    ctx = {}
                    vals = strat(self, rng, ctx)
                    return self._expand_blocks(vals)
                result = _retry_generate(_gen_random, "Random generation")
                if result is not None:
                    _add_case(result)

        return all_cases[:self.testcases]

    def generate_sample_testcases(self, rng, count=3, max_lines=15, external_seen=None):
        """Generate 2-3 sample testcases with 3-15 lines for human verification."""
        samples = []
        seen = set(external_seen) if external_seen else set()

        def _count_lines_from_render(text):
            return text.count("\n")

        def _add_sample(vals):
            sig = self._case_signature(vals)
            if sig in seen:
                return False
            seen.add(sig)
            samples.append(vals)
            return True

        strategies = [
            self._sample_minimum,
            self._sample_small_readable,
            self._sample_boundary,
        ]

        for strat_fn in strategies:
            for attempt in range(10):
                try:
                    vals = strat_fn(rng)
                    rendered = self.render_testcase(vals)
                    line_count = _count_lines_from_render(rendered)
                    if line_count >= 2 and line_count <= max_lines:
                        _add_sample(vals)
                        break
                except Exception:
                    continue

        max_attempts = count * 20
        for _ in range(max_attempts):
            if len(samples) >= count:
                break
            try:
                vals = self._sample_random_within_lines(max_lines, rng)
                rendered = self.render_testcase(vals)
                line_count = _count_lines_from_render(rendered)
                if line_count >= 2 and line_count <= max_lines:
                    _add_sample(vals)
            except Exception:
                break

        return samples[:count]

    def _sample_minimum(self, rng):
        result = {}
        ctx = {}
        for v in self._variables:
            lo = self._resolve_bound_val(v.min_value, ctx)
            hi = self._resolve_bound_val(v.max_value, ctx)
            if isinstance(v, Graph):
                n = self._resolve_bound_val(v.num_vertices, ctx)
                n = min(n, 4)
                result[v.name] = [(1, 2)] if n >= 2 else []
                result[f"{v.name}_n"] = n
                result[f"{v.name}_m"] = len(result[v.name])
            elif isinstance(v, Tree):
                n = self._resolve_bound_val(v.num_vertices, ctx)
                n = min(n, 4)
                result[v.name] = [(1, i) for i in range(2, n + 1)]
                result[f"{v.name}_n"] = n
            elif isinstance(v, Array):
                n = v._resolve_size(rng, ctx)
                n = min(n, 5)
                result[v.name] = [lo] * n
            elif isinstance(v, Matrix):
                r = min(self._resolve_bound_val(v.rows, ctx), 3)
                c = min(self._resolve_bound_val(v.cols, ctx), 3)
                result[v.name] = [[lo] * c for _ in range(r)]
            elif isinstance(v, String):
                n = self._resolve_bound_val(v.length, ctx) if v.length else 3
                n = min(n, 4)
                result[v.name] = (v.alphabet[0] if v.alphabet else "a") * n
            elif v.name == "T":
                result[v.name] = 1
            else:
                result[v.name] = lo
            ctx.update(result)
        return self._expand_blocks(result)

    def _sample_small_readable(self, rng):
        result = {}
        ctx = {}
        for v in self._variables:
            lo = self._resolve_bound_val(v.min_value, ctx)
            hi = self._resolve_bound_val(v.max_value, ctx)
            if isinstance(v, Graph):
                n = self._resolve_bound_val(v.num_vertices, ctx)
                n = min(n, 5)
                m = min(n - 1, 4)
                edges = [(i, i + 1) for i in range(1, m + 1)]
                result[v.name] = edges
                result[f"{v.name}_n"] = n
                result[f"{v.name}_m"] = len(edges)
            elif isinstance(v, Tree):
                n = self._resolve_bound_val(v.num_vertices, ctx)
                n = min(n, 5)
                edges = [(i, i + 1) for i in range(2, n + 1)]
                result[v.name] = edges
                result[f"{v.name}_n"] = n
            elif isinstance(v, Array):
                n = v._resolve_size(rng, ctx)
                n = min(n, 6)
                unique_vals = list(range(1, min(n + 1, hi - lo + 2)))
                while len(unique_vals) < n:
                    unique_vals.append(rng.randint(max(lo, 1), min(hi, 100)))
                result[v.name] = unique_vals[:n]
                if v.size is not None and hasattr(v.size, 'name'):
                    result[v.size.name] = n
            elif isinstance(v, Matrix):
                r = min(self._resolve_bound_val(v.rows, ctx), 4)
                c = min(self._resolve_bound_val(v.cols, ctx), 4)
                result[v.name] = [[rng.randint(max(lo, 1), min(hi, 50)) for _ in range(c)] for _ in range(r)]
            elif isinstance(v, String):
                n = self._resolve_bound_val(v.length, ctx) if v.length else rng.randint(3, 5)
                n = min(n, 6)
                result[v.name] = "".join(rng.choice(v.alphabet[:5]) for _ in range(n))
            elif v.name == "T":
                result[v.name] = 1
            else:
                if hi > 1000:
                    result[v.name] = rng.randint(max(lo, 1), min(hi, 100))
                else:
                    result[v.name] = rng.randint(max(lo, 1), min(hi, 50))
            ctx.update(result)
        return self._expand_blocks(result)

    def _sample_boundary(self, rng):
        result = {}
        ctx = {}
        for v in self._variables:
            lo = self._resolve_bound_val(v.min_value, ctx)
            hi = self._resolve_bound_val(v.max_value, ctx)
            if isinstance(v, Graph):
                n = self._resolve_bound_val(v.num_vertices, ctx)
                n = min(n, 4)
                edges = [(1, i) for i in range(2, n + 1)]
                result[v.name] = edges
                result[f"{v.name}_n"] = n
                result[f"{v.name}_m"] = len(edges)
            elif isinstance(v, Tree):
                n = self._resolve_bound_val(v.num_vertices, ctx)
                n = min(n, 4)
                edges = [(1, i) for i in range(2, n + 1)]
                result[v.name] = edges
                result[f"{v.name}_n"] = n
            elif isinstance(v, Array):
                n = v._resolve_size(rng, ctx)
                n = min(n, 5)
                vals = [lo, hi, lo, hi]
                while len(vals) < n:
                    vals.append(rng.randint(lo, hi))
                result[v.name] = vals[:n]
                if v.size is not None and hasattr(v.size, 'name'):
                    result[v.size.name] = n
            elif isinstance(v, Matrix):
                r = min(self._resolve_bound_val(v.rows, ctx), 3)
                c = min(self._resolve_bound_val(v.cols, ctx), 3)
                result[v.name] = [[lo if (i + j) % 2 == 0 else hi for j in range(c)] for i in range(r)]
            elif isinstance(v, String):
                n = self._resolve_bound_val(v.length, ctx) if v.length else 4
                n = min(n, 5)
                result[v.name] = v.alphabet[0] * (n // 2) + v.alphabet[-1] * (n - n // 2) if v.alphabet else "a" * n
            elif v.name == "T":
                result[v.name] = 1
            else:
                result[v.name] = rng.choice([lo, hi])
            ctx.update(result)
        return self._expand_blocks(result)

    def _sample_random_within_lines(self, max_lines, rng):
        result = {}
        ctx = {}
        for v in self._variables:
            lo = self._resolve_bound_val(v.min_value, ctx)
            hi = self._resolve_bound_val(v.max_value, ctx)
            if isinstance(v, Graph):
                n = self._resolve_bound_val(v.num_vertices, ctx)
                n = min(n, min(5, max_lines - 1))
                m = min(n - 1, 4)
                edges = [(i, i + 1) for i in range(1, m + 1)]
                result[v.name] = edges
                result[f"{v.name}_n"] = n
                result[f"{v.name}_m"] = len(edges)
            elif isinstance(v, Tree):
                n = self._resolve_bound_val(v.num_vertices, ctx)
                n = min(n, min(5, max_lines))
                edges = [(i, i + 1) for i in range(2, n + 1)]
                result[v.name] = edges
                result[f"{v.name}_n"] = n
            elif isinstance(v, Array):
                n = v._resolve_size(rng, ctx)
                n = min(n, 8)
                result[v.name] = [rng.randint(max(lo, 1), min(hi, 50)) for _ in range(n)]
                if v.size is not None and hasattr(v.size, 'name'):
                    result[v.size.name] = n
            elif isinstance(v, Matrix):
                r = min(self._resolve_bound_val(v.rows, ctx), 4)
                c = min(self._resolve_bound_val(v.cols, ctx), 4)
                result[v.name] = [[rng.randint(max(lo, 1), min(hi, 50)) for _ in range(c)] for _ in range(r)]
            elif isinstance(v, String):
                n = self._resolve_bound_val(v.length, ctx) if v.length else rng.randint(3, 5)
                n = min(n, 6)
                result[v.name] = "".join(rng.choice(v.alphabet) for _ in range(n))
            elif v.name == "T":
                result[v.name] = 1
            else:
                if hi > 1000:
                    result[v.name] = rng.randint(max(lo, 1), min(hi, 100))
                else:
                    result[v.name] = rng.randint(lo, hi)
            ctx.update(result)
        return self._expand_blocks(result)

    def _resolve_bound_val(self, bound, context):
        return resolve_bound(bound, context)

    def _default_random_strategy(self):
        def strategy(spec, rng, ctx):
            out = {}
            for v in spec._variables:
                out[v.name] = v.resolve(rng, ctx)
                ctx.update(out)
            return out
        return strategy

    def _expand_blocks(self, values):
        """Replicate a strategy's single generated block into a multi-test input.

        Strategies produce one set of per-block values; when the problem has a
        Blocks group, replicate it T times while capping T so the total number
        of rendered elements stays within BLOCK_BUDGET. Custom cases that need
        full control supply "__blocks__" themselves and skip this.
        """
        group = self._blocks_group()
        if group is None or "__blocks__" in values:
            return values

        t = values.get("T")
        if not isinstance(t, int) or t < 1:
            t = 1

        cost = 0
        for inner in flatten_vars(group):
            v = values.get(inner.name)
            if isinstance(v, list):
                cost += len(v)
            elif isinstance(v, str):
                cost += len(v)
            else:
                cost += 1
        cap = max(1, BLOCK_BUDGET // max(cost, 1))
        t = min(t, cap)

        blocks = []
        for _ in range(t):
            b = {}
            for inner in flatten_vars(group):
                b[inner.name] = values.get(inner.name)
                for suffix in ("_n", "_m"):
                    aux = values.get(f"{inner.name}{suffix}")
                    if aux is not None:
                        b[f"{inner.name}{suffix}"] = aux
            blocks.append(b)

        out = dict(values)
        out["T"] = t
        out["__blocks__"] = blocks
        return out

    def _render_item(self, v, values):
        lines = []
        val = values.get(v.name) if not isinstance(v, Line) else None

        if isinstance(v, Line):
            lines.append(v.render(values))
        elif isinstance(v, Graph):
            edges = val
            n = values.get(f"{v.name}_n", resolve_bound(v.num_vertices, values))
            m = values.get(f"{v.name}_m", len(edges))
            lines.append(v.render_header(n, m))
            for edge in edges:
                lines.append(v.render_edge(edge))
        elif isinstance(v, Tree):
            edges = val
            n = values.get(f"{v.name}_n", resolve_bound(v.num_vertices, values))
            lines.append(v.render_header(n))
            for edge in edges:
                lines.append(v.render_edge(edge))
        else:
            if val is None:
                raise ValueError(f"Missing value for variable '{v.name}'")
            lines.append(v.render(val))

        return lines

    def render_testcase(self, values):
        lines = []
        for v in self._input_order:
            if isinstance(v, Blocks):
                blocks = values.get("__blocks__") or [{}]
                for b in blocks:
                    scope = dict(values)
                    scope.update(b)
                    for inner in v.vars:
                        lines.extend(self._render_item(inner, scope))
            else:
                lines.extend(self._render_item(v, values))

        return "\n".join(lines) + "\n"

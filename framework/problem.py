import random as _random
from framework.generators import _Var
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
        from framework.generators import Line, Blocks, flatten_vars
        for v in vars:
            if isinstance(v, (Line, Blocks)):
                # Register each inner variable for generation, but put the group in render order
                for inner in flatten_vars(v):
                    self._variables.append(inner)
                self._input_order.append(v)
            else:
                self._variables.append(v)
                self._input_order.append(v)
        return self

    def _blocks_group(self):
        from framework.generators import Blocks
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

    def _resolve_context(self, values):
        return values

    def generate_testcases(self, rng, max_retries=10):
        all_cases = []

        for strat in self._strategies:
            for attempt in range(max_retries):
                try:
                    ctx = {}
                    vals = strat(self, rng, ctx)
                    all_cases.append(self._expand_blocks(vals))
                    break
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise RuntimeError(f"Strategy failed after {max_retries} retries: {e}")

        for custom_fn in self._custom_cases:
            for attempt in range(max_retries):
                try:
                    vals = custom_fn(rng)
                    if isinstance(vals, dict):
                        all_cases.append(vals)
                    else:
                        raise ValueError("Custom case must return a dict")
                    break
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise RuntimeError(f"Custom case failed after {max_retries} retries: {e}")

        remaining = self.testcases - len(all_cases)
        if remaining > 0:
            strat = self._default_random_strategy()
            for _ in range(remaining):
                for attempt in range(max_retries):
                    try:
                        ctx = {}
                        vals = strat(self, rng, ctx)
                        all_cases.append(vals)
                        break
                    except Exception as e:
                        if attempt == max_retries - 1:
                            raise RuntimeError(f"Random generation failed: {e}")

        return all_cases[:self.testcases]

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
        from framework.generators import flatten_vars
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
        from framework.generators import Line
        lines = []
        val = values.get(v.name) if not isinstance(v, Line) else None

        if isinstance(v, Line):
            lines.append(v.render(values))
        elif isinstance(v, Graph):
            edges = val
            n = values.get(f"{v.name}_n", _resolve_bound(v.num_vertices, values))
            m = values.get(f"{v.name}_m", len(edges))
            lines.append(v.render_header(n, m))
            for edge in edges:
                lines.append(v.render_edge(edge))
        elif isinstance(v, Tree):
            edges = val
            n = values.get(f"{v.name}_n", _resolve_bound(v.num_vertices, values))
            lines.append(v.render_header(n))
            for edge in edges:
                lines.append(v.render_edge(edge))
        else:
            if val is None:
                raise ValueError(f"Missing value for variable '{v.name}'")
            lines.append(v.render(val))

        return lines

    def render_testcase(self, values):
        from framework.generators import Blocks
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

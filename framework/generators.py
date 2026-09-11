import random as _random


def resolve_bound(bound, context):
    """Resolve a bound value that may be a literal, callable, or _Var reference."""
    if bound is None:
        return 0
    if callable(bound):
        return bound(context)
    if hasattr(bound, "resolve"):
        if bound.name in context:
            return int(context[bound.name])
        return bound.resolve(_random.Random(0), context)
    return int(bound)


class Line:
    """Groups multiple variables to be rendered space-separated on a single line."""

    def __init__(self, *vars):
        self.vars = vars
        self.name = "__line__"

    def render(self, values):
        parts = []
        for v in self.vars:
            val = values.get(v.name)
            parts.append(v.render(val))
        return " ".join(parts)


class Blocks:
    """Marks variables that repeat once per test-case block in multi-test inputs.

    The first declared variable of the problem is expected to be the
    test-case count T. A custom case supplies per-block values via the
    special "__blocks__" key (a list of dicts); strategies without it get
    their single generated block replicated with T lowered so aggregate
    size stays within budget.
    """

    def __init__(self, *vars):
        self.vars = vars
        self.name = "__blocks__"


def flatten_vars(group):
    """Return the individual variables inside a Line/Blocks group."""
    out = []
    for item in group.vars:
        if isinstance(item, Line):
            out.extend(item.vars)
        else:
            out.append(item)
    return out


class _Var:
    def __init__(self, name, min_value=None, max_value=None):
        self.name = name
        self.min_value = min_value
        self.max_value = max_value
        self._fixed = None
        self._resolve_fn = None

    def resolve(self, rng, context):
        if self._fixed is not None:
            return self._fixed
        if self._resolve_fn is not None:
            return self._resolve_fn(rng, context)
        return self._generate(rng, context)

    def _generate(self, rng, context):
        lo = self._eval_bound(self.min_value, context)
        hi = self._eval_bound(self.max_value, context)
        return rng.randint(lo, hi)

    def _eval_bound(self, bound, context):
        return resolve_bound(bound, context)

    def fixed(self, value):
        self._fixed = value
        return self

    def with_resolve(self, fn):
        self._resolve_fn = fn
        return self

    def render(self, value):
        return str(value)


class Integer(_Var):
    pass


class LongInteger(_Var):
    pass


class Float(_Var):
    def __init__(self, name, min_value=None, max_value=None, decimals=2):
        super().__init__(name, min_value, max_value)
        self.decimals = decimals

    def _generate(self, rng, context):
        lo = float(self._eval_bound(self.min_value, context))
        hi = float(self._eval_bound(self.max_value, context))
        return round(rng.uniform(lo, hi), self.decimals)

    def render(self, value):
        if isinstance(value, float) and value == int(value):
            return str(int(value))
        return str(value)


class String(_Var):
    def __init__(self, name, length=None, min_length=None, max_length=None,
                 alphabet="abcdefghijklmnopqrstuvwxyz"):
        super().__init__(name)
        self.length = length
        self.min_length = min_length
        self.max_length = max_length
        self.alphabet = alphabet

    def _generate(self, rng, context):
        if self.length is not None:
            n = self._eval_bound(self.length, context)
        elif self.min_length is not None and self.max_length is not None:
            lo = self._eval_bound(self.min_length, context)
            hi = self._eval_bound(self.max_length, context)
            n = rng.randint(lo, hi)
        else:
            n = rng.randint(1, 20)
        return "".join(rng.choice(self.alphabet) for _ in range(n))


class Array(_Var):
    def __init__(self, name, size=None, min_size=None, max_size=None,
                 min_value=None, max_value=None, unique=False):
        super().__init__(name, min_value, max_value)
        self.size = size
        self.min_size = min_size
        self.max_size = max_size
        self.unique = unique

    def _generate(self, rng, context):
        n = self._resolve_size(rng, context)
        lo = self._eval_bound(self.min_value, context)
        hi = self._eval_bound(self.max_value, context)
        if self.unique:
            if hi - lo + 1 < n:
                raise ValueError(f"Cannot generate {n} unique values in [{lo}, {hi}]")
            values = rng.sample(range(lo, hi + 1), n)
        else:
            values = [rng.randint(lo, hi) for _ in range(n)]
        return values

    def _resolve_size(self, rng, context):
        if self.size is not None:
            return self._eval_bound(self.size, context)
        if self.min_size is not None and self.max_size is not None:
            lo = self._eval_bound(self.min_size, context)
            hi = self._eval_bound(self.max_size, context)
            return rng.randint(lo, hi)
        return rng.randint(1, 20)

    def render(self, values):
        return " ".join(str(v) for v in values)


class Matrix(_Var):
    def __init__(self, name, rows=None, cols=None,
                 min_value=None, max_value=None):
        super().__init__(name, min_value, max_value)
        self.rows = rows
        self.cols = cols

    def _generate(self, rng, context):
        r = self._eval_bound(self.rows, context)
        c = self._eval_bound(self.cols, context)
        lo = self._eval_bound(self.min_value, context)
        hi = self._eval_bound(self.max_value, context)
        return [[rng.randint(lo, hi) for _ in range(c)] for _ in range(r)]

    def render(self, matrix):
        lines = []
        for row in matrix:
            lines.append(" ".join(str(v) for v in row))
        return "\n".join(lines)


class Permutation(_Var):
    def __init__(self, name, size=None, min_value=1, max_value=None):
        super().__init__(name)
        self.size = size
        self.min_value = min_value
        self.max_value = max_value

    def _generate(self, rng, context):
        n = self._eval_bound(self.size, context)
        hi = self.max_value if self.max_value is not None else n
        lo = self.min_value
        values = list(range(lo, lo + n))
        rng.shuffle(values)
        return values

    def render(self, values):
        return " ".join(str(v) for v in values)

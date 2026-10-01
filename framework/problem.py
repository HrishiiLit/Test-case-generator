import logging
import random as _random
from framework.generators import (
    _Var, resolve_bound, resolve_range, Line, Blocks, flatten_vars,
    Array, Matrix, String, Permutation,
)
from framework.graphs import Graph, Tree
from framework.validators import validate_testcase


logger = logging.getLogger(__name__)

BLOCK_BUDGET = 200000

STRATEGY_KEY = "__strategy__"


# duplicate BLOCK_BUDGET removed


def _minimal_period(seq):
    """Length of the smallest repeating period of *seq* (KMP failure function)."""
    n = len(seq)
    if n <= 1:
        return n
    pi = [0] * n
    for i in range(1, n):
        j = pi[i - 1]
        while j > 0 and seq[i] != seq[j]:
            j = pi[j - 1]
        if seq[i] == seq[j]:
            j += 1
        pi[i] = j
    p = n - pi[-1]
    return p if n % p == 0 else n


def _shape_label(seq):
    """Classify a sequence: constant / sorted / reverse-sorted / repeated / random.

    The label deliberately ignores *values* for the constant case: an array of
    all 50s and an array of all 1s exercise the same code path in a judge
    solution, which is what makes them redundant test cases.
    """
    n = len(seq)
    if n == 0:
        return "empty"
    try:
        if all(x == seq[0] for x in seq):
            return "constant"
        if all(seq[i] <= seq[i + 1] for i in range(n - 1)):
            return "sorted"
        if all(seq[i] >= seq[i + 1] for i in range(n - 1)):
            return "reverse-sorted"
        if _minimal_period(seq) < n:
            return "repeated"
    except TypeError:
        return "random"
    return "random"


def _edge_shape(edges):
    """Structural label for a Graph/Tree edge list."""
    if not edges:
        return "empty"
    if not all(isinstance(e, (list, tuple)) and len(e) >= 2 for e in edges):
        return _shape_label(edges)

    adj = {}
    undirected = set()
    for e in edges:
        a, b = e[0], e[1]
        undirected.add((a, b) if a <= b else (b, a))
        adj.setdefault(a, set()).add(b)
        adj.setdefault(b, set()).add(a)

    verts = set(adj)
    seen = set()
    components = 0
    for v in verts:
        if v in seen:
            continue
        components += 1
        stack = [v]
        seen.add(v)
        while stack:
            for w in adj.get(stack.pop(), ()):
                if w not in seen:
                    seen.add(w)
                    stack.append(w)
    if components > 1:
        return "disconnected"

    n = len(verts)
    deg = {v: len(adj[v]) for v in verts}
    m = len(undirected)
    if n >= 2 and all(d <= 2 for d in deg.values()) and sum(
        1 for d in deg.values() if d == 1
    ) == 2:
        return "chain"
    hub = [v for v in verts if deg[v] == n - 1]
    if n >= 2 and len(hub) == 1 and all(
        deg[v] == 1 for v in verts if v != hub[0]
    ):
        return "star"
    if n >= 2 and m == n * (n - 1) // 2:
        return "dense"
    return "random"


class Problem:
    def __init__(self, name="Problem", testcases=10):
        self.name = name
        self.testcases = testcases
        self._variables = []
        self._input_order = []
        self._strategies = []
        self._custom_cases = []
        self._sample_cases_fns = []  # Functions generating explicit sample testcases
        self._literal_samples = []  # List of (input_text, output_text) literal samples
        #: Set to ``True`` to silence semantic-redundancy findings for specs
        #: where deliberate repeats (e.g. several constant-array cases) are
        #: part of the intended test suite.
        self.allow_redundant = False
        #: Findings produced by the last ``generate_testcases`` call.
        self._redundancy_flags = []
        self._flagged = set()
        self._seen_texts = {}
        self._seen_shapes = {}

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

    def _count_var(self):
        """The scalar declared before the Blocks group that counts sub-tests.

        Supports any casing (``t``, ``T``, ``num_tests``, ...) because the
        header value must equal the number of rendered blocks. Returns ``None``
        for single-test specs.
        """
        if self._blocks_group() is None:
            return None
        for entry in self._input_order:
            if isinstance(entry, Blocks):
                break
            inner = flatten_vars(entry) if isinstance(entry, Line) else [entry]
            for var in inner:
                if isinstance(var, _Var):
                    return var
        for var in self._variables:
            if isinstance(var, _Var):
                return var
        return None

    def add_testcases(self, *strategies):
        for s in strategies:
            self._strategies.append(s)
        return self

    def add_custom_case(self, fn):
        """Add a closure that returns a custom test case dict."""
        self._custom_cases.append(fn)
        return self

    def add_sample(self, *args):
        """Add a sample test case.

        Two usage patterns:
        * ``add_sample(fn)`` where *fn* is a callable receiving ``rng`` and returning a dict of variable values.
        * ``add_sample(input_text, output_text)`` where the raw strings are written verbatim as a sample.

        Literal samples are stored for later processing and take precedence over generated
        samples. The framework will verify the sample against the solution executable.
        """
        if len(args) == 1 and callable(args[0]):
            # Callable case – retain existing behavior.
            fn = args[0]
            self._sample_cases_fns.append(fn)
        elif len(args) == 2 and all(isinstance(a, str) for a in args):
            # Literal sample (input, output).
            self._literal_samples.append((args[0], args[1]))
        else:
            raise ValueError("add_sample expects either a callable or two string arguments")
        return self

    @staticmethod
    def _case_signature(vals):
        """Convert a test case dict to a hashable form for deduplication.

        Everything except the provenance tag participates, including the
        per-block payloads of multi-test cases: two cases that differ only in
        their blocks are genuinely different test data.
        """
        def make_hashable(v):
            if isinstance(v, list):
                return tuple(make_hashable(x) for x in v)
            if isinstance(v, tuple):
                return tuple(make_hashable(x) for x in v)
            if isinstance(v, dict):
                return tuple(sorted((k2, make_hashable(v2)) for k2, v2 in v.items()))
            return v
        return tuple(sorted(
            (k, make_hashable(v))
            for k, v in vals.items()
            if k != STRATEGY_KEY
        ))

    @staticmethod
    def _origin_name(fn):
        """Human-readable name for a strategy closure or custom case."""
        name = getattr(fn, "__name__", None) or "strategy"
        if name.endswith("_strategy"):
            name = name[: -len("_strategy")]
        return name

    def strategy_applicability(self, strat):
        """Return ``None`` when *strat* is meaningful for this spec.

        Otherwise return the human-readable reason it cannot express its
        intent here (e.g. ``mixed_signs`` on a spec whose minimum is 1).
        Strategies opt in by attaching an ``applicable(spec)`` callable.
        """
        check = getattr(strat, "applicable", None)
        if check is None:
            return None
        try:
            return check(self)
        except Exception as e:  # a broken check must not kill dry-run
            return f"applicability check raised {type(e).__name__}: {e}"

    def _label_for(self, var, value):
        """Shape label for one rendered value, using the declared variable."""
        if isinstance(var, (Graph, Tree)):
            return _edge_shape(value) if isinstance(value, list) else None
        if isinstance(var, Matrix):
            if not isinstance(value, list) or not value:
                return None
            if all(row == value[0] for row in value):
                return "constant"
            return "matrix"
        if isinstance(value, str):
            return _shape_label(value)
        if isinstance(value, (list, tuple)):
            return _shape_label(value)
        return None

    def shape_signature(self, vals):
        """Compact shape summary of a case, e.g. ``constant`` or ``sorted``.

        Scalars carry no shape, so a spec without arrays reports ``scalar``.
        """
        by_name = {v.name: v for v in self._variables}
        labels = []

        def visit(key, value):
            if key == "__blocks__" and isinstance(value, list):
                for block in value:
                    if isinstance(block, dict):
                        for inner_key, inner_val in block.items():
                            visit(inner_key, inner_val)
                return
            label = self._label_for(by_name.get(key), value)
            if label and label not in labels:
                labels.append(label)

        for key, value in vals.items():
            if key == STRATEGY_KEY:
                continue
            visit(key, value)
        return "+".join(labels) if labels else "scalar"

    @staticmethod
    def redundancy_key(vals):
        """Hashable fingerprint used for semantic-redundancy detection.

        Scalar inputs must match exactly. Sequences of length two or more keep
        their values unless they are constant, in which case only the length
        survives — an array of all 50s and an array of all 1s of the same length
        are the same test shape. A single-element sequence has no shape to
        speak of, so its one value is the whole test and is compared exactly.
        The provenance tag is ignored so two strategies that produce the same
        shape are compared on data alone.
        """
        def norm(v):
            if isinstance(v, dict):
                return tuple(
                    sorted(
                        (k, norm(x)) for k, x in v.items() if k != STRATEGY_KEY
                    )
                )
            if isinstance(v, str):
                if len(v) > 1 and all(ch == v[0] for ch in v):
                    return ("const", len(v))
                return v
            if isinstance(v, (list, tuple)):
                if len(v) > 1 and not isinstance(v[0], (list, tuple, dict)):
                    if all(x == v[0] for x in v):
                        return ("const", len(v))
                    return tuple(v)
                if len(v) == 1 and not isinstance(v[0], (list, tuple, dict)):
                    return tuple(v)
                return tuple(norm(x) for x in v)
            return v

        return norm(vals)

    def _flag_redundancy(self, kind, first, second, detail):
        """Record a redundancy finding once and warn about it."""
        if self.allow_redundant:
            return
        key = (kind, first, second, detail)
        if key in self._flagged:
            return
        self._flagged.add(key)
        self._redundancy_flags.append(
            {"kind": kind, "first": first, "second": second, "detail": detail}
        )
        logger.warning(
            "%s test case: '%s' and '%s' — %s", kind, first, second, detail
        )

    @property
    def redundancy_flags(self):
        """Redundancy findings from the most recent ``generate_testcases``."""
        return list(self._redundancy_flags)

    def _normalize_aux(self, values):
        """Fill in Graph/Tree header values when a strategy omitted them.

        ``Graph.resolve`` (used by the random filler) returns only the edge
        list, so the rendered header would silently disagree with the data.
        Deriving ``_n`` from the largest vertex referenced keeps the header,
        the validator and the test case itself consistent.
        """
        for v in self._variables:
            if isinstance(v, Graph):
                edges = values.get(v.name)
                if not isinstance(edges, list):
                    continue
                if f"{v.name}_n" not in values:
                    nlo, nhi = resolve_range(
                        getattr(v, "num_vertices", None), values, (1, 1)
                    )
                    max_vertex = max(
                        (max(e[0], e[1]) for e in edges if len(e) >= 2),
                        default=nlo,
                    )
                    values[f"{v.name}_n"] = min(max(max_vertex, nlo), nhi)
                if f"{v.name}_m" not in values:
                    values[f"{v.name}_m"] = len(edges)
            elif isinstance(v, Tree):
                edges = values.get(v.name)
                if not isinstance(edges, list):
                    continue
                if f"{v.name}_n" not in values:
                    nlo, nhi = resolve_range(
                        getattr(v, "num_vertices", None), values, (1, 1)
                    )
                    values[f"{v.name}_n"] = min(max(len(edges) + 1, nlo), nhi)
        return values

    def generate_testcases(
        self, rng, max_retries=10, external_seen=None, external_texts=None
    ):
        """Generate exactly ``self.testcases`` distinct valid cases.

        Every case is tagged with the strategy or custom case that produced it.
        Duplicates are regenerated rather than dropped, and a shortfall raises a
        ``RuntimeError`` that names the requested and produced counts together
        with the declared value ranges, so an undersized domain is obvious.

        A rendered-input duplicate is dropped and regenerated — it is reported
        through :attr:`redundancy_flags` but the suite stays clean, so only a
        shape collision that survives into the suite aborts (unless
        ``allow_redundant`` is set). Strategies the spec cannot express (see
        :meth:`strategy_applicability`) are skipped; the count is still filled
        by the random fallback.
        """
        all_cases = []
        seen = set(external_seen) if external_seen else set()
        self._redundancy_flags = []
        self._flagged = set()
        self._seen_texts = dict(external_texts) if external_texts else {}
        self._seen_shapes = {}

        def _accept(vals, origin):
            vals = dict(vals)
            vals[STRATEGY_KEY] = origin

            try:
                text = self.render_testcase(vals)
            except Exception:
                text = None
            if text is not None:
                prior = self._seen_texts.get(text)
                if prior is not None:
                    if prior != origin:
                        self._flag_redundancy(
                            "duplicate",
                            origin,
                            prior,
                            "identical rendered input text",
                        )
                    return False

            sig = self._case_signature(vals)
            if sig in seen:
                return False
            seen.add(sig)

            try:
                shape = self.redundancy_key(vals)
            except Exception:
                shape = None
            if shape is not None:
                prior = self._seen_shapes.get(shape)
                if prior is not None and prior != origin:
                    self._flag_redundancy(
                        "redundant",
                        origin,
                        prior,
                        f"same shape ({self.shape_signature(vals)}) with "
                        "identical scalar inputs",
                    )
                elif prior is None:
                    self._seen_shapes[shape] = origin

            if text is not None:
                self._seen_texts[text] = origin
            all_cases.append(vals)
            return True

        def _generate_unique(gen_fn, origin, attempts):
            """Return the generated case, None if only duplicates, or raise."""
            last_error = None
            for attempt in range(1, attempts + 1):
                try:
                    vals = gen_fn()
                    if not isinstance(vals, dict):
                        raise ValueError("test case must be a dict of variable values")
                    vals = self._normalize_aux(vals)
                    vals = self._expand_blocks(vals)
                except Exception as e:
                    last_error = e
                    logger.warning(
                        "%s: attempt %d/%d failed: %s", origin, attempt, attempts, e
                    )
                    continue
                if _accept(vals, origin):
                    return all_cases[-1]
                logger.debug(
                    "%s: duplicate case (attempt %d/%d)", origin, attempt, attempts
                )
            if last_error is not None:
                raise RuntimeError(
                    f"{origin} failed after {attempts} attempts: {last_error}"
                )
            return None

        for strat in self._strategies:
            if len(all_cases) >= self.testcases:
                logger.warning(
                    "spec declares %d test cases but already has %d; skipping '%s'",
                    self.testcases, len(all_cases), self._origin_name(strat),
                )
                continue
            origin = self._origin_name(strat)
            reason = self.strategy_applicability(strat)
            if reason:
                logger.warning(
                    "skipping strategy '%s': %s", origin, reason
                )
                continue
            result = _generate_unique(
                lambda: strat(self, rng, {}), origin, max_retries
            )
            if result is None:
                logger.warning(
                    "%s: only produced duplicates of earlier cases; skipped", origin
                )

        for custom_fn in self._custom_cases:
            if len(all_cases) >= self.testcases:
                logger.warning(
                    "spec declares %d test cases but already has %d; skipping "
                    "custom case '%s'",
                    self.testcases, len(all_cases), self._origin_name(custom_fn),
                )
                continue
            origin = f"custom case '{self._origin_name(custom_fn)}'"
            _generate_unique(lambda: custom_fn(rng), origin, max_retries)

        del all_cases[self.testcases:]

        remaining = self.testcases - len(all_cases)
        if remaining > 0:
            filler = self._default_random_strategy()
            budget = remaining * max_retries
            attempts = 0
            while remaining > 0 and attempts < budget:
                attempts += 1
                try:
                    vals = self._normalize_aux(filler(self, rng, {}))
                    vals = self._expand_blocks(vals)
                except Exception as e:
                    logger.warning("random filler: attempt %d failed: %s", attempts, e)
                    continue
                if _accept(vals, "random filler"):
                    remaining -= 1

        if len(all_cases) < self.testcases:
            ranges = ", ".join(
                f"{v.name} in [{v.min_value}, {v.max_value}]"
                for v in self._variables
                if isinstance(v, _Var) and v.min_value is not None
            )
            raise RuntimeError(
                f"Spec '{self.name}': requested {self.testcases} test cases but only "
                f"{len(all_cases)} distinct cases could be generated."
                + (f" Distinct-value limits: {ranges}." if ranges else "")
            )

        fatal = [f for f in self._redundancy_flags if f["kind"] == "redundant"]
        if fatal:
            findings = "\n".join(
                f"  - '{f['first']}' and '{f['second']}' - {f['detail']}"
                for f in fatal
            )
            raise RuntimeError(
                f"Spec '{self.name}': {len(fatal)} redundant test case(s) kept in "
                f"the generated suite:\n"
                f"{findings}\n"
                "Set spec.allow_redundant = True to keep intentional repeats."
            )

        return all_cases


    @staticmethod
    def _size_floor(size):
        """Smallest length a size/rows/length bound may legally take."""
        if size is None:
            return 1
        if hasattr(size, "name"):
            lo = getattr(size, "min_value", None)
            if lo is None:
                return 1
            return int(resolve_bound(lo, {}))
        try:
            value = int(resolve_bound(size, {}))
        except Exception:
            return 1
        return value if value >= 1 else 1

    @classmethod
    def _clamp_size(cls, size, n, cap):
        """Shrink a generated length toward *cap* without breaking its floor."""
        return max(cls._size_floor(size), min(n, cap))

    @staticmethod
    def _rand_in(rng, lo, hi, cap=None):
        """Uniform draw in ``[lo, hi]``, preferring values at or below *cap*."""
        if hi < lo:
            hi = lo
        top = hi if cap is None else min(hi, cap)
        if top < lo:
            top = hi
        return rng.randint(lo, top)

    def _sample_permutation(self, v, ctx, rng, cap):
        """A shuffled run of consecutive values sized to the declared bound."""
        n = self._clamp_size(
            v.size, self._resolve_bound_val(v.size, ctx), cap
        )
        lo = self._resolve_bound_val(v.min_value, ctx)
        values = list(range(lo, lo + n))
        rng.shuffle(values)
        result = {v.name: values}
        if getattr(v.size, "name", None):
            result[v.size.name] = n
        return result

    def generate_sample_testcases(self, rng, count=3, max_lines=15, external_seen=None):
        """Generate ``count`` distinct sample test cases that satisfy the spec.

        Every candidate is validated: a strategy whose attempts are all
        invalid aborts with the violated constraints named, and falling short
        of *count* aborts too. ``max_lines`` is only a readability preference,
        so a spec whose declared minimum size is already large keeps valid
        oversized samples rather than failing or emitting invalid data.
        """
        samples = []
        seen = set(external_seen) if external_seen else set()
        oversized = []

        def _add(vals, origin):
            sig = self._case_signature(vals)
            if sig in seen:
                return False
            seen.add(sig)
            tagged = dict(vals)
            tagged[STRATEGY_KEY] = origin
            samples.append(tagged)
            return True

        def _prepare(vals):
            return self._expand_blocks(self._normalize_aux(vals))

        def _check(vals):
            """Return ``(errors, line_count)`` without letting render bugs escape."""
            try:
                errors = validate_testcase(self, vals)
                if errors:
                    return errors, 0
                return [], self.render_testcase(vals).count("\n")
            except Exception as e:
                return [f"{type(e).__name__}: {e}"], 0

        # Incorporate any literal samples supplied via add_sample.
        for input_text, output_text in getattr(self, "_literal_samples", []):
            if len(samples) >= count:
                break
            origin = "literal sample"
            # Store raw texts in a dict with special keys.
            vals = {"__literal_input__": input_text, "__literal_output__": output_text}
            _add(vals, origin)


        strategies = [
            self._sample_minimum,
            self._sample_small_readable,
            self._sample_boundary,
        ]

        for strat_fn in strategies:
            if len(samples) >= count:
                break
            origin = getattr(strat_fn, "__name__", "sample").lstrip("_")
            produced = 0
            valid = 0
            last_errors = []
            for _ in range(10):
                try:
                    vals = _prepare(strat_fn(rng))
                except Exception:
                    continue
                produced += 1
                errors, line_count = _check(vals)
                if errors:
                    last_errors = errors
                    continue
                valid += 1
                if line_count < 1:
                    continue
                if line_count <= max_lines:
                    if _add(vals, origin):
                        break
                else:
                    oversized.append((vals, origin))
            if produced and valid == 0:
                raise RuntimeError(
                    f"Sample generation failed for '{origin}': every attempt "
                    f"violated the spec:\n"
                    + "\n".join(f"  - {e}" for e in last_errors)
                )

        attempts = 0
        budget = max(20, (count - len(samples)) * 20)
        random_origin = self._sample_random_within_lines.__name__.lstrip("_")
        while len(samples) < count and attempts < budget:
            attempts += 1
            try:
                vals = _prepare(self._sample_random_within_lines(max_lines, rng))
            except Exception:
                continue
            errors, line_count = _check(vals)
            if errors:
                continue
            if line_count < 1:
                continue
            if line_count <= max_lines:
                _add(vals, random_origin)
            else:
                oversized.append((vals, random_origin))

        for vals, origin in oversized:
            if len(samples) >= count:
                break
            _add(vals, origin)

        if len(samples) < count:
            raise RuntimeError(
                f"Spec '{self.name}': only {len(samples)} of {count} distinct "
                f"valid sample test cases could be generated."
            )
        return samples[:count]

    def _sample_minimum(self, rng):
        from framework.strategies import _graph_case, _tree_case

        result = {}
        ctx = {}
        for v in self._variables:
            lo = self._resolve_bound_val(v.min_value, ctx)
            hi = self._resolve_bound_val(v.max_value, ctx)
            if isinstance(v, Graph):
                result.update(_graph_case(v, ctx, rng, "min"))
            elif isinstance(v, Tree):
                result.update(_tree_case(v, ctx, rng, "min"))
            elif isinstance(v, Permutation):
                result.update(self._sample_permutation(v, ctx, rng, 3))
            elif isinstance(v, Array):
                n = self._clamp_size(v.size, v._resolve_size(rng, ctx), 5)
                result[v.name] = [lo] * n
                if getattr(v.size, "name", None):
                    result[v.size.name] = n
            elif isinstance(v, Matrix):
                r = self._clamp_size(
                    v.rows, self._resolve_bound_val(v.rows, ctx), 3
                )
                c = self._clamp_size(
                    v.cols, self._resolve_bound_val(v.cols, ctx), 3
                )
                result[v.name] = [[lo] * c for _ in range(r)]
                if getattr(v.rows, "name", None):
                    result[v.rows.name] = r
                if getattr(v.cols, "name", None):
                    result[v.cols.name] = c
            elif isinstance(v, String):
                n = self._resolve_bound_val(v.length, ctx) if v.length else 3
                n = self._clamp_size(v.length, n, 4)
                if getattr(v, "min_length", None) is not None:
                    n = max(n, self._resolve_bound_val(v.min_length, ctx))
                result[v.name] = (v.alphabet[0] if v.alphabet else "a") * n
                if getattr(v.length, "name", None):
                    result[v.length.name] = n
            elif v.name == "T":
                result[v.name] = 1
            else:
                result[v.name] = lo
            ctx.update(result)
        return self._expand_blocks(result)

    def _sample_small_readable(self, rng):
        from framework.strategies import _graph_case, _tree_case

        result = {}
        ctx = {}
        for v in self._variables:
            lo = self._resolve_bound_val(v.min_value, ctx)
            hi = self._resolve_bound_val(v.max_value, ctx)
            if isinstance(v, Graph):
                result.update(_graph_case(v, ctx, rng, "random"))
            elif isinstance(v, Tree):
                result.update(_tree_case(v, ctx, rng, "random"))
            elif isinstance(v, Permutation):
                result.update(self._sample_permutation(v, ctx, rng, 6))
            elif isinstance(v, Array):
                n = self._clamp_size(v.size, v._resolve_size(rng, ctx), 6)
                span = max(hi - lo + 1, 0)
                unique_vals = [lo + i for i in range(min(n, span))]
                while len(unique_vals) < n:
                    unique_vals.append(self._rand_in(rng, lo, hi, 100))
                result[v.name] = unique_vals[:n]
                if getattr(v.size, "name", None):
                    result[v.size.name] = n
            elif isinstance(v, Matrix):
                r = self._clamp_size(
                    v.rows, self._resolve_bound_val(v.rows, ctx), 4
                )
                c = self._clamp_size(
                    v.cols, self._resolve_bound_val(v.cols, ctx), 4
                )
                result[v.name] = [
                    [self._rand_in(rng, lo, hi, 50) for _ in range(c)]
                    for _ in range(r)
                ]
                if getattr(v.rows, "name", None):
                    result[v.rows.name] = r
                if getattr(v.cols, "name", None):
                    result[v.cols.name] = c
            elif isinstance(v, String):
                n = self._resolve_bound_val(v.length, ctx) if v.length else rng.randint(3, 5)
                n = self._clamp_size(v.length, n, 6)
                if getattr(v, "min_length", None) is not None:
                    n = max(n, self._resolve_bound_val(v.min_length, ctx))
                result[v.name] = "".join(rng.choice(v.alphabet[:5]) for _ in range(n))
                if getattr(v.length, "name", None):
                    result[v.length.name] = n
            elif v.name == "T":
                result[v.name] = 1
            else:
                if hi > 1000:
                    result[v.name] = self._rand_in(rng, max(lo, 1), hi, 100)
                else:
                    result[v.name] = self._rand_in(rng, max(lo, 1), hi, 50)
            ctx.update(result)
        return self._expand_blocks(result)

    def _sample_boundary(self, rng):
        from framework.strategies import _graph_case, _tree_case

        result = {}
        ctx = {}
        for v in self._variables:
            lo = self._resolve_bound_val(v.min_value, ctx)
            hi = self._resolve_bound_val(v.max_value, ctx)
            if isinstance(v, Graph):
                result.update(_graph_case(v, ctx, rng, "max"))
            elif isinstance(v, Tree):
                result.update(_tree_case(v, ctx, rng, "max"))
            elif isinstance(v, Permutation):
                result.update(self._sample_permutation(v, ctx, rng, 5))
            elif isinstance(v, Array):
                n = self._clamp_size(v.size, v._resolve_size(rng, ctx), 5)
                vals = [lo, hi, lo, hi]
                while len(vals) < n:
                    vals.append(rng.randint(lo, hi))
                result[v.name] = vals[:n]
                if getattr(v.size, "name", None):
                    result[v.size.name] = n
            elif isinstance(v, Matrix):
                r = self._clamp_size(
                    v.rows, self._resolve_bound_val(v.rows, ctx), 3
                )
                c = self._clamp_size(
                    v.cols, self._resolve_bound_val(v.cols, ctx), 3
                )
                result[v.name] = [
                    [lo if (i + j) % 2 == 0 else hi for j in range(c)]
                    for i in range(r)
                ]
                if getattr(v.rows, "name", None):
                    result[v.rows.name] = r
                if getattr(v.cols, "name", None):
                    result[v.cols.name] = c
            elif isinstance(v, String):
                n = self._resolve_bound_val(v.length, ctx) if v.length else 4
                n = self._clamp_size(v.length, n, 5)
                if getattr(v, "min_length", None) is not None:
                    n = max(n, self._resolve_bound_val(v.min_length, ctx))
                alphabet = v.alphabet or ["a"]
                result[v.name] = (
                    alphabet[0] * (n // 2) + alphabet[-1] * (n - n // 2)
                )
                if getattr(v.length, "name", None):
                    result[v.length.name] = n
            elif v.name == "T":
                result[v.name] = 1
            else:
                result[v.name] = rng.choice([lo, hi])
            ctx.update(result)
        return self._expand_blocks(result)

    def _sample_random_within_lines(self, max_lines, rng):
        from framework.strategies import _graph_case, _tree_case

        result = {}
        ctx = {}
        for v in self._variables:
            lo = self._resolve_bound_val(v.min_value, ctx)
            hi = self._resolve_bound_val(v.max_value, ctx)
            if isinstance(v, Graph):
                result.update(_graph_case(v, ctx, rng, "random"))
            elif isinstance(v, Tree):
                result.update(_tree_case(v, ctx, rng, "random"))
            elif isinstance(v, Permutation):
                result.update(self._sample_permutation(v, ctx, rng, 8))
            elif isinstance(v, Array):
                n = self._clamp_size(v.size, v._resolve_size(rng, ctx), 8)
                result[v.name] = [
                    self._rand_in(rng, max(lo, 1), hi, 50) for _ in range(n)
                ]
                if getattr(v.size, "name", None):
                    result[v.size.name] = n
            elif isinstance(v, Matrix):
                r = self._clamp_size(
                    v.rows, self._resolve_bound_val(v.rows, ctx), 4
                )
                c = self._clamp_size(
                    v.cols, self._resolve_bound_val(v.cols, ctx), 4
                )
                result[v.name] = [
                    [self._rand_in(rng, lo, hi, 50) for _ in range(c)]
                    for _ in range(r)
                ]
                if getattr(v.rows, "name", None):
                    result[v.rows.name] = r
                if getattr(v.cols, "name", None):
                    result[v.cols.name] = c
            elif isinstance(v, String):
                n = self._resolve_bound_val(v.length, ctx) if v.length else rng.randint(3, 5)
                n = self._clamp_size(v.length, n, 6)
                if getattr(v, "min_length", None) is not None:
                    n = max(n, self._resolve_bound_val(v.min_length, ctx))
                result[v.name] = "".join(rng.choice(v.alphabet) for _ in range(n))
                if getattr(v.length, "name", None):
                    result[v.length.name] = n
            elif v.name == "T":
                result[v.name] = 1
            else:
                if hi > 1000:
                    result[v.name] = self._rand_in(rng, max(lo, 1), hi, 100)
                else:
                    result[v.name] = self._rand_in(rng, lo, hi)
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

        The header value is written back to the declared count variable so the
        rendered input can never claim a different number of blocks.
        """
        group = self._blocks_group()
        if group is None or "__blocks__" in values:
            return values

        count_var = self._count_var()
        if count_var is None:
            raise ValueError(
                "Multi-test spec declares Blocks(...) but no count variable "
                "before it. Declare the test count first, e.g. "
                "spec.input(t, Blocks(n, a))."
            )

        t = values.get(count_var.name)
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
        out[count_var.name] = t
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

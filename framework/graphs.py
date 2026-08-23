import random as _random


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


class Graph:
    _is_graph = True

    def __init__(self, name, num_vertices=None, num_edges=None,
                 directed=False, weighted=False,
                 allow_self_loops=False, allow_multi_edges=False,
                 weight_min=1, weight_max=100):
        self.name = name
        self.num_vertices = num_vertices
        self.num_edges = num_edges
        self.directed = directed
        self.weighted = weighted
        self.allow_self_loops = allow_self_loops
        self.allow_multi_edges = allow_multi_edges
        self.weight_min = weight_min
        self.weight_max = weight_max
        self._fixed = None

    def resolve(self, rng, context):
        if self._fixed is not None:
            return self._fixed
        n = _resolve_bound(self.num_vertices, context)
        m = _resolve_bound(self.num_edges, context)
        return self._generate_edges(n, m, rng)

    def _generate_edges(self, n, m, rng):
        edges = []
        seen = set()
        max_attempts = m * 100 + 10000
        attempts = 0
        while len(edges) < m and attempts < max_attempts:
            attempts += 1
            u = rng.randint(1, n)
            v = rng.randint(1, n)
            if not self.allow_self_loops and u == v:
                continue
            if self.directed:
                key = (u, v)
            else:
                key = (min(u, v), max(u, v))
            if not self.allow_multi_edges and key in seen:
                continue
            seen.add(key)
            if self.weighted:
                weight = rng.randint(self.weight_min, self.weight_max)
                edges.append((u, v, weight))
            else:
                edges.append((u, v))
        if len(edges) < m:
            raise ValueError(f"Could not generate {m} edges for {n} vertices")
        return edges

    def render_header(self, n, m):
        return f"{n} {m}"

    def render_edge(self, edge):
        if self.weighted and len(edge) > 2:
            return f"{edge[0]} {edge[1]} {edge[2]}"
        return f"{edge[0]} {edge[1]}"

    def fixed(self, value):
        self._fixed = value
        return self


class Tree:
    _is_tree = True

    def __init__(self, name, num_vertices=None, weighted=False,
                 weight_min=1, weight_max=100):
        self.name = name
        self.num_vertices = num_vertices
        self.weighted = weighted
        self.weight_min = weight_min
        self.weight_max = weight_max
        self._fixed = None

    def resolve(self, rng, context):
        if self._fixed is not None:
            return self._fixed
        n = _resolve_bound(self.num_vertices, context)
        return self._generate_edges(n, rng)

    def _generate_edges(self, n, rng):
        if n <= 1:
            return []
        edges = []
        for i in range(2, n + 1):
            parent = rng.randint(1, i - 1)
            if self.weighted:
                weight = rng.randint(self.weight_min, self.weight_max)
                edges.append((parent, i, weight))
            else:
                edges.append((parent, i))
        return edges

    def render_header(self, n):
        return str(n)

    def render_edge(self, edge):
        if self.weighted and len(edge) > 2:
            return f"{edge[0]} {edge[1]} {edge[2]}"
        return f"{edge[0]} {edge[1]}"

    def fixed(self, value):
        self._fixed = value
        return self

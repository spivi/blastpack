"""Ground-truth forward reachability via directed BFS, O(V+E) per source.

Forward = follow OUT-edges only. This is the independent oracle the closure is
checked against on every build.
"""
from collections import deque


def reachable(graph, src):
    """Set of nodes forward-reachable from src (excluding src itself)."""
    adj = graph["adj"]
    seen = set()
    q = deque(adj[src])
    seen.update(adj[src])
    while q:
        u = q.popleft()
        for v in adj[u]:
            if v not in seen:
                seen.add(v)
                q.append(v)
    seen.discard(src)
    return seen

"""Node ordering strategies.

A perm maps ordering-position -> original node id: perm[pos] = node_id. Rows are
packed in ordering space, so locality in the ordering decides whether reachable
bits form long zero runs (which the codec rewards).
"""
import random


def invert(perm):
    """inv[node_id] = position in perm."""
    inv = [0] * len(perm)
    for pos, node in enumerate(perm):
        inv[node] = pos
    return inv


def cluster_aware_bloodhound(graph):
    """Group nodes by domain, then type, numbered contiguously. Deterministic."""
    domain_of = graph["meta"]["domain_of"]
    type_of = graph["meta"]["type_of"]
    return sorted(range(graph["n"]),
                  key=lambda node: (domain_of[node], type_of[node], node))


def arbitrary(graph, seed):
    """A random permutation of node ids — a test baseline for ordering's effect."""
    perm = list(range(graph["n"]))
    random.Random(seed).shuffle(perm)
    return perm

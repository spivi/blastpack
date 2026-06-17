from blastpack import oracle


def _graph(adj):
    return {"n": len(adj), "adj": [set(s) for s in adj], "meta": {}}


def test_reachable_chain():
    # 0 -> 1 -> 2 ; 2 is a leaf
    g = _graph([[1], [2], []])
    assert oracle.reachable(g, 0) == {1, 2}
    assert oracle.reachable(g, 2) == set()


def test_reachable_excludes_self_even_in_cycle():
    # 0 -> 1 -> 0  (cycle)
    g = _graph([[1], [0]])
    assert oracle.reachable(g, 0) == {1}


def test_reachable_forward_only():
    # 0 -> 1 ; reverse edge must NOT be traversed from 1
    g = _graph([[1], []])
    assert oracle.reachable(g, 1) == set()

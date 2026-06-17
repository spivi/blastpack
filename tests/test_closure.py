from blastpack import closure, oracle, ordering


def _graph(adj, domain=None, type_=None):
    n = len(adj)
    meta = {"domain_of": domain or ["D"] * n,
            "type_of": type_ or ["User"] * n}
    return {"n": n, "adj": [set(s) for s in adj], "meta": meta}


def test_decode_row_equals_oracle_all_nodes_all_orderings():
    # 0 -> 1 -> 2 -> 3 ; plus 1 -> 3 shortcut
    g = _graph([[1], [2, 3], [3], []])
    for perm in (ordering.cluster_aware_bloodhound(g),
                 ordering.arbitrary(g, 1)):
        table = closure.build(g, perm)
        inv = ordering.invert(perm)
        for node in range(g["n"]):
            pos = inv[node]
            assert closure.decode_row(table, pos) == oracle.reachable(g, node)


def test_build_reports_byte_totals():
    g = _graph([[1], [2], []])
    table = closure.build(g, ordering.cluster_aware_bloodhound(g))
    assert table["nbytes"] == 1            # 3 nodes -> 1 byte
    assert table["raw_bytes"] == 3         # nbytes * n
    assert table["compressed_bytes"] == sum(len(r) for r in table["rows"])
    assert len(table["rows"]) == 3

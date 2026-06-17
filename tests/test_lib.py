import pathlib

from blastpack import lib, loader, oracle, pack

FIXTURE = str(pathlib.Path(__file__).parent / "fixtures" / "essos_like")


def _build(tmp_path):
    out = tmp_path / "essos.blastpack"
    p = pack.build_pack(loader.load(FIXTURE), source_name="x", build_timestamp="t")
    pack.write_pack(p, str(out))
    return str(out)


def test_reach_bitset_matches_decoded_row(tmp_path):
    path = _build(tmp_path)
    P = lib.load(path)
    p = pack.read_pack(path)
    i = pack.resolve_node(p, "S-1-5-21-AAA-512")
    bits = P.reach(i)
    expected = pack.decode_pack_row(p, i)
    got = {b for b in range(len(p["nodes"])) if (bits >> b) & 1}
    assert got == expected


def test_reach_after_is_union(tmp_path):
    path = _build(tmp_path)
    P = lib.load(path)
    a, b = 0, 1
    assert P.reach_after([a, b]) == (P.reach(a) | P.reach(b))


def test_covers_counts_targets_hit(tmp_path):
    path = _build(tmp_path)
    P = lib.load(path)
    da = P.resolve("S-1-5-21-AAA-512")
    targets = P.bitset_of([P.resolve("S-1-5-21-AAA-2001")])  # WS01
    assert P.covers(P.reach(da), targets) == 1  # DA reaches WS01


def test_score_frontier_top_matches_bfs_marginal(tmp_path):
    path = _build(tmp_path)
    P = lib.load(path)
    p = pack.read_pack(path)
    g = loader.load(FIXTURE)

    targets_sids = {"S-1-5-21-AAA-2001", "S-1-5-21-AAA-2002"}  # the two computers
    target_idx = [pack.resolve_node(p, s) for s in targets_sids]
    targets = P.bitset_of(target_idx)
    candidates = list(range(len(p["nodes"])))
    scores = P.score_frontier(candidates, targets)

    # independent BFS marginal coverage over the same targets
    sid_to_id = {s: i for i, s in enumerate(g["meta"]["sid_of"])}
    idx_to_sid = {pack.resolve_node(p, s): s for s in g["meta"]["sid_of"]}
    def bfs_cover(node_idx):
        sid = p["nodes"][node_idx]["id"]
        reach = oracle.reachable(g, sid_to_id[sid])
        reach_sids = {g["meta"]["sid_of"][r] for r in reach}
        return len(reach_sids & targets_sids)

    top = max(scores, key=lambda i: scores[i])
    assert scores[top] == bfs_cover(top)
    assert scores[top] == max(bfs_cover(i) for i in candidates)


def test_provenance_exposes_timestamp(tmp_path):
    path = _build(tmp_path)
    P = lib.load(path)
    assert "build_timestamp" in P.provenance


def test_score_frontier_marginal_over_have(tmp_path):
    path = _build(tmp_path)
    P = lib.load(path)
    p = pack.read_pack(path)
    # targets = everything reachable from some admin group, as a concrete target set
    da = pack.resolve_node(p, "S-1-5-21-AAA-512")
    targets = P.reach(da)
    if targets == 0:
        # admin reaches nobody on this fixture build — pick a non-empty reach instead
        targets = P.bitset_of(range(len(P.nodes)))
    # with have already covering the admin's reach, the admin's own marginal must be 0
    scores = P.score_frontier([da], targets, have=[da])
    assert scores[da] == 0
    # and without have, the admin scores its full coverage of targets (>= the have-version)
    base_scores = P.score_frontier([da], targets, have=None)
    assert base_scores[da] >= scores[da]
